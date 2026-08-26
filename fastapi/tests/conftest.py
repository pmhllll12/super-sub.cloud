from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.user.adapter.outbound.stub.user_stub_repository import (
    DEMO_EMAIL,
    DEMO_PASSWORD,
    StubUserRepository,
)
from app.user.dependencies.user_repository_provider import get_user_repository

V1 = "/api/v1"

# 테스트는 `.env` 에 의존하지 않는다. 시크릿이 없으면 여기서 채운다 —
# 없으면 토큰 발급이 503 이라 계약 테스트가 통째로 무너진다.
if not settings.jwt_secret:
    settings.jwt_secret = "test-only-secret-not-for-deploy"


@pytest.fixture
def client() -> TestClient:
    """**저장소를 스텁으로 갈아끼운 클라이언트.**

    계약(응답 형태·에러 코드·인증 흐름)을 검사하는 테스트는 DB 없이 돌아야 한다.
    실제 PostgreSQL 구현은 `@pytest.mark.db` 가 붙은 테스트가 따로 검사한다.
    """
    app.dependency_overrides[get_user_repository] = StubUserRepository
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_user_repository, None)


@pytest.fixture
def auth(client: TestClient) -> dict[str, str]:
    res = client.post(
        f"{V1}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
    )
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def error_code(res) -> str:
    """계약의 에러 봉투에서 code 를 꺼낸다. 형태가 다르면 여기서 터진다."""
    body = res.json()
    assert set(body) == {"error"}, f"에러 봉투가 아니다: {body}"
    assert set(body["error"]) == {"code", "message"}
    return body["error"]["code"]


# ---------------------------------------------------------------------------
# 실제 PostgreSQL 을 쓰는 테스트용. `@pytest.mark.db` 와 함께 쓴다.
# DB 가 없는 환경에서는 **실패가 아니라 skip** 이다 — 영원히 실패하는 검사는
# 아무도 안 돌리게 되고, 그러면 없느니만 못하다.
# ---------------------------------------------------------------------------


@pytest.fixture
def db_client() -> TestClient:
    """스텁을 끼우지 않은 클라이언트. 진짜 저장소가 들어간다."""
    from sqlalchemy.exc import SQLAlchemyError

    from app.core.database import engine_or_none

    engine = engine_or_none()
    if engine is None:
        pytest.skip("DATABASE_URL 이 설정되지 않았다")
    try:
        with engine.connect():
            pass
    except SQLAlchemyError as exc:
        pytest.skip(f"PostgreSQL 에 접속할 수 없다: {exc.__class__.__name__}")

    return TestClient(app)


@pytest.fixture
def db_session():
    """검증용 세션. 앱이 저장한 것을 밖에서 직접 확인할 때 쓴다."""
    from sqlalchemy.orm import Session

    from app.core.database import engine_or_none

    engine = engine_or_none()
    if engine is None:
        pytest.skip("DATABASE_URL 이 설정되지 않았다")
    with Session(engine) as session:
        yield session
