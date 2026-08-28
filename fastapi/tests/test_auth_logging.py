"""인증 사건이 로그에 남는지, 그리고 **비밀·개인정보가 안 남는지**. 5장 SEC-010.

로그는 사고가 난 뒤에야 없는 것을 알게 되는 자리라 검사로 고정해 둔다.
**남는지**뿐 아니라 **안 남아야 할 것이 안 남는지**를 같이 본다 — 뒤쪽이 SEC-010 이
명시한 확인 방법이다.
"""

import logging

import pytest

from app.user.adapter.outbound.stub.user_stub_repository import (
    DEMO_EMAIL,
    DEMO_PASSWORD,
)
from tests.conftest import V1

# 로그에 섞이면 눈에 띄도록 실제로 쓰지 않는 값을 쓴다.
SECRET_PASSWORD = "nunca-en-el-log-123"


AUTH_LOGGER = "supersub.auth"


@pytest.fixture
def logs(caplog):
    """인증 로거를 INFO 까지 잡는다. 기본값(WARNING)이면 성공 사건이 안 잡힌다."""
    caplog.set_level(logging.INFO, logger=AUTH_LOGGER)
    return caplog


def levels(logs) -> list[str]:
    """우리 로거가 남긴 것만 본다 — httpx 등 남의 로거도 caplog 에 함께 들어온다."""
    return [r.levelname for r in logs.records if r.name == AUTH_LOGGER]


class TestSuccess:
    def test_로그인_성공이_사용자_id_와_함께_남는다(self, client, logs):
        res = client.post(
            f"{V1}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
        )
        assert res.status_code == 200

        assert "event=login_success" in logs.text
        assert "user_id=" in logs.text
        # 🔴 발급한 토큰은 로그에 남으면 안 된다 — 그 자체가 인증 수단이다.
        assert res.json()["access_token"] not in logs.text

    def test_가입_성공이_남는다(self, client, logs):
        res = client.post(
            f"{V1}/auth/signup",
            json={
                "email": "logging-test@example.com",
                "password": SECRET_PASSWORD,
                "nickname": "로그시험",
            },
        )
        assert res.status_code == 201
        assert "event=signup_success" in logs.text


class TestFailure:
    def test_로그인_실패가_경고로_남는다(self, client, logs):
        res = client.post(
            f"{V1}/auth/login",
            json={"email": DEMO_EMAIL, "password": SECRET_PASSWORD},
        )
        assert res.status_code == 401

        assert "code=INVALID_CREDENTIALS" in logs.text
        assert "path=/api/v1/auth/login" in logs.text
        assert levels(logs) == ["WARNING"]

    def test_토큰_거부가_남는다(self, client, logs):
        res = client.get(f"{V1}/me", headers={"Authorization": "Bearer not-a-token"})
        assert res.status_code == 401

        assert "code=INVALID_TOKEN" in logs.text

    def test_평범한_404_는_경고가_아니다(self, client, logs):
        """404·422 까지 경고로 남기면 정작 봐야 할 401 이 묻힌다."""
        res = client.get(f"{V1}/cards/no-such-slug")
        assert res.status_code == 404

        assert levels(logs) == ["INFO"]


class TestNoSecrets:
    """SEC-010 의 확인 방법 그대로 — 로그에 비밀번호·`Bearer`·이메일이 없는지."""

    def test_비밀번호와_토큰과_이메일이_로그에_없다(self, client, logs):
        client.post(
            f"{V1}/auth/signup",
            json={
                "email": "secret-check@example.com",
                "password": SECRET_PASSWORD,
                "nickname": "비밀검사",
            },
        )
        client.post(
            f"{V1}/auth/login",
            json={"email": "secret-check@example.com", "password": SECRET_PASSWORD},
        )
        client.post(
            f"{V1}/auth/login",
            json={"email": "secret-check@example.com", "password": "wrong-password"},
        )
        client.get(f"{V1}/me", headers={"Authorization": "Bearer leaked-token-value"})

        assert SECRET_PASSWORD not in logs.text
        assert "Bearer" not in logs.text
        assert "leaked-token-value" not in logs.text
        # 실패 로그에 시도된 이메일을 남기지 않는다 — 공격자가 값을 정하는 자리다.
        assert "secret-check@example.com" not in logs.text
