#!/usr/bin/env bash
# 자동 종료를 **완전히 제거한다.** EC2 안에서 돌린다.
#
#   cd ~/super-sub.cloud && sudo ./agent/deploy/uninstall_autostop.sh --i-will-stop-it-myself
#
# 🔴 **제거하면 인스턴스가 스스로 꺼지지 않는다.** 지금까지는 잊고 두어도
# 최대 18시간이면 멈췄다(`/etc/supersub/autostop.conf` 의 `MAX_UPTIME_HOURS`).
# 제거 뒤에는 **상한이 없다** — 사람이 끄지 않으면 계속 켜져 있고, g4dn.xlarge
# 온디맨드 $0.647/시간이면 하루 방치에 **$15.5** 다.
#
# 그래서 확인 플래그를 요구한다. `install_autostop.sh` 가 "종료 동작이 중지인가"
# 를 사람에게 물었던 것과 같은 이유다 — 인스턴스 안에서는 확인할 수 없고,
# 틀렸을 때 조용히 비싸진다.
#
# **잠깐만 안 꺼지게 하려는 것이면 이 스크립트가 아니다.** 보류를 쓴다:
#
#   sudo supersub-hold 4h
#
# 보류는 만료가 있어서 잊어도 결국 돌아온다. 제거는 안 돌아온다.
#
# 되살리기:
#
#   sudo ./agent/deploy/install_autostop.sh --shutdown-behavior-verified
#
# 🔴 되살리면 **스크립트 기본값(30/120/12)** 으로 돌아온다. 이 인스턴스에만
# 있던 튜닝값(90/240/18)은 복구되지 않는다 — 아래에서 지우기 전에 내용을
# 찍어 두므로, 필요하면 그 출력에서 되살린다.
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "root 로 실행할 것: sudo $0 $*" >&2
  exit 1
fi

if [[ "${1:-}" != "--i-will-stop-it-myself" ]]; then
  cat >&2 <<'MSG'
제거를 멈춘다 — 확인 플래그가 없다.

제거하면 이 인스턴스는 **스스로 꺼지지 않는다.** 끄는 것은 사람 몫이 된다.
그래도 할 것이면:

  sudo ./agent/deploy/uninstall_autostop.sh --i-will-stop-it-myself

잠깐만 안 꺼지게 하려는 것이면 보류가 맞는 도구다 (만료가 있다):

  sudo supersub-hold 4h
MSG
  exit 2
fi

echo "[1/5] 지우기 전에 지금 설정을 남긴다 — 되살릴 때 쓸 유일한 사본이다"
if [[ -e /etc/supersub/autostop.conf ]]; then
  echo "----- /etc/supersub/autostop.conf -----"
  cat /etc/supersub/autostop.conf
  echo "---------------------------------------"
else
  echo "      없음 (이미 지워졌거나 설치된 적이 없다)"
fi

echo "[2/5] 타이머 정지·비활성"
systemctl disable --now supersub-autostop.timer 2>/dev/null || true
systemctl stop supersub-autostop.service 2>/dev/null || true

echo "[3/5] systemd 유닛 제거"
rm -f /etc/systemd/system/supersub-autostop.service
rm -f /etc/systemd/system/supersub-autostop.timer
systemctl daemon-reload
systemctl reset-failed supersub-autostop.service 2>/dev/null || true

echo "[4/5] 스크립트·설정 제거"
rm -rf /opt/supersub
rm -f /usr/local/bin/supersub-hold
rm -rf /etc/supersub

echo "[5/5] 남은 것이 없는지 확인"
left=0
for p in /etc/systemd/system/supersub-autostop.service \
         /etc/systemd/system/supersub-autostop.timer \
         /opt/supersub /usr/local/bin/supersub-hold /etc/supersub; do
  if [[ -e "$p" ]]; then echo "  🔴 남아 있음: $p"; left=1; fi
done
if systemctl list-unit-files 2>/dev/null | grep -q '^supersub-autostop'; then
  echo "  🔴 유닛이 아직 보인다"; left=1
fi
[[ $left -eq 0 ]] && echo "  전부 제거됨"

echo
cat <<'MSG'
제거 완료. 🔴 **이 인스턴스는 이제 스스로 꺼지지 않는다.**

끄는 법 (인스턴스 안에서):
  sudo shutdown -h now        # 종료 동작이 "중지" 면 stop 된다

되살리기:
  sudo ./agent/deploy/install_autostop.sh --shutdown-behavior-verified
  ( 기본값 30/120/12 로 돌아온다 — 위 [1/5] 출력의 값으로 고쳐 쓴다 )
MSG
