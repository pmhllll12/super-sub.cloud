#!/usr/bin/env bash
# 유휴하면 인스턴스를 스스로 멈춘다 — AWS 권한 없이.
#
#   sudo /opt/supersub/autostop.sh          # 한 번 판정 (타이머가 5분마다 부른다)
#   sudo /opt/supersub/autostop.sh --dry-run # 판정만 하고 끄지는 않는다
#
# **왜 인스턴스 안에서 끄는가.** 보통 쓰는 자동 종료(CloudWatch 알람,
# EC2 Instance Scheduler, Lambda)는 전부 IAM 권한이 필요한데 `ho`는 IAM이
# 전면 차단이다(미결 항목 「AWS 계정에서 `ho`가 IAM·할당량을 못 쓴다」).
# EBS 기반 인스턴스는 **안에서 poweroff 하면 stop 상태로 떨어지므로**,
# AWS 자격증명이 하나도 없어도 과금을 멈출 수 있다. 지금 되는 유일한 방법이다.
#
# 🔴 **쓰기 전에 반드시 확인할 것 — 종료 동작이 `중지(stop)`인가.**
#   EC2 → 인스턴스 선택 → 작업 → 인스턴스 설정 → **종료 동작 변경**
#   여기가 `종료(terminate)`면 이 스크립트가 **인스턴스와 EBS를 지운다.**
#   기본값은 `중지`지만 기본값을 믿고 돌리지 않는다. 확인은 공짜다.
set -euo pipefail

CONF=/etc/supersub/autostop.conf
# shellcheck source=/dev/null
[[ -r $CONF ]] && . "$CONF"

# GPU도 분석 프로세스도 없고 아무도 안 붙어 있을 때 기다리는 시간
IDLE_MINUTES="${IDLE_MINUTES:-30}"
# SSH 세션은 열려 있는데 일은 안 하고 있을 때 — 터미널을 켜 둔 채 퇴근한 경우다.
# 사람이 붙어 있다고 무한정 봐주면 이 스크립트가 막으려던 그 상황이 된다.
SSH_IDLE_MINUTES="${SSH_IDLE_MINUTES:-120}"
# 무엇을 하고 있든 이만큼 지나면 끈다. 위 둘이 오판해도 이건 걸린다.
MAX_UPTIME_HOURS="${MAX_UPTIME_HOURS:-12}"
# 이 값을 넘으면 GPU가 일하는 중으로 본다 (%)
GPU_UTIL_BUSY="${GPU_UTIL_BUSY:-10}"
# 이 패턴이 걸리면 일하는 중으로 본다. GPU를 아직 안 쓰는 구간(영상 디코딩,
# 모델 다운로드, S3 전송)이 있어서 GPU 사용률만으로는 부족하다.
#
# 🔴 **명령줄 맨 앞을 고정한다.** `pgrep -f` 는 명령줄 **어디에나** 그 문자열이
# 있으면 걸리므로, 파일 이름만 적어 두면 `vim analyze.py` 나 `less analyze.py`
# 까지 "작업 중"이 된다 — 편집기를 열어 둔 채 자리를 뜨면 영영 안 꺼지고,
# 그게 이 타이머가 막으려던 바로 그 상황이다. 그래서 **실제로 그 스크립트를
# 실행하는 인터프리터**만 걸리도록 앞을 묶는다.
#
# POSIX 확장 정규식이다 (pgrep 이 regcomp 를 쓴다) — `\S` 같은 GNU 확장은
# 쓰지 않는다.
BUSY_PATTERN="${BUSY_PATTERN:-^[^[:space:]]*(python[0-9.]*|uv)[[:space:]].*(analyze_s3|analyze|measure|track_overlay)\.py|^[^[:space:]]*hf[[:space:]]+download|^[^[:space:]]*aws[[:space:]]+s3}"

HOLD_FILE="${HOLD_FILE:-/run/supersub-autostop.hold}"
STATE_FILE="${STATE_FILE:-/run/supersub-autostop.idle-since}"

DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

log() { echo "[autostop] $*"; }

now=$(date +%s)

