"""card/adapter/inbound/api/v1/card_router.py — 계약 문서 3장."""

from uuid import UUID, uuid4

import pytest

from app.card.adapter.outbound.stub.card_stub_repository import (
    DEMO_SLUG,
    reset_created_cards,
)

from app.core.security import issue_access_token
from tests.conftest import V1, error_code


class TestMyCard:
    def test_내_카드(self, client, auth):
        res = client.get(f"{V1}/me/card", headers=auth)
        assert res.status_code == 200
        assert res.json()["public_slug"] == DEMO_SLUG

    def test_인증이_필요하다(self, client):
        res = client.get(f"{V1}/me/card")
        assert res.status_code == 401
        assert error_code(res) == "UNAUTHORIZED"

    def test_카드가_없는_사용자면_404(self, client):
        # 예전에는 "Bearer stub-token-for-<uuid>" 를 손으로 적어 넣었다. 토큰에
        # 서명이 없어서 가능했던 것이고, **그건 곧 아무나 남의 id 로 인증할 수
        # 있었다는 뜻이다.** 이제는 서명된 토큰을 실제로 발급해서 쓴다.
        token = issue_access_token(UUID("00000000-0000-4000-8000-000000000000"))
        res = client.get(
            f"{V1}/me/card", headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 404
        assert error_code(res) == "CARD_NOT_FOUND"


class TestPublicCard:
    def test_인증_없이_보인다(self, client):
        assert client.get(f"{V1}/cards/{DEMO_SLUG}").status_code == 200

    def test_내부_id_가_없다(self, client):
        assert "id" not in client.get(f"{V1}/cards/{DEMO_SLUG}").json()

    def test_호칭이_최신순으로_나온다(self, client):
        titles = client.get(f"{V1}/cards/{DEMO_SLUG}").json()["titles"]
        assert [t["code"] for t in titles] == ["sharp_shooter", "weekend_regular"]

    def test_호칭_분류는_부록_D_의_값이다(self, client):
        titles = client.get(f"{V1}/cards/{DEMO_SLUG}").json()["titles"]
        assert {t["category"] for t in titles} <= {"강점", "활동", "용병"}

    def test_시각은_Z_로_끝난다(self, client):
        titles = client.get(f"{V1}/cards/{DEMO_SLUG}").json()["titles"]
        assert all(t["granted_at"].endswith("Z") for t in titles)

    def test_없는_슬러그면_404(self, client):
        res = client.get(f"{V1}/cards/no-such-slug")
        assert res.status_code == 404
        assert error_code(res) == "CARD_NOT_FOUND"


class TestCreateMyCard:
    """POST /me/card — 계약 문서 3-2절. 카드는 요청할 때 생긴다."""

    @pytest.fixture(autouse=True)
    def _clean_stub(self):
        """스텁이 만든 카드는 모듈에 남는다. 검사 사이에 새지 않게 비운다."""
        reset_created_cards()
        yield
        reset_created_cards()

    def _token(self, user_id=None) -> dict[str, str]:
        return {"Authorization": f"Bearer {issue_access_token(user_id or uuid4())}"}

    def test_인증이_필요하다(self, client):
        res = client.post(f"{V1}/me/card")
        assert res.status_code == 401
        assert error_code(res) == "UNAUTHORIZED"

    def test_없던_카드를_만들면_201(self, client):
        res = client.post(f"{V1}/me/card", headers=self._token())
        assert res.status_code == 201, res.text
        assert res.json()["public_slug"]

    def test_갓_만든_카드에는_호칭이_없다(self, client):
        """호칭은 분석 결과로 붙는다. 생성 시점에 있을 수 없다."""
        res = client.post(f"{V1}/me/card", headers=self._token())
        assert res.json()["titles"] == []

    def test_두_번째부터는_200_이고_슬러그가_같다(self, client):
        """멱등이다 — 재시도해도 공유 링크가 바뀌면 안 된다."""
        headers = self._token()
        first = client.post(f"{V1}/me/card", headers=headers)
        second = client.post(f"{V1}/me/card", headers=headers)
        assert (first.status_code, second.status_code) == (201, 200)
        assert first.json()["public_slug"] == second.json()["public_slug"]
        assert first.json()["id"] == second.json()["id"]

    def test_이미_카드가_있으면_그것을_돌려준다(self, client, auth):
        res = client.post(f"{V1}/me/card", headers=auth)
        assert res.status_code == 200
        assert res.json()["public_slug"] == DEMO_SLUG

    def test_만든_카드가_바로_조회된다(self, client):
        headers = self._token()
        created = client.post(f"{V1}/me/card", headers=headers).json()
        read = client.get(f"{V1}/me/card", headers=headers)
        assert read.status_code == 200
        assert read.json()["public_slug"] == created["public_slug"]

    def test_사람마다_슬러그가_다르다(self, client):
        a = client.post(f"{V1}/me/card", headers=self._token()).json()
        b = client.post(f"{V1}/me/card", headers=self._token()).json()
        assert a["public_slug"] != b["public_slug"]

    def test_수치가_실려_나가지_않는다(self, client):
        """부록 D.5 — 생성 응답도 조회와 같은 모델을 쓴다."""
        from app.card.domain.rules.card_rules import FORBIDDEN_CARD_FIELDS

        body = client.post(f"{V1}/me/card", headers=self._token()).json()
        assert not (set(body) & FORBIDDEN_CARD_FIELDS)
