"""Super-Sub 백엔드 API 진입점.

**모든 엔드포인트가 PostgreSQL 에 붙어 있다** (2026-08-26 에 카드까지 옮기면서
스텁이 사라졌다). 스텁 구현은 테스트에서 저장소를 갈아끼울 때만 쓴다.
명세는 `docs/api-contract.md`, 구조 설명은 `README.md`.
"""

from fastapi import FastAPI

from app.card.adapter.inbound.api.v1.card_router import card_router
from app.card.adapter.outbound.stub.card_stub_repository import DEMO_SLUG
from app.core.config import settings
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.user.adapter.inbound.api.v1.admin_router import admin_router
from app.user.adapter.inbound.api.v1.auth_router import auth_router
from app.user.adapter.inbound.api.v1.me_router import me_router
from app.user.adapter.inbound.api.v1.team_router import team_router
from app.user.adapter.outbound.stub.user_stub_repository import (
    DEMO_EMAIL,
    DEMO_PASSWORD,
)

# 라우터가 붙기 전에 부른다 — 기동 중에 나는 로그도 형식을 갖추게 된다.
configure_logging()

API_PREFIX = "/api/v1"

# 대화형 문서와 데모 자격증명을 내보낼 환경. `scripts/seed_demo.py` 와 같은 기준이다.
#
# 🔴 `app_env` 의 기본값이 `local` 이므로 **배포 환경은 APP_ENV 를 반드시 넣어야
#    한다.** 빠뜨리면 개발 환경으로 간주돼 /docs 와 데모 계정이 그대로 열린다.
DEV_ENVS = frozenset({"local", "dev"})

_dev = settings.app_env in DEV_ENVS

_DESCRIPTION = """
생활체육 용병 스카우팅 플랫폼 백엔드.

**모든 엔드포인트가 PostgreSQL에 붙어 있습니다.** 고정 응답은 더 이상 없습니다.

구글 로그인(`POST /auth/google`)은 **`id_token`**(access_token 아님)을 받습니다.
서버에 `GOOGLE_CLIENT_IDS`가 없으면 503으로 떨어집니다.

실패 응답은 모두 `{"error": {"code": ..., "message": ...}}` 형태입니다.
`code`로 분기하고 `message`로 분기하지 마십시오.
"""

# 🔴 데모 계정의 비밀번호는 개발 환경에서만 문서에 넣는다. 운영에서는 /docs 자체를
#    끄지만, 설명 문자열에 값을 박아 두면 **끄는 것을 잊는 순간 그대로 노출된다.**
_DEMO_SECTION = f"""
아래 데모 계정과 카드는 개발 DB에 넣어 둔 실제 데이터입니다. **새로 가입해서 그
계정으로 로그인해도 됩니다.** 다른 값은 계약대로 실패합니다.

- 이메일 `{DEMO_EMAIL}` / 비밀번호 `{DEMO_PASSWORD}`
- 공개 카드 슬러그 `{DEMO_SLUG}`
"""

app = FastAPI(
    title="Super-Sub API",
    description=_DESCRIPTION + (_DEMO_SECTION if _dev else ""),
    version="0.1.0",
    # 운영에서는 대화형 문서를 아예 등록하지 않는다(None 이면 라우트가 없어 404 다).
    # 스키마 자체가 공격 표면이라 `openapi_url` 까지 함께 닫는다.
    docs_url="/docs" if _dev else None,
    redoc_url="/redoc" if _dev else None,
    openapi_url="/openapi.json" if _dev else None,
)

install_error_handlers(app)

# 컨텍스트가 늘면 여기에 한 줄씩 추가한다 (video · match · review · billing).
for _router in (auth_router, me_router, team_router, card_router, admin_router):
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
        # 2026-08-26 에 카드까지 DB 로 옮기면서 False 가 됐다. 필드를 지우지 않는
        # 이유는 클라이언트가 이미 읽고 있을 수 있어서다 — 계약에서 빼는 것은 별건이다.
        "stub": False,
    }
