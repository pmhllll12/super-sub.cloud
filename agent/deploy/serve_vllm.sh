#!/usr/bin/env bash
# EXAONE 4.0 1.2B를 vLLM OpenAI 호환 서버로 띄운다 (T4 16GB 전용 설정).
#
# ┌ T4에서 반드시 지켜야 하는 것 ─────────────────────────────────────────┐
# │ dtype=float16 이어야 한다. T4는 Turing(SM 7.5)이라 bfloat16 네이티브   │
# │ 지원이 없고, vLLM은 compute capability 8.0 미만에서 bfloat16을 거부한다.│
# │ judge.py의 로컬 경로가 bf16인 것과 다르다 — 그쪽은 개발 GPU 기준이다.  │
# └───────────────────────────────────────────────────────────────────────┘
#
# GPU 예산이 이 스크립트의 핵심이다. T4 16GB 한 장을 vLLM과 포즈 모델
# (RT-DETR + ViTPose)이 나눠 쓴다. vLLM은 gpu_memory_utilization 만큼을
# **미리 잡고 놓지 않으므로**, 기본값 0.9로 두면 포즈 추출이 OOM으로 죽는다.
# 0.35면 1.2B 가중치(fp16 약 2.4GB) + KV 캐시가 들어가고 나머지가 포즈 몫이다.
#
# 🔴 **vLLM은 에이전트 venv에 넣지 않는다.** vLLM 휠은 자기가 빌드된 torch에만
# 맞는 C 확장을 들고 오는데, pyproject 는 torch 를 cu126 · <2.9 로 고정하고 있다.
# 같은 venv 에 넣으면 둘 중 하나가 깨진다 — 2026-09-03 에 실제로 vllm import 가
# `undefined symbol: torch_list_size` 로, torchvision 이 `operator
# torchvision::nms does not exist` 로 죽었다(포즈 경로가 여기 걸린다).
# 서버는 별도 프로세스라 venv 를 나눠도 아무 문제가 없다.
set -euo pipefail

MODEL_DIR="${SUPERSUB_MODEL_DIR:-/opt/supersub/models/exaone-4.0-1.2b}"
# judge.py의 MODELS["1.2B"]와 **같아야 한다.** 다르면 Judge.load()가 서빙 목록을
# 보고 거부한다 (그러라고 만든 검사다).
SERVED_NAME="${SUPERSUB_SERVED_NAME:-LGAI-EXAONE/EXAONE-4.0-1.2B}"
# 127.0.0.1에 묶는다. vLLM OpenAI 서버는 인증이 없으므로 외부에 열지 않는다.
HOST="${SUPERSUB_VLLM_HOST:-127.0.0.1}"
PORT="${SUPERSUB_VLLM_PORT:-8000}"
GPU_FRACTION="${SUPERSUB_GPU_FRACTION:-0.35}"
# 판정 프롬프트는 항목 하나짜리라 짧다(수백 토큰). 컨텍스트를 모델 최대값으로
# 두면 KV 캐시가 그만큼 잡혀 포즈 몫을 깎는다.
MAX_LEN="${SUPERSUB_MAX_MODEL_LEN:-4096}"
# CUDA 그래프 캡처를 끄면 1~3GB를 아낀다. 1.2B에서 지연 차이는 작고, 메모리가
# 빠듯한 구성이라 기본으로 켜 둔다. 여유가 확인되면 0으로 바꿀 것.
ENFORCE_EAGER="${SUPERSUB_ENFORCE_EAGER:-1}"
# vLLM 실행 파일. 위 주석대로 에이전트 venv 와 분리된 venv 를 가리킨다.
VLLM_BIN="${SUPERSUB_VLLM_BIN:-/opt/supersub/vllm-venv/bin/vllm}"

[[ -d "$MODEL_DIR" ]] || { echo "모델 디렉터리 없음: $MODEL_DIR (sync_model.sh 먼저)" >&2; exit 1; }
[[ -x "$VLLM_BIN" ]] || {
  echo "vLLM 실행 파일 없음: $VLLM_BIN" >&2
  echo "  uv venv /opt/supersub/vllm-venv --python 3.12" >&2
  echo "  VIRTUAL_ENV=/opt/supersub/vllm-venv uv pip install vllm" >&2
  exit 1
}

args=(
  --model "$MODEL_DIR"
  --served-model-name "$SERVED_NAME"
  --host "$HOST" --port "$PORT"
  --dtype float16
  --gpu-memory-utilization "$GPU_FRACTION"
  --max-model-len "$MAX_LEN"
  --disable-log-requests
)
[[ "$ENFORCE_EAGER" == "1" ]] && args+=(--enforce-eager)

echo "[vllm] $SERVED_NAME @ $HOST:$PORT  gpu=$GPU_FRACTION len=$MAX_LEN eager=$ENFORCE_EAGER"
exec "$VLLM_BIN" serve "${args[@]}"
