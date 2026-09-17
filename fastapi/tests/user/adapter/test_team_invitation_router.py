"""user/adapter/inbound/api/v1/team_router.py — 팀 초대. `min` 20번.

스텁을 끼워 DB 없이 돈다. 알림이 실제로 쌓이는지는 `test_team_db.py`가
진짜 PostgreSQL로 본다.
"""

from uuid import uuid4

import pytest

from app.core.security import issue_access_token
from app.user.adapter.outbound.stub.team_stub_repository import (
    register_user,
    reset_teams,
)
from tests.conftest import V1, error_code

TEAM = {"name": "번개FC", "region": "서울 강남", "sport_code": "football"}


def _headers(user_id=None):
    return {"Authorization": f"Bearer {issue_access_token(user_id or uuid4())}"}


@pytest.fixture(autouse=True)
def _clean():
    reset_teams()
    yield
    reset_teams()


@pytest.fixture
def owner():
    user_id = uuid4()
    register_user(user_id)
    return {"id": user_id, "headers": _headers(user_id)}


@pytest.fixture
def candidate():
    """초대받을 사람. 아직 어느 팀에도 없다."""
    user_id = uuid4()
    register_user(user_id)
    return {"id": user_id, "headers": _headers(user_id)}


@pytest.fixture
def team(client, owner):
    res = client.post(f"{V1}/teams", json=TEAM, headers=owner["headers"])
    assert res.status_code == 201, res.text
    return res.json()


def _invite(client, team_id, owner_headers, invited_user_id):
    return client.post(
        f"{V1}/teams/{team_id}/invitations",
        json={"invited_user_id": str(invited_user_id)},
        headers=owner_headers,
    )


class TestCreateInvitation:
    def test_인증이_필요하다(self, client, team):
        res = client.post(
            f"{V1}/teams/{team['id']}/invitations",
            json={"invited_user_id": str(uuid4())},
        )
        assert res.status_code == 401

    def test_주장이_보내면_201이고_대기중이다(self, client, team, owner, candidate):
        res = _invite(client, team["id"], owner["headers"], candidate["id"])
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["team_id"] == team["id"]
        assert body["invited_user_id"] == str(candidate["id"])
        assert body["status"] == "pending"
        assert body["responded_at"] is None

    def test_주장이_아니면_403(self, client, team, candidate):
        """구성원이 아닌 사람(`candidate`)이 초대를 보내려 한다."""
        res = _invite(client, team["id"], candidate["headers"], uuid4())
        assert res.status_code == 403
        assert error_code(res) == "FORBIDDEN"

    def test_없는_팀은_404(self, client, owner, candidate):
        res = _invite(client, uuid4(), owner["headers"], candidate["id"])
        assert res.status_code == 404
        assert error_code(res) == "TEAM_NOT_FOUND"

    def test_없는_사용자는_404(self, client, team, owner):
        res = _invite(client, team["id"], owner["headers"], uuid4())
        assert res.status_code == 404
        assert error_code(res) == "USER_NOT_FOUND"

    def test_이미_구성원이면_409(self, client, team, owner):
        res = _invite(client, team["id"], owner["headers"], owner["id"])
        assert res.status_code == 409
        assert error_code(res) == "ALREADY_MEMBER"

    def test_이미_보낸_대기중_초대가_있으면_409(
        self, client, team, owner, candidate
    ):
        _invite(client, team["id"], owner["headers"], candidate["id"])
        res = _invite(client, team["id"], owner["headers"], candidate["id"])
        assert res.status_code == 409
        assert error_code(res) == "ALREADY_INVITED"


class TestListTeamInvitations:
    def test_주장만_볼_수_있다(self, client, team, owner, candidate):
        _invite(client, team["id"], owner["headers"], candidate["id"])
        res = client.get(
            f"{V1}/teams/{team['id']}/invitations", headers=candidate["headers"]
        )
        assert res.status_code == 403

    def test_보낸_초대가_보인다(self, client, team, owner, candidate):
        _invite(client, team["id"], owner["headers"], candidate["id"])
        res = client.get(
            f"{V1}/teams/{team['id']}/invitations", headers=owner["headers"]
        )
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["invited_user_id"] == str(candidate["id"])


class TestListMyInvitations:
    def test_내가_받은_대기중_초대만_보인다(self, client, team, owner, candidate):
        _invite(client, team["id"], owner["headers"], candidate["id"])
        res = client.get(f"{V1}/me/invitations", headers=candidate["headers"])
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["team_id"] == team["id"]

    def test_남이_받은_초대는_안_보인다(self, client, team, owner, candidate):
        _invite(client, team["id"], owner["headers"], candidate["id"])
        res = client.get(f"{V1}/me/invitations", headers=owner["headers"])
        assert res.status_code == 200
        assert res.json() == []


