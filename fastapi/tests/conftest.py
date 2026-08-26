from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.user.adapter.outbound.stub.user_stub_repository import (
    DEMO_EMAIL,
    DEMO_PASSWORD,
)

V1 = "/api/v1"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


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
