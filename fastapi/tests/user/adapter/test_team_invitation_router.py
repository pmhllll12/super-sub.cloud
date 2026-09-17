"""user/adapter/inbound/api/v1/team_router.py — 팀 초대. `min` 20번.

스텁을 끼워 DB 없이 돈다. 알림이 실제로 쌓이는지는 `test_team_db.py`가
진짜 PostgreSQL로 본다.
"""

from uuid import UUID, uuid4

import pytest

from app.core.security import issue_access_token
from app.user.adapter.outbound.stub.team_stub_repository import (
    register_squad,
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


def _invite(client, team_id, owner_headers, invited_user_id, position_code=None):
    body = {"invited_user_id": str(invited_user_id)}
    if position_code is not None:
        body["position_code"] = position_code
    return client.post(
        f"{V1}/teams/{team_id}/invitations", json=body, headers=owner_headers
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


class TestInvitationPosition:
    """「부르는 자리」 — `paik` 37번. **선택이다.**"""

    def test_자리를_안_정해도_초대가_된다(self, client, team, owner, candidate):
        res = _invite(client, team["id"], owner["headers"], candidate["id"])
        assert res.status_code == 201, res.text
        assert res.json()["position_code"] is None
        assert res.json()["position_label"] is None

    def test_자리를_정하면_약칭과_이름이_함께_나온다(
        self, client, team, owner, candidate
    ):
        res = _invite(client, team["id"], owner["headers"], candidate["id"], "GK")
        assert res.status_code == 201, res.text
        assert res.json()["position_code"] == "GK"
        # 🔴 이름까지 주는 것이 요점이다 — 화면이 약칭만으로는 「골키퍼」를
        # 못 쓴다(포지션 목록을 따로 부르지 않는 한).
        assert res.json()["position_label"] == "골키퍼"

    def test_다른_종목의_약칭은_422다(self, client, team, owner, candidate):
        # 야구의 `P`(투수). 축구 팀이라 없는 자리다 — 약칭은 종목 안에서만
        # 유일하므로 이것이 오타인지 아닌지는 종목을 봐야 안다.
        res = _invite(client, team["id"], owner["headers"], candidate["id"], "P")
        assert res.status_code == 422
        assert error_code(res) == "UNKNOWN_POSITION"

    def test_받은_목록에도_자리가_실린다(self, client, team, owner, candidate):
        _invite(client, team["id"], owner["headers"], candidate["id"], "FW")
        row = client.get(
            f"{V1}/me/invitations", headers=candidate["headers"]
        ).json()[0]
        assert row["position_code"] == "FW"
        assert row["position_label"] == "공격수"


class TestListMyInvitations:
    def test_내가_받은_대기중_초대만_보인다(self, client, team, owner, candidate):
        _invite(client, team["id"], owner["headers"], candidate["id"])
        res = client.get(f"{V1}/me/invitations", headers=candidate["headers"])
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["team_id"] == team["id"]

    def test_팀_이름과_지역이_초대_한_줄에_실린다(
        self, client, team, owner, candidate
    ):
        """`paik` 37번. 받는 사람은 그 팀 소속이 아니라 팀 화면을 안 거친다."""
        _invite(client, team["id"], owner["headers"], candidate["id"])
        row = client.get(
            f"{V1}/me/invitations", headers=candidate["headers"]
        ).json()[0]
        assert row["team_name"] == TEAM["name"]
        assert row["team_region"] == TEAM["region"]
        assert row["team_sport_code"] == TEAM["sport_code"]

    def test_기존_칸이_그대로_남아_있다(self, client, team, owner, candidate):
        """🔴 감싸지 않고 덧붙였다 — 화면이 읽던 칸이 한 겹 들어가면 안 된다."""
        _invite(client, team["id"], owner["headers"], candidate["id"])
        row = client.get(
            f"{V1}/me/invitations", headers=candidate["headers"]
        ).json()[0]
        assert set(row) >= {
            "id",
            "team_id",
            "invited_user_id",
            "status",
            "created_at",
            "responded_at",
        }
        assert "invitation" not in row

    def test_스쿼드가_있으면_공개_슬러그를_준다(
        self, client, team, owner, candidate
    ):
        """이 한 칸으로 화면이 `GET /squads/{slug}` 를 불러 판을 그린다."""
        # 🔴 스텁은 UUID 로 키를 잡는다 — JSON 의 문자열 그대로 넣으면 안 걸린다.
        register_squad(UUID(team["id"]), "sq-abc123")
        _invite(client, team["id"], owner["headers"], candidate["id"])
        row = client.get(
            f"{V1}/me/invitations", headers=candidate["headers"]
        ).json()[0]
        assert row["squad_public_slug"] == "sq-abc123"

    def test_스쿼드가_아직_없으면_null_이다(self, client, team, owner, candidate):
        """🔴 빈 값이 정상이다 — 스쿼드는 늦게 생긴다(생성이 멱등이다)."""
        _invite(client, team["id"], owner["headers"], candidate["id"])
        row = client.get(
            f"{V1}/me/invitations", headers=candidate["headers"]
        ).json()[0]
        assert row["squad_public_slug"] is None

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
