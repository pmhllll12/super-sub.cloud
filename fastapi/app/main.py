"""Super-Sub 백엔드 API 진입점.

지금은 앱이 뜨는 것까지만 확인한다. 실제 엔드포인트는 API 계약을 팀과 맞춘 뒤 붙인다.
"""

from fastapi import FastAPI

from app.config import settings

app = FastAPI(
    title="Super-Sub API",
    description="생활체육 용병 스카우팅 플랫폼 백엔드",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, object]:
    """앱 기동 확인용.

    DB 연결까지는 확인하지 않는다 — 아직 붙을 인스턴스가 없다.
    `db_configured`는 접속 정보가 채워졌는지만 알려준다.
    """
    return {
        "status": "ok",
        "env": settings.app_env,
        "db_configured": settings.db_configured,
    }
