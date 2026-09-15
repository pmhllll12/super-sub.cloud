"""팀 대 팀 경기 신청을 **실제 PostgreSQL** 에 대고 확인한다. `paik` 17번.

스텁이 답할 수 없는 것들이다:

- `opponent_team_id`가 실제로 저장·조회되는가
- **알림이 실제로 쌓이는가**(대상 팀 주장에게 신청, 신청 팀에 수락/거절,
  동시 확정 방지로 정리된 쪽 양쪽에게) — `notification`은 `match`가 임포트
  못 하는 남의 테이블이라 원시 SQL로 직접 대조한다
- 동시 확정 방지가 실제 트랜잭션에서 두 팀 다 정리하는가
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from tests.conftest import V1, error_code

pytestmark = pytest.mark.db

PASSWORD = "supersub2026"


def _account(db_client, nickname):
    nickname = f"{nickname}{uuid.uuid4().hex[:6]}"
    email = f"teammatch-{uuid.uuid4().hex[:12]}@super-sub.example"
    signup = db_client.post(
        f"{V1}/auth/signup",
        json={"email": email, "password": PASSWORD, "nickname": nickname},
    )
    assert signup.status_code == 201, signup.text
    login = db_client.post(
        f"{V1}/auth/login", json={"email": email, "password": PASSWORD}
    )
    return {
        "id": uuid.UUID(signup.json()["id"]),
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


def _team(db_client, owner, name):
    res = db_client.post(
        f"{V1}/teams",
        json={"name": name, "region": "서울", "sport_code": "football"},
        headers=owner["headers"],
    )
    assert res.status_code == 201, res.text
    return uuid.UUID(res.json()["id"])


def _future(days=7):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


@pytest.fixture
def world(db_client, db_session):
    a_owner = _account(db_client, "A주장")
    b_owner = _account(db_client, "B주장")
    team_a = _team(db_client, a_owner, "팀A")
    team_b = _team(db_client, b_owner, "팀B")

    yield {
        "a_owner": a_owner, "b_owner": b_owner,
        "team_a": team_a, "team_b": team_b,
    }

    db_session.execute(text("delete from notification"))
    db_session.execute(text("delete from team_match_request"))
    db_session.execute(
        text("delete from match where team_id in (:a, :b) or opponent_team_id in (:a, :b)"),
        {"a": team_a, "b": team_b},
    )
    db_session.execute(
        text("delete from team_member where team_id in (:a, :b)"),
        {"a": team_a, "b": team_b},
    )
    db_session.execute(
        text("delete from team where id in (:a, :b)"), {"a": team_a, "b": team_b}
    )
    for acc in (a_owner, b_owner):
        db_session.execute(
            text('delete from "user" where id = :i'), {"i": acc["id"]}
        )
    db_session.commit()


class TestCreate:
    def test_신청이_실제로_저장된다(self, db_client, db_session, world):
        res = db_client.post(
            f"{V1}/teams/{world['team_a']}/match-requests",
            json={
                "target_team_id": str(world["team_b"]),
                "played_at": _future(),
                "place": "강남 풋살장",
            },
            headers=world["a_owner"]["headers"],
        )
        assert res.status_code == 201, res.text
        request_id = uuid.UUID(res.json()["id"])

        row = db_session.execute(
            text(
                "select requester_team_id, target_team_id, status "
                "from team_match_request where id = :i"
            ),
            {"i": request_id},
        ).one()
        assert row.requester_team_id == world["team_a"]
        assert row.target_team_id == world["team_b"]
        assert row.status == "pending"

    def test_대상_팀_주장에게_알림이_간다(self, db_client, db_session, world):
        db_client.post(
            f"{V1}/teams/{world['team_a']}/match-requests",
            json={
                "target_team_id": str(world["team_b"]),
                "played_at": _future(),
                "place": "강남 풋살장",
            },
            headers=world["a_owner"]["headers"],
        )
        notif = db_session.execute(
            text(
                "select type, subject_type from notification "
                "where recipient_user_id = :r"
            ),
            {"r": world["b_owner"]["id"]},
        ).one()
        assert notif.type == "team_match_requested"
        assert notif.subject_type == "team_match_request"


class TestAccept:
    def _create(self, db_client, world, **kw):
        return db_client.post(
            f"{V1}/teams/{world['team_a']}/match-requests",
            json={
                "target_team_id": str(world["team_b"]),
                "played_at": kw.get("played_at", _future()),
                "place": "강남 풋살장",
            },
            headers=world["a_owner"]["headers"],
        ).json()

    def test_수락하면_match에_상대팀이_실제로_찬다(
        self, db_client, db_session, world
    ):
        req = self._create(db_client, world)
        accepted = db_client.post(
            f"{V1}/teams/{world['team_b']}/match-requests/{req['id']}/accept",
            headers=world["b_owner"]["headers"],
        ).json()

        row = db_session.execute(
            text("select team_id, opponent_team_id from match where id = :i"),
            {"i": uuid.UUID(accepted["match_id"])},
        ).one()
        assert row.team_id == world["team_a"]
        assert row.opponent_team_id == world["team_b"]

    def test_신청_팀에게_수락_알림이_간다(self, db_client, db_session, world):
        req = self._create(db_client, world)
        db_client.post(
            f"{V1}/teams/{world['team_b']}/match-requests/{req['id']}/accept",
            headers=world["b_owner"]["headers"],
        )
        notif = db_session.execute(
            text(
                "select type from notification "
                "where recipient_user_id = :r and type = 'team_match_accepted'"
            ),
            {"r": world["a_owner"]["id"]},
        ).first()
        assert notif is not None

    def test_다른_pending_신청_정리와_알림이_실제_DB에서도_일어난다(
        self, db_client, db_session, world
    ):
        c_owner = _account(db_client, "C주장")
        team_c = _team(db_client, c_owner, "팀C")
        try:
            ab = self._create(db_client, world)
            ac = db_client.post(
                f"{V1}/teams/{world['team_a']}/match-requests",
                json={
                    "target_team_id": str(team_c),
                    "played_at": _future(),
                    "place": "다른 구장",
                },
                headers=world["a_owner"]["headers"],
            ).json()

            db_client.post(
                f"{V1}/teams/{world['team_b']}/match-requests/{ab['id']}/accept",
                headers=world["b_owner"]["headers"],
            )

            status = db_session.execute(
                text("select status from team_match_request where id = :i"),
                {"i": uuid.UUID(ac["id"])},
            ).scalar_one()
            assert status == "cancelled"

            notif = db_session.execute(
                text(
                    "select type from notification where recipient_user_id = :r "
                    "and type = 'team_match_request_cancelled'"
                ),
                {"r": c_owner["id"]},
            ).first()
            assert notif is not None
        finally:
            db_session.execute(text("delete from notification"))
            db_session.execute(text("delete from team_match_request"))
            db_session.execute(
                text(
                    "delete from match where team_id = :c or opponent_team_id = :c"
                ),
                {"c": team_c},
            )
            db_session.execute(
                text("delete from team_member where team_id = :c"), {"c": team_c}
            )
            db_session.execute(text("delete from team where id = :c"), {"c": team_c})
            db_session.execute(
                text('delete from "user" where id = :i'), {"i": c_owner["id"]}
            )
            db_session.commit()


class TestCancelMatch:
    def test_확정_경기_취소는_상대팀_주장에게만_간다(
        self, db_client, db_session, world
    ):
        req = db_client.post(
            f"{V1}/teams/{world['team_a']}/match-requests",
            json={
                "target_team_id": str(world["team_b"]),
                "played_at": _future(),
                "place": "강남 풋살장",
            },
            headers=world["a_owner"]["headers"],
        ).json()
        accepted = db_client.post(
            f"{V1}/teams/{world['team_b']}/match-requests/{req['id']}/accept",
            headers=world["b_owner"]["headers"],
        ).json()

        cancel = db_client.delete(
            f"{V1}/matches/{accepted['match_id']}",
            headers=world["a_owner"]["headers"],
        )
        assert cancel.status_code == 204, cancel.text

        notif = db_session.execute(
            text(
                "select recipient_user_id from notification "
                "where type = 'team_match_cancelled'"
            )
        ).scalar_one()
        assert notif == world["b_owner"]["id"]
