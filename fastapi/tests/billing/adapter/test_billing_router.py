"""과금 경로. 계약 3-10절.

스텁을 끼워 DB 없이 돈다. `analysis_credit`·`coach_referral`의 유일 제약
없음(중복 허용)이 **실제로 DB에도 그런지**는 이 파일이 아니라 `test_billing_db.py`
가 본다 — 여기는 계약(응답 형태·에러 코드·인증 흐름)만 본다.

## 이 검사가 보는 것

1. **크레딧 잔량은 `history`의 `delta` 합이다** — 별도 컬럼이 없다(부록 D.4)
2. **크레딧 조정은 관리자만** 한다 — 분석 경로와 이어지지 않는다(패킷 A 「하지 말 것」)
3. **코치에 종목·가격 같은 값이 없다** — `id`·`name`·`contact` 뿐이다(부록 D)
4. **코치 연결 요청은 중복을 막지 않는다**
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.billing.adapter.outbound.stub.billing_stub_repository import (
    referrals_of,
    register_coach,
    register_user,
)
from app.billing.domain.entities.billing_entity import CoachEntity
from app.core.config import settings
from app.core.security import issue_access_token
from app.user.adapter.outbound.stub.user_stub_repository import (
    DEMO_EMAIL,
    DEMO_USER_ID,
)
from tests.billing.conftest import V1

CREDITS = f"{V1}/credits"
ADJUSTMENTS = f"{V1}/admin/credits/adjustments"
COACHES = f"{V1}/coaches"


def _headers(user_id=None):
    return {"Authorization": f"Bearer {issue_access_token(user_id or uuid4())}"}


@pytest.fixture
def as_admin():
    original = settings.admin_emails
    settings.admin_emails = DEMO_EMAIL
    try:
        yield
    finally:
        settings.admin_emails = original


@pytest.fixture
def coach():
    c = CoachEntity(id=uuid4(), name="김도현", contact="kim@example.test")
    register_coach(c)
    return c


class TestCredits:
    def test_인증이_필요하다(self, client):
        assert client.get(CREDITS).status_code == 401

    def test_이력이_없으면_잔량_0이다(self, client):
        res = client.get(CREDITS, headers=_headers())
        assert res.status_code == 200
        assert res.json() == {"balance": 0, "history": []}


class TestAdjustCredit:
    def test_관리자가_아니면_403(self, client):
        res = client.post(
            ADJUSTMENTS,
            json={"user_id": str(uuid4()), "delta": 100, "reason": "signup_bonus"},
            headers=_headers(),
        )
        assert res.status_code == 403

    def test_지급하면_잔량에_반영된다(self, client, as_admin):
        target = uuid4()
        register_user(target)
        res = client.post(
            ADJUSTMENTS,
            json={"user_id": str(target), "delta": 100, "reason": "signup_bonus"},
            headers=_headers(DEMO_USER_ID),
        )
        assert res.status_code == 201, res.text
        assert res.json()["balance"] == 100

        res = client.post(
            ADJUSTMENTS,
            json={"user_id": str(target), "delta": -30, "reason": "analysis"},
            headers=_headers(DEMO_USER_ID),
        )
        assert res.status_code == 201
        assert res.json()["balance"] == 70
        assert [h["delta"] for h in res.json()["history"]] == [100, -30]

    def test_없는_사용자면_404(self, client, as_admin):
        res = client.post(
            ADJUSTMENTS,
            json={"user_id": str(uuid4()), "delta": 100, "reason": "x"},
            headers=_headers(DEMO_USER_ID),
        )
        assert res.status_code == 404

    def test_증감액_0은_422(self, client, as_admin):
        target = uuid4()
        register_user(target)
        res = client.post(
            ADJUSTMENTS,
            json={"user_id": str(target), "delta": 0, "reason": "x"},
            headers=_headers(DEMO_USER_ID),
        )
        assert res.status_code == 422


class TestCoaches:
    def test_목록에서_코치를_볼_수_있다(self, client, coach):
        res = client.get(COACHES, headers=_headers())
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 1
        assert body["items"][0] == {
            "id": str(coach.id),
            "name": coach.name,
            "contact": coach.contact,
        }

    def test_코치에_종목이나_가격이_없다(self, client, coach):
        res = client.get(COACHES, headers=_headers())
        for item in res.json()["items"]:
            assert set(item) == {"id", "name", "contact"}

    def test_상세를_볼_수_있다(self, client, coach):
        res = client.get(f"{COACHES}/{coach.id}", headers=_headers())
        assert res.status_code == 200
        assert res.json()["name"] == coach.name

    def test_없는_코치는_404(self, client):
        res = client.get(f"{COACHES}/{uuid4()}", headers=_headers())
        assert res.status_code == 404


class TestCoachReferral:
    def test_연결을_요청하면_기록된다(self, client, coach):
        actor = uuid4()
        res = client.post(
            f"{COACHES}/{coach.id}/referrals",
            json={"fee": "50000.00"},
            headers=_headers(actor),
        )
        assert res.status_code == 201, res.text
        assert res.json()["coach_id"] == str(coach.id)
        assert len(referrals_of(actor)) == 1

    def test_같은_코치에_여러_번_요청할_수_있다(self, client, coach):
        actor = uuid4()
        headers = _headers(actor)
        for _ in range(2):
            res = client.post(
                f"{COACHES}/{coach.id}/referrals",
                json={"fee": "0"},
                headers=headers,
            )
            assert res.status_code == 201
        assert len(referrals_of(actor)) == 2

    def test_없는_코치면_404(self, client):
        res = client.post(
            f"{COACHES}/{uuid4()}/referrals",
            json={"fee": "1000"},
            headers=_headers(),
        )
        assert res.status_code == 404

    def test_음수_수수료는_422(self, client, coach):
        res = client.post(
            f"{COACHES}/{coach.id}/referrals",
            json={"fee": "-1"},
            headers=_headers(),
        )
        assert res.status_code == 422

    def test_인증이_필요하다(self, client, coach):
        res = client.post(
            f"{COACHES}/{coach.id}/referrals", json={"fee": "0"}
        )
        assert res.status_code == 401
