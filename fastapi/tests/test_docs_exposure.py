"""운영 환경에서 대화형 문서와 데모 자격증명이 닫히는지 검사한다.

`app` 은 임포트 시점에 만들어지므로 환경을 바꾼 효과를 보려면 **모듈을 다시
불러와야 한다.** 검사가 끝나면 원래 환경으로 되돌린다 — 되돌리지 않으면 뒤에
오는 테스트가 운영 설정의 앱을 보게 된다.
"""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

import app.main
from app.core.config import settings
from app.user.adapter.outbound.stub.user_stub_repository import DEMO_PASSWORD


@pytest.fixture
def main_module(request):
    """`APP_ENV` 를 갈아끼우고 다시 불러온 `app.main`."""
    original = settings.app_env
    settings.app_env = request.param
    try:
        yield importlib.reload(app.main)
    finally:
        settings.app_env = original
        importlib.reload(app.main)


@pytest.mark.parametrize("main_module", ["production"], indirect=True)
def test_운영에서는_문서_경로가_등록되지_않는다(main_module):
    client = TestClient(main_module.app)

    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404, f"{path} 가 열려 있다"


@pytest.mark.parametrize("main_module", ["production"], indirect=True)
def test_운영_설명에는_데모_비밀번호가_없다(main_module):
    assert DEMO_PASSWORD not in (main_module.app.description or "")


@pytest.mark.parametrize("main_module", ["local"], indirect=True)
def test_개발에서는_문서와_데모_계정이_그대로다(main_module):
    """반대쪽도 함께 검사한다 — 늘 404 를 내는 앱은 위 검사를 통과시켜 버린다."""
    client = TestClient(main_module.app)

    assert client.get("/docs").status_code == 200
    assert DEMO_PASSWORD in main_module.app.description