# --- 보류 파일 ------------------------------------------------------------
# 오래 걸리는 작업 앞에 걸어 둔다. 비어 있으면 무기한, 안에 unix 시각이 있으면
# 그때까지만 — 무기한 보류를 걸고 잊는 것이 가장 비싼 실수라 만료를 권한다.
#
#   sudo supersub-hold 4h     # 4시간 보류 (설치 스크립트가 만들어 주는 도우미)
#   sudo rm /run/supersub-autostop.hold
if [[ -e $HOLD_FILE ]]; then
  until_ts=$(tr -dc '0-9' < "$HOLD_FILE" | head -c 20)
  if [[ -n $until_ts ]] && (( now >= until_ts )); then
    log "보류 만료 ($(date -d "@$until_ts" '+%F %T')) — 보류를 푼다"
    rm -f "$HOLD_FILE"
  else
    if [[ -n $until_ts ]]; then
      log "보류 중 — $(date -d "@$until_ts" '+%F %T') 까지"
    else
      log "보류 중 — 만료 없음 (해제: sudo rm $HOLD_FILE)"
    fi
    rm -f "$STATE_FILE"
    exit 0
  fi
fi

# --- 무엇이 돌고 있나 ------------------------------------------------------
gpu_util=0
if command -v nvidia-smi >/dev/null 2>&1; then
  # 여러 장이면 가장 높은 것을 본다. 실패하면 0으로 두고 아래 프로세스·세션
  # 검사와 최대 가동시간에 맡긴다 — 여기서 "바쁘다"로 넘겨 버리면 영영 안 꺼진다.
  gpu_util=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null \
             | tr -dc '0-9\n' | sort -n | tail -1) || gpu_util=0
  [[ -z $gpu_util ]] && gpu_util=0
else
  log "경고: nvidia-smi 가 없다 — GPU 사용률을 0으로 본다"
fi

# 🔴 GPU **메모리**는 유휴 판정에 쓰지 않는다. vLLM이 상주하며 VRAM을 미리
# 잡아 두기 때문이다(vllm.env 의 SUPERSUB_GPU_FRACTION=0.35). 메모리로 보면
# vLLM이 떠 있는 한 영원히 "바쁨"이 되어 이 스크립트가 무력해진다.
# 사용률은 요청이 없으면 0으로 떨어지므로 그쪽을 본다.

busy_procs=$(pgrep -fc "$BUSY_PATTERN" 2>/dev/null || true)
[[ -z $busy_procs ]] && busy_procs=0

ssh_sessions=$(who 2>/dev/null | wc -l)

uptime_s=$(awk '{print int($1)}' /proc/uptime)
max_uptime_s=$(( MAX_UPTIME_HOURS * 3600 ))

log "GPU ${gpu_util}% · 분석 프로세스 ${busy_procs} · 접속 ${ssh_sessions} · 가동 $(( uptime_s / 60 ))분"

# --- 최대 가동시간 ---------------------------------------------------------
if (( uptime_s >= max_uptime_s )); then
  log "가동 ${MAX_UPTIME_HOURS}시간을 넘었다 — 무조건 멈춘다"
  if (( DRY_RUN )); then log "(--dry-run: 멈추지 않는다)"; exit 0; fi
  exec systemctl poweroff
fi

# --- 유휴 판정 -------------------------------------------------------------
busy=0
(( gpu_util > GPU_UTIL_BUSY )) && busy=1
(( busy_procs > 0 )) && busy=1

if (( busy )); then
  rm -f "$STATE_FILE"
  log "작업 중 — 유휴 타이머를 초기화한다"
  exit 0
fi

# 사람이 붙어 있으면 더 오래 봐준다. 다만 무한정은 아니다.
if (( ssh_sessions > 0 )); then
  limit_min="$SSH_IDLE_MINUTES"
  why="접속은 있으나 작업 없음"
else
  limit_min="$IDLE_MINUTES"
  why="접속도 작업도 없음"
fi

if [[ ! -e $STATE_FILE ]]; then
  echo "$now" > "$STATE_FILE"
  log "$why — 유휴 시작 (${limit_min}분 뒤 멈춘다)"
  exit 0
fi

since=$(tr -dc '0-9' < "$STATE_FILE" | head -c 20)
[[ -z $since ]] && since=$now
idle_min=$(( (now - since) / 60 ))

if (( idle_min >= limit_min )); then
  log "$why 이 ${idle_min}분 지속 — 멈춘다"
  if (( DRY_RUN )); then log "(--dry-run: 멈추지 않는다)"; exit 0; fi
  exec systemctl poweroff
fi

log "$why — ${idle_min}/${limit_min}분"
