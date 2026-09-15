"""팀 대 팀 경기 신청(`team_match_request`) 계약. `paik` 17번.

기존 `test_application_router.py`(개인이 경기에 지원)와는 주체가 다르다 —
여기는 **팀이 팀에게** 걸고 **상대 팀 주장**이 받는다.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.security import issue_access_token
from app.match.adapter.outbound.stub.match_stub_repository import (
    register_role,
    register_team,
    register_user,
    reset_matches,
)
from tests.conftest import V1, error_code


def _headers(user_id):
    return {"Authorization": f"Bearer {issue_access_token(user_id)}"}


@pytest.fixture(autouse=True)
def _clean():
    reset_matches()
    yield
    reset_matches()


def _future(days=7):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


@pytest.fixture
def world(client):
    """팀 셋(A·B·C) — 각자 주장 하나, A엔 주장 아닌 팀원도 하나."""
    a, b, c = uuid4(), uuid4(), uuid4()
    a_owner, a_member, b_owner, c_owner = uuid4(), uuid4(), uuid4(), uuid4()
    register_team(a, "football")
    register_team(b, "football")
    register_team(c, "football")
    register_role(a, a_owner, "owner")
    register_role(a, a_member, "member")
    register_role(b, b_owner, "owner")
    register_role(c, c_owner, "owner")
    for u in (a_owner, a_member, b_owner, c_owner):
        register_user(u)
    return {
        "a": a, "b": b, "c": c,
        "a_owner": a_owner, "a_member": a_member,
        "b_owner": b_owner, "c_owner": c_owner,
    }


def _request(client, world, requester_actor, requester_team, target_team, **kw):
    body = {
        "target_team_id": str(target_team),
        "played_at": kw.get("played_at", _future()),
        "place": kw.get("place", "강남 풋살장"),
    }
    return client.post(
        f"{V1}/teams/{requester_team}/match-requests",
        json=body,
        headers=_headers(requester_actor),
    )


class TestCreate:
    def test_인증이_필요하다(self, client, world):
        res = client.post(
            f"{V1}/teams/{world['a']}/match-requests",
            json={"target_team_id": str(world["b"]), "played_at": _future(), "place": "x"},
        )
        assert res.status_code == 401

    def test_주장이_아니면_403(self, client, world):
        res = _request(client, world, world["a_member"], world["a"], world["b"])
        assert res.status_code == 403

    def test_주장이면_신청된다(self, client, world):
        res = _request(client, world, world["a_owner"], world["a"], world["b"])
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["status"] == "pending"
        assert body["requester_team_id"] == str(world["a"])
        assert body["target_team_id"] == str(world["b"])
        assert body["match_id"] is None

    def test_같은_팀에는_못_건다(self, client, world):
        res = _request(client, world, world["a_owner"], world["a"], world["a"])
        assert res.status_code == 422
        assert error_code(res) == "CANNOT_REQUEST_SELF"

    def test_지난_시각은_422(self, client, world):
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        res = _request(
            client, world, world["a_owner"], world["a"], world["b"], played_at=past
        )
        assert res.status_code == 422
        assert error_code(res) == "PAST_MATCH"

    def test_없는_대상_팀은_404(self, client, world):
        res = _request(client, world, world["a_owner"], world["a"], uuid4())
        assert res.status_code == 404


class TestList:
    def test_주장만_볼_수_있다(self, client, world):
        _request(client, world, world["a_owner"], world["a"], world["b"])
        res = client.get(
            f"{V1}/teams/{world['a']}/match-requests",
            headers=_headers(world["a_member"]),
        )
        assert res.status_code == 403

    def test_보낸_것과_받은_것_둘_다_보인다(self, client, world):
        _request(client, world, world["a_owner"], world["a"], world["b"])
        _request(client, world, world["c_owner"], world["c"], world["a"])

        rows = client.get(
            f"{V1}/teams/{world['a']}/match-requests",
            headers=_headers(world["a_owner"]),
        ).json()
        assert len(rows) == 2
        teams = {(r["requester_team_id"], r["target_team_id"]) for r in rows}
        assert (str(world["a"]), str(world["b"])) in teams
        assert (str(world["c"]), str(world["a"])) in teams


class TestAccept:
    def test_대상_팀_주장만_수락한다(self, client, world):
        req = _request(client, world, world["a_owner"], world["a"], world["b"]).json()

        # 신청 팀(a) 주장이 수락하려 해도 막힌다 — 받는 쪽은 상대(b)여야 한다.
        wrong = client.post(
            f"{V1}/teams/{world['a']}/match-requests/{req['id']}/accept",
            headers=_headers(world["a_owner"]),
        )
        assert wrong.status_code == 403

        res = client.post(
            f"{V1}/teams/{world['b']}/match-requests/{req['id']}/accept",
            headers=_headers(world["b_owner"]),
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["status"] == "accepted"
        assert body["match_id"] is not None

    def test_수락하면_양쪽_경기_목록에_같은_경기가_뜬다(self, client, world):
        req = _request(client, world, world["a_owner"], world["a"], world["b"]).json()
        accepted = client.post(
            f"{V1}/teams/{world['b']}/match-requests/{req['id']}/accept",
            headers=_headers(world["b_owner"]),
        ).json()

        a_matches = client.get(
            f"{V1}/teams/{world['a']}/matches", headers=_headers(world["a_owner"])
        ).json()
        b_matches = client.get(
            f"{V1}/teams/{world['b']}/matches", headers=_headers(world["b_owner"])
        ).json()
        assert accepted["match_id"] in [m["id"] for m in a_matches]
        assert accepted["match_id"] in [m["id"] for m in b_matches]

    def test_다른_pending_신청이_같이_정리된다(self, client, world):
        """A→B(수락될 것) · A→C(A가 걸어 둔 다른 신청) · C→B(B가 받은 다른 신청).

        A→B가 수락되면 A→C(A가 더 못 뛰니 무의미)·C→B(B가 더 못 뛰니 무의미)
        **둘 다** cancelled 여야 한다 — 이중 예약 방지.
        """
        ab = _request(client, world, world["a_owner"], world["a"], world["b"]).json()
        ac = _request(client, world, world["a_owner"], world["a"], world["c"]).json()
        cb = _request(client, world, world["c_owner"], world["c"], world["b"]).json()

        client.post(
            f"{V1}/teams/{world['b']}/match-requests/{ab['id']}/accept",
            headers=_headers(world["b_owner"]),
        )

        rows = {
            r["id"]: r
            for r in client.get(
                f"{V1}/teams/{world['a']}/match-requests",
                headers=_headers(world["a_owner"]),
            ).json()
        }
        assert rows[ac["id"]]["status"] == "cancelled"

        c_rows = {
            r["id"]: r
            for r in client.get(
                f"{V1}/teams/{world['c']}/match-requests",
                headers=_headers(world["c_owner"]),
            ).json()
        }
        assert c_rows[cb["id"]]["status"] == "cancelled"

    def test_이미_답이_난_신청은_다시_수락_못한다(self, client, world):
        req = _request(client, world, world["a_owner"], world["a"], world["b"]).json()
        client.post(
            f"{V1}/teams/{world['b']}/match-requests/{req['id']}/accept",
            headers=_headers(world["b_owner"]),
        )
        again = client.post(
            f"{V1}/teams/{world['b']}/match-requests/{req['id']}/accept",
            headers=_headers(world["b_owner"]),
        )
        assert again.status_code == 409
        assert error_code(again) == "TEAM_MATCH_REQUEST_ALREADY_RESPONDED"


class TestReject:
    def test_대상_팀_주장이_거절한다(self, client, world):
        req = _request(client, world, world["a_owner"], world["a"], world["b"]).json()
        res = client.post(
            f"{V1}/teams/{world['b']}/match-requests/{req['id']}/reject",
            headers=_headers(world["b_owner"]),
        )
        assert res.status_code == 200
        assert res.json()["status"] == "rejected"


class TestCancel:
    def test_신청_팀_주장만_무른다(self, client, world):
        req = _request(client, world, world["a_owner"], world["a"], world["b"]).json()

        wrong = client.delete(
            f"{V1}/teams/{world['b']}/match-requests/{req['id']}",
            headers=_headers(world["b_owner"]),
        )
        assert wrong.status_code == 403

        res = client.delete(
            f"{V1}/teams/{world['a']}/match-requests/{req['id']}",
            headers=_headers(world["a_owner"]),
        )
        assert res.status_code == 200
        assert res.json()["status"] == "cancelled"

    def test_이미_수락된_것은_못_무른다(self, client, world):
        req = _request(client, world, world["a_owner"], world["a"], world["b"]).json()
        client.post(
            f"{V1}/teams/{world['b']}/match-requests/{req['id']}/accept",
            headers=_headers(world["b_owner"]),
        )
        res = client.delete(
            f"{V1}/teams/{world['a']}/match-requests/{req['id']}",
            headers=_headers(world["a_owner"]),
        )
        assert res.status_code == 409
