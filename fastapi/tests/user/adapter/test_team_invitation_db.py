"""팀 초대를 **실제 PostgreSQL** 에 대고 확인한다. `min` 20번.

스텁이 답할 수 없는 것들이다:

- **알림이 실제로 쌓이는가**(받은 사람에게 발송, 팀 주장에게 수락·거절) —
  `notification`은 `user` 컨텍스트 안이지만 다른 테이블이라 원시 SQL로 대조한다
- 수락하면 `team_member` 행이 **실제로** 생기는가(기존 `JoinTeamUseCase` 재사용 경로)
- `team_invitation`이 저장·조회되는가
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from tests.conftest import V1, error_code

pytestmark = pytest.mark.db

PASSWORD = "supersub2026"
TEAM = {"name": "번개FC", "region": "서울 강남", "sport_code": "football"}


def _account(db_client, nickname):
    nickname = f"{nickname}{uuid.uuid4().hex[:6]}"
    email = f"teaminvite-{uuid.uuid4().hex[:12]}@super-sub.example"
    signup = db_client.post(
        f"{V1}/auth/signup",
        json={"email": email, "password": PASSWORD, "nickname": nickname},
    )
    assert signup.status_code == 201, signup.text
    login = db_client.post(
        f"{V1}/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert login.status_code == 200
    return {
        "id": uuid.UUID(signup.json()["id"]),
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


@pytest.fixture
def world(db_client, db_session):
    owner = _account(db_client, "주장")
    candidate = _account(db_client, "후보")
    res = db_client.post(f"{V1}/teams", json=TEAM, headers=owner["headers"])
    assert res.status_code == 201, res.text
    team_id = uuid.UUID(res.json()["id"])

    yield {"owner": owner, "candidate": candidate, "team_id": team_id}

    db_session.execute(text("delete from notification"))
    db_session.execute(text("delete from team_invitation"))
    db_session.execute(
        text("delete from team_member where team_id = :t"), {"t": team_id}
    )
    db_session.execute(text("delete from team where id = :t"), {"t": team_id})
    for acc in (owner, candidate):
        db_session.execute(
            text('delete from "user" where id = :i'), {"i": acc["id"]}
        )
    db_session.commit()


def _invite(db_client, world):
    res = db_client.post(
        f"{V1}/teams/{world['team_id']}/invitations",
        json={"invited_user_id": str(world["candidate"]["id"])},
        headers=world["owner"]["headers"],
    )
    assert res.status_code == 201, res.text
    return uuid.UUID(res.json()["id"])


class TestCreate:
    def test_초대가_실제로_저장된다(self, db_client, db_session, world):
        invitation_id = _invite(db_client, world)
        row = db_session.execute(
            text(
                "select team_id, invited_user_id, status "
                "from team_invitation where id = :i"
            ),
            {"i": invitation_id},
        ).one()
        assert row.team_id == world["team_id"]
        assert row.invited_user_id == world["candidate"]["id"]
        assert row.status == "pending"

    def test_받은_사람에게_알림이_간다(self, db_client, db_session, world):
        _invite(db_client, world)
        notif = db_session.execute(
            text(
                "select type, subject_type from notification "
                "where recipient_user_id = :r"
            ),
            {"r": world["candidate"]["id"]},
        ).one()
        assert notif.type == "team_invitation_sent"
        assert notif.subject_type == "team_invitation"


class TestAccept:
    def test_수락하면_실제로_구성원이_된다(self, db_client, db_session, world):
        invitation_id = _invite(db_client, world)
        res = db_client.post(
            f"{V1}/me/invitations/{invitation_id}/accept",
            headers=world["candidate"]["headers"],
        )
        assert res.status_code == 200, res.text

        row = db_session.execute(
            text(
                "select role, left_at from team_member "
                "where team_id = :t and user_id = :u"
            ),
            {"t": world["team_id"], "u": world["candidate"]["id"]},
        ).one()
        assert row.role == "member"
        assert row.left_at is None

    def test_수락하면_주장에게_알림이_간다(self, db_client, db_session, world):
        invitation_id = _invite(db_client, world)
        db_client.post(
            f"{V1}/me/invitations/{invitation_id}/accept",
            headers=world["candidate"]["headers"],
        )
        notif = db_session.execute(
            text(
                "select type from notification "
                "where recipient_user_id = :r and type = 'team_invitation_accepted'"
            ),
            {"r": world["owner"]["id"]},
        ).one()
        assert notif.type == "team_invitation_accepted"


class TestReject:
    def test_거절하면_구성원이_안_되고_주장에게_알림이_간다(
        self, db_client, db_session, world
    ):
        invitation_id = _invite(db_client, world)
        res = db_client.post(
            f"{V1}/me/invitations/{invitation_id}/reject",
            headers=world["candidate"]["headers"],
        )
        assert res.status_code == 200, res.text

        member = db_session.execute(
            text(
                "select count(*) from team_member "
                "where team_id = :t and user_id = :u"
            ),
            {"t": world["team_id"], "u": world["candidate"]["id"]},
        ).scalar_one()
        assert member == 0

        notif = db_session.execute(
            text(
                "select type from notification "
                "where recipient_user_id = :r and type = 'team_invitation_rejected'"
            ),
            {"r": world["owner"]["id"]},
        ).one()
        assert notif.type == "team_invitation_rejected"
