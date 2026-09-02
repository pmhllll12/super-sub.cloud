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
uv sync --extra aws

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
