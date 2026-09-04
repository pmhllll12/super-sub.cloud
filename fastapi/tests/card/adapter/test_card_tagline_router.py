"""`PATCH /me/card` — 카드에서 사람이 정하는 한 줄. 미결 `paik` 3번.

스텁을 끼워 DB 없이 돈다. 실제 저장·공개 카드 반영은 `test_card_db.py` 가 본다.

## 이 검사가 보는 것

카드는 만들고 나면 **손댈 것이 하나도 없었다** — 별명이 화면의 붙박이 상수라
모든 카드가 글자까지 똑같았다. 그것을 여는 경로이고, 여는 김에 **열면 안 되는
것까지 열리지 않았는지**를 함께 본다.

🔴 **`public_slug` 는 못 바꾼다.** 이미 공유된 주소라 바꾸면 남이 가진 링크가
죽는다 — 계약이 슬러그를 무작위·멱등으로 둔 이유와 같다.
"""

from __future__ import annotations

import pytest

from app.card.adapter.outbound.stub.card_stub_repository import reset_created_cards
from tests.conftest import V1, error_code

CARD = f"{V1}/me/card"


@pytest.fixture(autouse=True)
def _clean():
    reset_created_cards()
    yield
    reset_created_cards()


class TestUpdateTagline:
    def test_인증이_필요하다(self, client):
        assert client.patch(CARD, json={"tagline": "x"}).status_code == 401

    def test_한_줄을_정한다(self, client, auth):
        res = client.patch(CARD, json={"tagline": "THREE LUNGS"}, headers=auth)
        assert res.status_code == 200, res.text
        assert res.json()["tagline"] == "THREE LUNGS"

        # 다시 읽어도 남아 있어야 한다.
        assert client.get(CARD, headers=auth).json()["tagline"] == "THREE LUNGS"

    def test_앞뒤_공백을_턴다(self, client, auth):
        res = client.patch(CARD, json={"tagline": "  숨은 왼발  "}, headers=auth)
        assert res.json()["tagline"] == "숨은 왼발"

    def test_빈_값은_지운_것으로_본다(self, client, auth):
        client.patch(CARD, json={"tagline": "지울 것"}, headers=auth)

        for empty in ("", "   ", None):
            res = client.patch(CARD, json={"tagline": empty}, headers=auth)
            assert res.status_code == 200, res.text
            assert res.json()["tagline"] is None, f"{empty!r} 가 안 지워졌다"

    def test_20자를_넘으면_422_다(self, client, auth):
        """🔴 조용히 자르지 않는다 — 쓴 것과 보이는 것이 달라지고, 알아차리는
        시점은 카드를 공유한 뒤다."""
        res = client.patch(CARD, json={"tagline": "가" * 21}, headers=auth)
        assert res.status_code == 422
        assert error_code(res) == "VALIDATION_ERROR"

    def test_20자는_된다(self, client, auth):
        res = client.patch(CARD, json={"tagline": "가" * 20}, headers=auth)
        assert res.status_code == 200


class TestWhatMustNotChange:
    """🔴 여는 김에 열리면 안 되는 것들."""

    def test_슬러그를_보내도_안_바뀐다(self, client, auth):
        before = client.get(CARD, headers=auth).json()

        res = client.patch(
            CARD,
            json={"tagline": "x", "public_slug": "내가-정한-주소"},
            headers=auth,
        )
        assert res.status_code == 200
        assert res.json()["public_slug"] == before["public_slug"]

    def test_이미지_키도_안_바뀐다(self, client, auth):
        before = client.get(CARD, headers=auth).json()
        res = client.patch(
            CARD, json={"tagline": "x", "og_image_key": "내키"}, headers=auth
        )
        assert res.json()["og_image_key"] == before["og_image_key"]

    def test_호칭은_사람이_못_고친다(self, client, auth):
        """호칭은 분석이 주는 것이다 — 요청으로 바꿀 수 있으면 뜻이 없어진다."""
        before = client.get(CARD, headers=auth).json()["titles"]
        res = client.patch(
            CARD, json={"tagline": "x", "titles": []}, headers=auth
        )
        assert res.json()["titles"] == before


class TestNoCard:
    def test_카드가_없으면_404_다(self, client):
        """🔴 **수정이 생성을 겸하지 않는다.** 만드는 자리는 `POST /me/card`
        하나다(3장) — 두 곳으로 흩어지면 "카드는 여기서만 생긴다"가 깨진다."""
        from uuid import uuid4

        from app.core.security import issue_access_token

        headers = {"Authorization": f"Bearer {issue_access_token(uuid4())}"}
        res = client.patch(CARD, json={"tagline": "x"}, headers=headers)
        assert res.status_code == 404
        assert error_code(res) == "CARD_NOT_FOUND"
