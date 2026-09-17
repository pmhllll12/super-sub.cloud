"""user/adapter/inbound/api/v1/contacts_router.py — 계약 문서 3-12절.

**엔드포인트를 추가하면 성공 1건 + 실패 최소 1건을 같이 넣는다**
(`test_auth_router.py`와 같은 관례).
"""

from __future__ import annotations

import uuid

from tests.conftest import V1, error_code

# 스텁의 get()이 "존재하는 남"으로 인식하는 유일한 타인 id.
_OTHER_USER_ID = "9a2e5f31-6d70-4c18-b3a9-4e82d7c05a17"


class TestRequestContact:
    def test_성공하면_201(self, client, auth):
        res = client.post(
            f"{V1}/me/contacts",
            json={"target_user_id": _OTHER_USER_ID, "note": "같은 동네"},
            headers=auth,
        )
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["accepted_at"] is None
        assert body["note"] == "같은 동네"

    def test_자기_자신에게는_422(self, client, auth):
        me = client.get(f"{V1}/me", headers=auth).json()
        res = client.post(
            f"{V1}/me/contacts", json={"target_user_id": me["id"]}, headers=auth
        )
        assert res.status_code == 422
        assert error_code(res) == "CANNOT_REQUEST_SELF"

    def test_없는_사용자면_404(self, client, auth):
        # 스텁의 get()은 DEMO_USER_ID·_OTHER_USER_ID 말고는 전부 None을 돌려준다.
        res = client.post(
            f"{V1}/me/contacts", json={"target_user_id": str(uuid.uuid4())}, headers=auth
        )
        assert res.status_code == 404
        assert error_code(res) == "USER_NOT_FOUND"

    def test_인증_없으면_401(self, client):
        res = client.post(
            f"{V1}/me/contacts", json={"target_user_id": str(uuid.uuid4())}
        )
        assert res.status_code == 401


class TestAcceptContact:
    def test_성공하면_200(self, client, auth):
        # 스텁의 find_contact_by_id는 이 고정 id에 대해 대기중 신청을 돌려준다.
        contact_id = "6e1a2b3c-4d5e-4f60-8a71-2b3c4d5e6f71"
        res = client.post(f"{V1}/me/contacts/{contact_id}/accept", headers=auth)
        assert res.status_code == 200, res.text
        assert res.json()["accepted_at"] is not None

    def test_없는_신청이면_404(self, client, auth):
        res = client.post(
            f"{V1}/me/contacts/{uuid.uuid4()}/accept", headers=auth
        )
        assert res.status_code == 404
        assert error_code(res) == "CONTACT_NOT_FOUND"


class TestListContacts:
    def test_목록이_배열이다(self, client, auth):
        res = client.get(f"{V1}/me/contacts", headers=auth)
        assert res.status_code == 200, res.text
        assert isinstance(res.json()["items"], list)

    def test_인증_없으면_401(self, client):
        res = client.get(f"{V1}/me/contacts")
        assert res.status_code == 401


class TestListContactRequests:
    def test_목록이_배열이다(self, client, auth):
        res = client.get(f"{V1}/me/contacts/requests", headers=auth)
        assert res.status_code == 200, res.text
        assert isinstance(res.json(), list)


class TestContactCardSlug:
    """지인 목록에 **카드 슬러그**가 실린다 (미결 `paik` 39번, 백성검 요청).

    🔴 홈 스쿼드 판이 앉은 사람의 **진짜 카드**를 그리는데, 지인으로 앉힌
    사람만 찾아갈 값이 없어 이름표로 남았다 — 같은 판 안에서 어디서
    앉혔느냐에 따라 카드가 뜨기도 안 뜨기도 하면 안 된다.
    """

    def test_카드가_있으면_슬러그가_실린다(self, client, auth):
        res = client.get(f"{V1}/me/contacts", headers=auth)
        assert res.status_code == 200, res.text
        items = res.json()["items"]
        assert items, "스텁 지인이 한 명은 있어야 이 시험이 뜻이 있다"
        # 🔴 **내부 id 가 아니라 슬러그다** — 밖으로 나가는 것은 슬러그뿐이다.
        assert items[0]["card_public_slug"] == "kim-chulsoo-1a2b"

    def test_칸_자체는_늘_있다(self, client, auth):
        """카드를 안 만든 사람은 `null` 이다 — **빠지는 것이 아니라 null** 이라
        화면이 「아직 못 받았다」와 「카드가 없다」를 가를 수 있다."""
        items = client.get(f"{V1}/me/contacts", headers=auth).json()["items"]
        for row in items:
            assert "card_public_slug" in row
