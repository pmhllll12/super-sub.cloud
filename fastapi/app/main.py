"""Super-Sub 백엔드 API 진입점.

지금은 **스텁**이다. 모든 응답이 고정값이고 DB에 붙지 않는다.
명세는 `docs/api-contract.md`, 구조 설명은 `README.md`.
"""

from fastapi import FastAPI

from app.card.adapter.inbound.api.v1.card_router import card_router
from app.card.adapter.outbound.repositories.card_stub_repository import DEMO_SLUG
from app.config import settings
from app.errors import install_error_handlers
from app.user.adapter.inbound.api.v1.auth_router import auth_router
from app.user.adapter.inbound.api.v1.me_router import me_router
from app.user.adapter.outbound.repositories.user_stub_repository import (
    DEMO_EMAIL,
    DEMO_PASSWORD,
)

API_PREFIX = "/api/v1"

_DESCRIPTION = f"""
생활체육 용병 스카우팅 플랫폼 백엔드.

> ⚠️ **현재 모든 응답이 스텁(고정값)입니다.** DB에 붙지 않습니다.

성공 경로를 보려면 아래 값으로 로그인하십시오. 다른 값은 계약대로 실패합니다.

- 이메일 `{DEMO_EMAIL}` / 비밀번호 `{DEMO_PASSWORD}`
- 공개 카드 슬러그 `{DEMO_SLUG}`

실패 응답은 모두 `{{"error": {{"code": ..., "message": ...}}}}` 형태입니다.
`code`로 분기하고 `message`로 분기하지 마십시오.
"""

app = FastAPI(
    title="Super-Sub API",
    description=_DESCRIPTION,
    version="0.1.0",
)

install_error_handlers(app)

# 컨텍스트가 늘면 여기에 한 줄씩 추가한다 (video · match · review · billing).
for _router in (auth_router, me_router, card_router):
    app.include_router(_router, prefix=API_PREFIX)


@app.get("/health", tags=["health"])
def health() -> dict[str, object]:
    """앱 기동 확인용.

    DB 연결까지는 확인하지 않는다 — 아직 붙을 인스턴스가 없다.
    `db_configured`는 접속 정보가 채워졌는지만 알려준다.
    """
    return {
        "status": "ok",
        "env": settings.app_env,
        "db_configured": settings.db_configured,
        "stub": True,
    }
