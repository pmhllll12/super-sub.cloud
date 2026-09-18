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

# 사진 다섯 칸의 **기본값**(2026-09-18). 🔴 안 보내도 응답에는 늘 실린다 —
# 기본값이 있어야 지금 돌고 있는 클라이언트가 422 를 안 맞는다(스키마 주석).
_PHOTO_DEFAULTS = {
    "photo_key": None,
    "photo_scale": 1,
    "photo_x": 0,
    "photo_y": 0,
    "mode": "cutout",
}

# 사진 칸까지 채운 값 — 「보낸 대로 남는가」를 볼 때 쓴다.
_STYLE_WITH_PHOTO = {
    **_STYLE,
    "photo_key": None,
    "photo_scale": 1.4,
    "photo_x": -12,
    "photo_y": 8,
    "mode": "full",
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
        # 🔴 **사진 칸을 안 보내도 기본값이 실려 온다**(2026-09-18) — 보낸
        # 아홉은 그대로고 다섯이 더 붙는다.
        assert res.json()["style"] == {**_STYLE, **_PHOTO_DEFAULTS}

        # 다시 읽어도 남아 있어야 한다.
        assert client.get(CARD, headers=auth).json()["style"] == {
            **_STYLE,
            **_PHOTO_DEFAULTS,
        }

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
        assert res.json()["style"] == {
            **_STYLE,
            **_PHOTO_DEFAULTS,
        }, "안 보냈는데 지워지거나 바뀌었다"

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


class TestPhotoStyle:
    """사진 다섯 칸 (2026-09-18, 사용자 요청).

    🔴 **바이트는 여기 안 담는다** — `style` 에는 S3 키만 온다. data URL 로
    담으면 카드를 읽는 모든 응답에 사진이 실린다(스쿼드 판은 한 번에 5~7장).
    """

    def test_안_보내면_기본값이_된다(self, client, auth):
        """🔴 **이것이 깨지면 지금 돌고 있는 클라이언트가 전부 422 다.**"""
        res = client.patch(CARD, json={"style": _STYLE}, headers=auth)
        assert res.status_code == 200, res.text
        assert res.json()["style"]["mode"] == "cutout"
        assert res.json()["style"]["photo_key"] is None

    def test_보낸_대로_남는다(self, client, auth):
        res = client.patch(CARD, json={"style": _STYLE_WITH_PHOTO}, headers=auth)
        assert res.status_code == 200, res.text
        got = res.json()["style"]
        assert got["mode"] == "full"
        assert got["photo_scale"] == 1.4
        assert got["photo_x"] == -12

    def test_모르는_모드는_422(self, client, auth):
        bad = {**_STYLE, "mode": "background"}
        res = client.patch(CARD, json={"style": bad}, headers=auth)
        assert res.status_code == 422
        assert error_code(res) == "VALIDATION_ERROR"

    def test_사진_자리는_음수가_된다(self, client, auth):
        """글자 자리(`text_x`)와 다르다 — 사진은 칸보다 크게 잡아 밀어 넣는다."""
        res = client.patch(
            CARD, json={"style": {**_STYLE, "photo_x": -40}}, headers=auth
        )
        assert res.status_code == 200, res.text
        assert res.json()["style"]["photo_x"] == -40

    def test_키가_너무_길면_422(self, client, auth):
        bad = {**_STYLE, "photo_key": "cards/photos/" + "x" * 300}
        res = client.patch(CARD, json={"style": bad}, headers=auth)
        assert res.status_code == 422
