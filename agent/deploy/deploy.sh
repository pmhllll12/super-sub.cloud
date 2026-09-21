#!/usr/bin/env bash
# EC2 수동 배포 — git pull origin ho → 의존성 동기화 → 서비스 재시작 → 상태 확인.
#
#   cd ~/super-sub.cloud && ./agent/deploy/deploy.sh
#
# 로컬에서 ho에 푸시한 뒤 EC2에서 이것 하나만 돌리면 된다. 손으로 하던 순서를
# 그대로 옮긴 것이고, 다른 점은 **마지막에 확인까지 한다**는 것뿐이다 —
# 재시작만 하고 끝내면 기동 실패를 다음 분석 때 알게 된다.
set -euo pipefail

REPO="${SUPERSUB_REPO:-$HOME/super-sub.cloud}"
BRANCH="${SUPERSUB_BRANCH:-ho}"
VLLM_URL="${SUPERSUB_VLLM_URL:-http://127.0.0.1:8000}"

# 🔴 `uv` 를 PATH 에 기대지 않는다 (2026-09-21). 설치 위치가
# `~/.local/bin` 이라 **로그인 셸에서만** PATH 에 들어온다 — 사람이 손으로
# 돌릴 때는 보이지만 `ssh <호스트> './deploy.sh'` 처럼 비대화형으로 부르면
# `uv: command not found` 로 2단계에서 멈춘다(실제로 겪었다). 그때 pull 은
# 이미 끝나 있어서 **코드는 새것이고 venv 는 옛것인** 어중간한 상태가 된다.
UV="${SUPERSUB_UV:-$(command -v uv 2>/dev/null || true)}"
if [[ -z "$UV" ]]; then
  for cand in "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv" /usr/local/bin/uv; do
    if [[ -x "$cand" ]]; then UV="$cand"; break; fi
  done
fi
if [[ -z "$UV" ]]; then
  echo "uv 를 찾지 못했다. 경로를 SUPERSUB_UV 로 주거나 PATH 에 넣을 것." >&2
  exit 1
fi

cd "$REPO"

# 작업 트리가 더러우면 멈춘다. EC2에서 직접 고친 것이 있으면 pull이 그것을
# 덮거나 충돌한다 — 조용히 진행하면 어느 코드가 도는지 알 수 없게 된다.
if [[ -n "$(git status --porcelain)" ]]; then
  echo "작업 트리에 변경이 있다. 커밋하거나 되돌린 뒤 다시 실행할 것:" >&2
  git status --short >&2
  exit 1
fi

echo "[1/4] git pull origin $BRANCH"
git checkout "$BRANCH"
git pull origin "$BRANCH"
echo "      → $(git rev-parse --short HEAD) $(git log -1 --format=%s)"

echo "[2/4] 의존성 동기화"
cd "$REPO/agent"
# 🔴 `--locked` 가 핵심이다 (미결 ho 49번). 이게 없으면 uv 가 그 자리에서
#    **다시 해석**하고, 그래서 EC2 와 평가 기계가 같은 커밋인데도
#    transformers 5.16.1 / 5.15.1 로 갈려 **같은 영상이 다른 등급**을 받았다.
#    `--locked` 는 `uv.lock` 과 `pyproject.toml` 이 어긋나면 **멈춘다** —
#    조용히 다른 버전으로 도는 것보다 배포가 실패하는 편이 낫다.
#    (어긋났다고 나오면 로컬에서 `uv lock` 하고 커밋한 뒤 다시 배포한다.)
#
# 🔴 `--extra aws` 를 빼지 말 것 — boto3 가 빠져 S3 경로가 죽는다.
"$UV" sync --locked --extra aws

echo "[3/4] vLLM 재시작"
# 코드를 pull했다고 모델이 바뀌지는 않지만, serve_vllm.sh나 유닛이 바뀌었을 수
# 있어 항상 재시작한다. 1.2B 적재는 수십 초다.
sudo systemctl restart supersub-vllm

echo "[4/4] 기동 확인"
for i in $(seq 1 60); do
  if curl -sf "$VLLM_URL/v1/models" >/dev/null; then
    echo "      vLLM 응답 OK — $(curl -s "$VLLM_URL/v1/models" | python3 -c 'import sys,json; print(*[m["id"] for m in json.load(sys.stdin)["data"]])')"
    exit 0
  fi
  sleep 5
done

echo "vLLM이 5분 안에 뜨지 않았다. 로그를 볼 것:" >&2
echo "  sudo journalctl -u supersub-vllm -n 100 --no-pager" >&2
exit 1
