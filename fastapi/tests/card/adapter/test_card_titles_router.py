"""`PATCH /me/card` 의 `titles` — 사람이 직접 적는 호칭. `paik` 36번.

스텁을 끼워 DB 없이 돈다. 실제 저장·공개 카드 반영은 `test_card_db.py` 가 본다.

## 이 검사가 보는 것

팀이 방향을 뒤집었다(2026-09-16) — **호칭은 분석이 주는 것이 아니라 사용자
본인이 적는다.** 그래서 `paik` 32번(분석이 붙이게 해 달라)은 ⛔ 로 닫혔고
쓰는 경로가 필요해졌다.

🔴 **`tagline` 을 재활용하지 않았다.** 그 칸은 카드 가운데 큰 글자로 이미
쓰이고 있어서 겹쳐 쓰면 둘 중 하나를 잃는다(그 항목의 「하지 말 것」).
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


def _labels(body: dict) -> list[str]:
    """직접 적은 호칭만 골라 낸다 — 부여된 호칭과 한 목록에 섞여 온다."""
    return [t["label"] for t in body["titles"] if t["category"] is None]


class TestWriteTitles:
    def test_인증이_필요하다(self, client):
        assert client.patch(CARD, json={"titles": ["x"]}).status_code == 401

    def test_적으면_카드에_실린다(self, client, auth):
        res = client.patch(
            CARD, json={"titles": ["시야가 넓은", "왼발잡이"]}, headers=auth
        )
        assert res.status_code == 200, res.text
        assert _labels(res.json()) == ["시야가 넓은", "왼발잡이"]

        # 다시 읽어도 남아 있어야 한다.
        assert _labels(client.get(CARD, headers=auth).json()) == [
            "시야가 넓은",
            "왼발잡이",
        ]

    def test_직접_적은_것은_분류가_없고_code_가_custom_으로_시작한다(
        self, client, auth
    ):
        """🔴 분류를 사람에게 묻지 않기로 했다(그 항목의 「하지 말 것」).

        부여된 호칭과 한 목록에 오므로 화면이 가를 수단이 필요하다.
        """
        body = client.patch(CARD, json={"titles": ["왼발잡이"]}, headers=auth).json()
        written = next(t for t in body["titles"] if t["category"] is None)
        assert written["code"].startswith("custom:")
        assert written["label"] == "왼발잡이"

    def test_통째로_갈아_끼운다(self, client, auth):
        """부분 병합이 아니다 — 보낸 목록이 그대로 남는다."""
        client.patch(CARD, json={"titles": ["왼발잡이", "시야가 넓은"]}, headers=auth)
        res = client.patch(CARD, json={"titles": ["오른발잡이"]}, headers=auth)
        assert _labels(res.json()) == ["오른발잡이"]

    def test_빈_목록이면_지운다(self, client, auth):
        client.patch(CARD, json={"titles": ["왼발잡이"]}, headers=auth)
        res = client.patch(CARD, json={"titles": []}, headers=auth)
        assert _labels(res.json()) == []

    def test_null_이면_지운다(self, client, auth):
        client.patch(CARD, json={"titles": ["왼발잡이"]}, headers=auth)
        res = client.patch(CARD, json={"titles": None}, headers=auth)
        assert _labels(res.json()) == []

    def test_안_보내면_안_건드린다(self, client, auth):
        """`tagline` 만 고치는 요청이 호칭을 지우면 안 된다."""
        client.patch(CARD, json={"titles": ["왼발잡이"]}, headers=auth)
        res = client.patch(CARD, json={"tagline": "THREE LUNGS"}, headers=auth)
        assert res.json()["tagline"] == "THREE LUNGS"
        assert _labels(res.json()) == ["왼발잡이"]

    def test_부여된_호칭은_안_건드린다(self, client, auth):
        """🔴 다른 테이블이고 다른 뜻이다 — 직접 적은 것만 갈아 끼운다."""
        before = client.get(CARD, headers=auth).json()
        granted = [t["code"] for t in before["titles"] if t["category"] is not None]
        assert granted, "데모 카드에 부여된 호칭이 있어야 이 검사가 뜻이 있다"

        after = client.patch(CARD, json={"titles": ["왼발잡이"]}, headers=auth).json()
        assert [
            t["code"] for t in after["titles"] if t["category"] is not None
        ] == granted

    def test_앞뒤_공백을_턴다(self, client, auth):
        res = client.patch(CARD, json={"titles": ["  왼발잡이  "]}, headers=auth)
        assert _labels(res.json()) == ["왼발잡이"]

    def test_빈_글자는_버린다(self, client, auth):
        res = client.patch(CARD, json={"titles": ["왼발잡이", "   "]}, headers=auth)
        assert _labels(res.json()) == ["왼발잡이"]

    def test_같은_글은_하나만_남는다(self, client, auth):
        res = client.patch(
            CARD, json={"titles": ["왼발잡이", "왼발잡이"]}, headers=auth
        )
        assert _labels(res.json()) == ["왼발잡이"]

    def test_개수_상한을_넘으면_422(self, client, auth):
        res = client.patch(
            CARD, json={"titles": ["하나", "둘", "셋", "넷"]}, headers=auth
        )
        assert res.status_code == 422

    def test_길이_상한을_넘으면_422(self, client, auth):
        res = client.patch(CARD, json={"titles": ["가" * 21]}, headers=auth)
        assert res.status_code == 422

    def test_카드가_없으면_404(self, client):
        """카드를 여기서 만들지 않는다 — 만드는 자리는 `POST /me/card` 하나다."""
        from uuid import uuid4

        from app.core.security import issue_access_token

        headers = {"Authorization": f"Bearer {issue_access_token(uuid4())}"}
        res = client.patch(CARD, json={"titles": ["왼발잡이"]}, headers=headers)
        assert res.status_code == 404
        assert error_code(res) == "CARD_NOT_FOUND"
