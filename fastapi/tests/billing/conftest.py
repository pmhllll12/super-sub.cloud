"""과금 계약 테스트 전용 fixture.

🔴 **`app.main.app` 을 쓰지 않는다.** `billing_router` 는 아직 `app/main.py` 에
등록돼 있지 않다 — 공유 파일 5곳(`fastapi/CLAUDE.md`)은 정어진이 배선하기로
되어 있어서다. 그때까지 계약을 확인할 수 있도록, 이 라우터 하나만 올린
**별도의 작은 앱**을 여기서 만든다. `app/main.py`가 하는 일 중 이 라우터가
필요로 하는 것(에러 봉투 형식·인증)만 그대로 재현한다.

`app/main.py`에 등록되면 이 fixture는 지워지고 전역 `client`(tests/conftest.py)
로 옮기면 된다 — 그 전까지는 이 파일이 대체한다.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.billing.adapter.inbound.api.v1.billing_router import billing_router
from app.billing.adapter.outbound.stub.billing_stub_repository import (
    StubBillingRepository,
    reset_billing,
)
from app.billing.dependencies.billing_providers import get_billing_repository
from app.core.config import settings
from app.core.deps import (
    get_token_version_reader,
    get_user_email_reader,
)
from app.core.errors import install_error_handlers
from tests.conftest import DEMO_EMAIL, _stub_token_version_reader, _stub_user_email_reader

V1 = "/api/v1"

if not settings.jwt_secret:
    settings.jwt_secret = "test-only-secret-not-for-deploy"


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    install_error_handlers(app)
    app.include_router(billing_router, prefix=V1)
    app.dependency_overrides[get_billing_repository] = StubBillingRepository
    app.dependency_overrides[get_token_version_reader] = _stub_token_version_reader
    app.dependency_overrides[get_user_email_reader] = _stub_user_email_reader
    reset_billing()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
