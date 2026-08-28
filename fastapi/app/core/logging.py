"""로그 설정과 인증 사건 기록. 5장 SEC-010.

**남기지 않는 것: 비밀번호 · 토큰 · `Authorization` 헤더 · 요청 본문 · 쿼리 문자열.**
남길 수 있는 것은 사후 추적에 필요한 최소한 — 사건 이름, 에러 code, 메서드와 경로,
호출자 주소, 그리고 **이미 인증된** 사용자의 id 다.

🔴 **실패 로그에는 시도된 이메일을 남기지 않는다.** 공격자가 값을 정하는 자리라
로그가 그대로 오염되고, 남의 이메일이 우리 로그에 쌓인다. 남용 탐지는 주소로 한다
(SEC-009 의 요청 제한도 같은 기준을 쓴다).

⚠️ `client` 는 **직접 연결한 상대의 주소**다. 로드밸런서 뒤에 놓이면 전부 LB 주소로
찍히므로, 배포 시점에 `X-Forwarded-For` 를 신뢰하는 설정이 함께 필요하다.

`import logging` 은 표준 라이브러리를 가리킨다 — 절대 임포트라 이 모듈
(`app.core.logging`)과 겹치지 않는다.
"""

from __future__ import annotations

import logging
from typing import Any

from starlette.requests import Request

_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"

# 인증 사건 전용 로거. 이름을 나눠 두면 배포 환경에서 이 계통만 따로 뽑을 수 있다.
auth_logger = logging.getLogger("supersub.auth")

# 사후에 추적해야 하는 실패. 나머지 4xx(404·422)는 대개 평범한 오타라 같은 수준으로
# 남기면 **정작 봐야 할 것이 묻힌다.**
_SECURITY_STATUSES = frozenset({401, 403, 409, 429})


def configure_logging() -> None:
    """루트 로거를 설정한다.

    `basicConfig` 는 **핸들러가 이미 있으면 아무것도 하지 않는다** — uvicorn 이나
    pytest 가 붙여 둔 것을 덮어쓰지 않는다는 뜻이라 그대로 쓴다.
    """
    logging.basicConfig(level=logging.INFO, format=_FORMAT)


def _line(event: str, fields: dict[str, Any]) -> str:
    parts = [f"event={event}"]
    parts += [f"{key}={value}" for key, value in fields.items() if value is not None]
    return " ".join(parts)


def log_auth_event(event: str, **fields: Any) -> None:
    """성공한 인증 사건. 호출자가 넘기는 값만 남는다."""
    auth_logger.info(_line(event, fields))


def log_api_error(request: Request, status_code: int, code: str) -> None:
    """계약 에러(`ApiError`)를 한자리에서 남긴다.

    로그인 실패·토큰 거부가 전부 이 경로로 지나가므로 인터랙터마다 따로 적지 않는다.
    """
    level = logging.ERROR if status_code >= 500 else logging.INFO
    if status_code in _SECURITY_STATUSES:
        level = logging.WARNING

    auth_logger.log(
        level,
        _line(
            "api_error",
            {
                "code": code,
                "status": status_code,
                "method": request.method,
                # 쿼리 문자열은 빼고 경로만 남긴다.
                "path": request.url.path,
                "client": request.client.host if request.client else None,
            },
        ),
    )
