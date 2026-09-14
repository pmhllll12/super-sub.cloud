"""`PATCH /me/card` — 카드 꾸미기(`style`). 미결 `paik` 3번 나머지.

스텁을 끼워 DB 없이 돈다. 실제 저장·공개 카드 반영은 `test_card_db.py` 가 본다.
`tagline`(`test_card_tagline_router.py`)과 같은 자리 — 여기는 **형식 검증**과
「보낸 필드만 바뀐다」를 본다.
"""

from __future__ import annotations

import pytest

from app.card.adapter.outbound.stub.card_stub_repository import reset_created_cards
from tests.conftest import V1, error_code

CARD = f"{V1}/me/card"

_STYLE = {
    "bg": "#91ea92",
    "logo": "#0b0b0b",
    "text_color": "#0b0b0b",
    "text_x": 50,
    "text_y": 34,
    "brush": 0,
    "brush_color": "#0b0b0b",
    "brush_scale": 1,
    "brush_x": 0,
    "brush_y": 0,
}


@pytest.fixture(autouse=True)
def _clean():
    reset_created_cards()
    yield
    reset_created_cards()


class TestUpdateStyle:
    def test_인증이_필요하다(self, client):
        assert client.patch(CARD, json={"style": _STYLE}).status_code == 401

    def test_꾸미기를_정한다(self, client, auth):
        res = client.patch(CARD, json={"style": _STYLE}, headers=auth)
        assert res.status_code == 200, res.text
        assert res.json()["style"] == _STYLE

        # 다시 읽어도 남아 있어야 한다.
        assert client.get(CARD, headers=auth).json()["style"] == _STYLE

    def test_null을_보내면_지운다(self, client, auth):
        client.patch(CARD, json={"style": _STYLE}, headers=auth)

        res = client.patch(CARD, json={"style": None}, headers=auth)
        assert res.status_code == 200, res.text
        assert res.json()["style"] is None

    def test_안_보내면_안_바뀐다(self, client, auth):
        client.patch(CARD, json={"style": _STYLE}, headers=auth)

        # `tagline` 만 보낸다 — `style` 은 요청 본문에 아예 없다.
        res = client.patch(CARD, json={"tagline": "x"}, headers=auth)
        assert res.status_code == 200, res.text
        assert res.json()["style"] == _STYLE, "안 보냈는데 지워지거나 바뀌었다"

    @pytest.mark.parametrize("field", ["bg", "logo", "text_color", "brush_color"])
    def test_색이_16진수가_아니면_422(self, client, auth, field):
        bad = {**_STYLE, field: "green"}
        res = client.patch(CARD, json={"style": bad}, headers=auth)
        assert res.status_code == 422
        assert error_code(res) == "VALIDATION_ERROR"

    def test_필드가_모자라면_422(self, client, auth):
        """🔴 화면이 늘 전체 값을 들고 있다가 보낸다 — 부분 병합을 안 하므로
        (포트 주석 참고) 일부만 보내면 나머지가 지워지는 대신 거부한다."""
        res = client.patch(CARD, json={"style": {"bg": "#91ea92"}}, headers=auth)
        assert res.status_code == 422
        assert error_code(res) == "VALIDATION_ERROR"

    def test_사진_관련_필드는_모른다(self, client, auth):
        """저장 위치가 아직 없다 — 조용히 무시하지 않고 거부한다."""
        res = client.patch(
            CARD, json={"style": {**_STYLE, "photo": "data:..."}}, headers=auth
        )
        assert res.status_code == 422
        assert error_code(res) == "VALIDATION_ERROR"

    def test_brush_scale_상한을_넘으면_422(self, client, auth):
        res = client.patch(
            CARD, json={"style": {**_STYLE, "brush_scale": 999}}, headers=auth
        )
        assert res.status_code == 422
        assert error_code(res) == "VALIDATION_ERROR"


class TestNoCard:
    def test_카드가_없으면_404_다(self, client):
        from uuid import uuid4

        from app.core.security import issue_access_token

        headers = {"Authorization": f"Bearer {issue_access_token(uuid4())}"}
        res = client.patch(CARD, json={"style": _STYLE}, headers=headers)
        assert res.status_code == 404
        assert error_code(res) == "CARD_NOT_FOUND"