class TestAcceptInvitation:
    def test_받은_사람이_수락하면_구성원이_된다(
        self, client, team, owner, candidate
    ):
        invitation_id = _invite(
            client, team["id"], owner["headers"], candidate["id"]
        ).json()["id"]

        res = client.post(
            f"{V1}/me/invitations/{invitation_id}/accept",
            headers=candidate["headers"],
        )
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "accepted"
        assert res.json()["responded_at"] is not None

        team_after = client.get(
            f"{V1}/teams/{team['id']}", headers=owner["headers"]
        ).json()
        member_ids = {m["user_id"] for m in team_after["members"]}
        assert str(candidate["id"]) in member_ids

    def test_받은_사람이_아니면_403(self, client, team, owner, candidate):
        invitation_id = _invite(
            client, team["id"], owner["headers"], candidate["id"]
        ).json()["id"]
        res = client.post(
            f"{V1}/me/invitations/{invitation_id}/accept", headers=owner["headers"]
        )
        assert res.status_code == 403

    def test_없는_초대는_404(self, client, candidate):
        res = client.post(
            f"{V1}/me/invitations/{uuid4()}/accept", headers=candidate["headers"]
        )
        assert res.status_code == 404
        assert error_code(res) == "TEAM_INVITATION_NOT_FOUND"

    def test_이미_답한_초대는_409(self, client, team, owner, candidate):
        invitation_id = _invite(
            client, team["id"], owner["headers"], candidate["id"]
        ).json()["id"]
        client.post(
            f"{V1}/me/invitations/{invitation_id}/accept",
            headers=candidate["headers"],
        )
        res = client.post(
            f"{V1}/me/invitations/{invitation_id}/accept",
            headers=candidate["headers"],
        )
        assert res.status_code == 409
        assert error_code(res) == "TEAM_INVITATION_ALREADY_RESPONDED"


class TestRejectInvitation:
    def test_받은_사람이_거절하면_구성원이_안_된다(
        self, client, team, owner, candidate
    ):
        invitation_id = _invite(
            client, team["id"], owner["headers"], candidate["id"]
        ).json()["id"]

        res = client.post(
            f"{V1}/me/invitations/{invitation_id}/reject",
            headers=candidate["headers"],
        )
        assert res.status_code == 200
        assert res.json()["status"] == "rejected"

        team_after = client.get(
            f"{V1}/teams/{team['id']}", headers=owner["headers"]
        ).json()
        member_ids = {m["user_id"] for m in team_after["members"]}
        assert str(candidate["id"]) not in member_ids

    def test_받은_사람이_아니면_403(self, client, team, owner, candidate):
        invitation_id = _invite(
            client, team["id"], owner["headers"], candidate["id"]
        ).json()["id"]
        res = client.post(
            f"{V1}/me/invitations/{invitation_id}/reject", headers=owner["headers"]
        )
        assert res.status_code == 403


class TestCancelInvitation:
    def test_보낸_주장이_무를_수_있다(self, client, team, owner, candidate):
        invitation_id = _invite(
            client, team["id"], owner["headers"], candidate["id"]
        ).json()["id"]

        res = client.delete(
            f"{V1}/teams/{team['id']}/invitations/{invitation_id}",
            headers=owner["headers"],
        )
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "cancelled"

        # 무른 뒤에는 같은 사람에게 다시 초대를 보낼 수 있다(대기 중 초대가 아니므로).
        res2 = _invite(client, team["id"], owner["headers"], candidate["id"])
        assert res2.status_code == 201, res2.text

    def test_주장이_아니면_403(self, client, team, owner, candidate):
        invitation_id = _invite(
            client, team["id"], owner["headers"], candidate["id"]
        ).json()["id"]
        res = client.delete(
            f"{V1}/teams/{team['id']}/invitations/{invitation_id}",
            headers=candidate["headers"],
        )
        assert res.status_code == 403

    def test_이미_답한_초대는_409(self, client, team, owner, candidate):
        invitation_id = _invite(
            client, team["id"], owner["headers"], candidate["id"]
        ).json()["id"]
        client.post(
            f"{V1}/me/invitations/{invitation_id}/reject",
            headers=candidate["headers"],
        )
        res = client.delete(
            f"{V1}/teams/{team['id']}/invitations/{invitation_id}",
            headers=owner["headers"],
        )
        assert res.status_code == 409
