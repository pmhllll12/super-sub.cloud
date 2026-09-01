"""인증 엔드포인트 요청 제한. 5장 SEC-009.

비밀번호 해싱(bcrypt)은 **일부러 느리다.** 그래서 인증 요청 자체가 CPU 를 태우는
수단이 된다 — 로그인 폭주 하나로 서비스 전체가 느려질 수 있다.

**계정 잠금 방식은 쓰지 않는다.** 남의 이메일을 아는 것만으로 그 계정을 잠글 수 있어
그 자체가 서비스 거부 수단이 된다. 제한은 **출처(주소) 기준**이다 — 인증 사건 로깅이
이메일 대신 주소를 남기는 것과 같은 기준이다(`app/core/logging.py`).

🔴 **프로세스 안에서만 센다.** 워커를 여러 개 띄우면 워커마다 따로 세므로 실효
한도가 그만큼 늘어난다. 여러 대로 늘리는 시점에는 공유 저장소(Redis 등)가 필요하다.
지금은 단일 프로세스라 이 형태로 충분하고, **없는 것보다 훨씬 낫다.**

미들웨어가 아니라 **라우터 의존성**으로 붙인다. 미들웨어에서 던진 예외는
`install_error_handlers` 가 잡지 못해 에러 봉투를 여기서 또 만들어야 하고(형태가
갈라진다), 경로를 문자열로 맞춰야 한다. 라우터에 달면 **그 라우터에 추가되는
엔드포인트가 자동으로 포함된다.**
"""

from __future__ import annotations

import math
import threading
import time
from collections import deque

from fastapi import Request

from app.core.errors import ApiError

# 사람이 로그인 화면에서 내는 요청은 분당 한두 번이다. 오타를 여러 번 내는 경우까지
# 감안해도 10 이면 넉넉하고, 자동화된 폭주는 이 선에서 걸린다.
AUTH_LIMIT = 10
AUTH_WINDOW_SECONDS = 60.0

# 이 수를 넘으면 오래된 출처를 쓸어낸다. 안 쓸면 **주소를 바꿔 가며 보내는 쪽이
# 메모리를 늘릴 수 있다** — 막으려는 것과 같은 종류의 공격이 된다.
_SWEEP_AT = 1024


class SlidingWindowLimiter:
    """최근 `window` 초 안의 요청 수를 센다.

    고정 창(매 분 0초에 초기화)은 창 경계에서 한도의 두 배가 통과한다. 기록을
    들고 있다가 지나간 것만 버리는 쪽이 그 구멍이 없고, 한도가 작아서 기록도 작다.
    """

    def __init__(self, limit: int, window_seconds: float) -> None:
        self._limit = limit
        self._window = window_seconds
        self._hits: dict[str, deque[float]] = {}
        # 동기 엔드포인트는 스레드풀에서 돌아 같은 키에 동시에 닿을 수 있다.
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """한도를 넘었으면 `ApiError(429)` 를 던진다. 넘지 않았으면 한 번 센다."""
        now = time.monotonic()
        with self._lock:
            if len(self._hits) > _SWEEP_AT:
                self._sweep(now)

            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] >= self._window:
                hits.popleft()

            if len(hits) >= self._limit:
                # 🔴 **거부된 요청은 세지 않는다**(여기서 append 하지 않는다).
                #    세면 재시도할수록 창이 밀려 영영 안 풀린다 — 오타를 반복한
                #    사람이 그 사이 아무것도 못 하게 된다.
                #
                # 가장 오래된 기록이 창을 벗어나면 자리가 하나 난다. 그때까지의
                # 시간을 **올림해서** 초로 알려 준다 — 내림하면 그 시각에 다시
                # 걸린다.
                wait = self._window - (now - hits[0])
                retry_after = max(1, math.ceil(wait))
                raise ApiError(
                    429,
                    "TOO_MANY_REQUESTS",
                    "요청이 너무 잦습니다. 잠시 후 다시 시도해 주세요.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)

    def reset(self) -> None:
        """전부 잊는다. 테스트에서 각 검사를 같은 조건에서 시작시키는 용도다."""
        with self._lock:
            self._hits.clear()

    def _sweep(self, now: float) -> None:
        stale = [
            key
            for key, hits in self._hits.items()
            if not hits or now - hits[-1] >= self._window
        ]
        for key in stale:
            del self._hits[key]


auth_limiter = SlidingWindowLimiter(AUTH_LIMIT, AUTH_WINDOW_SECONDS)


def limit_auth_requests(request: Request) -> None:
    """`auth_router` 전체에 붙는 의존성.

    경로별로 따로 센다. 한 엔드포인트로 몰린 요청이 다른 엔드포인트까지 막으면,
    구글 로그인을 재시도하던 사람이 비밀번호 로그인도 못 하게 된다.

    ⚠️ `request.client.host` 는 **직접 연결한 상대**의 주소다. 로드밸런서 뒤에서는
    전부 같은 주소로 보여 제한이 사실상 전체 한도가 된다 — 배포 시점에
    `X-Forwarded-For` 를 신뢰하는 설정이 함께 필요하다(로깅과 같은 사정).
    """
    client = request.client.host if request.client else "unknown"
    auth_limiter.check(f"{client} {request.url.path}")
