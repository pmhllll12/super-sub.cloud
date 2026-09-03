#!/usr/bin/env bash
# 자동 종료 타이머를 설치한다. EC2 안에서 한 번만 돌린다.
#
#   cd ~/super-sub.cloud && sudo ./agent/deploy/install_autostop.sh
#
# 🔴 **먼저 확인할 것 — 종료 동작이 `중지(stop)`인가.**
#
#   EC2 → 인스턴스 선택 → 작업 → 인스턴스 설정 → **종료 동작 변경**
#
# 여기가 `종료(terminate)`면 이 타이머가 인스턴스와 EBS를 **지운다.** 모델
# 캐시도 함께 사라지고 되돌릴 수 없다. 콘솔 기본값은 `중지`지만, 기본값을
# 믿고 돌리지 않는다 — 확인은 30초고 공짜다.
#
# 인스턴스 안에서는 이 값을 읽을 방법이 없다. IMDS 가 노출하지 않고,
# ec2:DescribeInstanceAttribute 는 자격증명이 필요한데 우리 인스턴스에는
# IAM 역할이 없다(미결 항목 「AWS 계정에서 `ho`가 IAM·할당량을 못 쓴다」).
# 그래서 **사람이 확인했다고 말해 줘야** 설치가 진행된다.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ${EUID} -ne 0 ]]; then
  echo "root 로 실행할 것: sudo $0 $*" >&2
  exit 1
fi

if [[ "${1:-}" != "--shutdown-behavior-verified" ]]; then
  cat >&2 <<'MSG'
설치를 멈춘다 — 종료 동작을 아직 확인하지 않았다.

  EC2 → 인스턴스 선택 → 작업 → 인스턴스 설정 → 종료 동작 변경

값이 "중지(stop)" 인지 보고, 맞으면 다시 실행한다:

  sudo ./agent/deploy/install_autostop.sh --shutdown-behavior-verified

"종료(terminate)" 라면 먼저 "중지" 로 바꾼다. 그대로 두고 설치하면 이 타이머가
유휴를 감지했을 때 인스턴스와 EBS 를 지운다.
MSG
  exit 2
fi

echo "[1/5] 스크립트 설치"
install -d -m 755 /opt/supersub
install -m 755 "$SRC/autostop.sh"    /opt/supersub/autostop.sh
install -m 755 "$SRC/supersub-hold"  /usr/local/bin/supersub-hold

echo "[2/5] 설정 파일"
install -d -m 755 /etc/supersub
if [[ -e /etc/supersub/autostop.conf ]]; then
  echo "      이미 있어 그대로 둔다 — /etc/supersub/autostop.conf"
else
  install -m 644 "$SRC/autostop.conf.example" /etc/supersub/autostop.conf
  echo "      기본값으로 만들었다 — /etc/supersub/autostop.conf"
fi

echo "[3/5] systemd 유닛"
install -m 644 "$SRC/supersub-autostop.service" /etc/systemd/system/
install -m 644 "$SRC/supersub-autostop.timer"   /etc/systemd/system/
systemctl daemon-reload

echo "[4/5] 판정이 되는지 먼저 본다 (--dry-run — 여기서는 안 꺼진다)"
/opt/supersub/autostop.sh --dry-run

echo "[5/5] 타이머 시작"
systemctl enable --now supersub-autostop.timer

echo
echo "설치 완료."
systemctl list-timers supersub-autostop.timer --no-pager || true
cat <<'MSG'

쓰는 법:
  sudo supersub-hold 4h                          # 오래 걸리는 작업 앞에 보류
  sudo supersub-hold                             # 남은 보류 확인
  sudo supersub-hold off                         # 즉시 해제
  journalctl -u supersub-autostop -n 30 --no-pager   # 판정 기록

기본값: 유휴 30분(접속 없음) / 120분(접속은 있으나 작업 없음) / 최대 가동 12시간.
바꾸려면 /etc/supersub/autostop.conf 를 고치고
  sudo systemctl restart supersub-autostop.timer
MSG
