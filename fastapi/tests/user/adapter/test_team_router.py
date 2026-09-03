"""user/adapter/inbound/api/v1/team_router.py — 계약 문서 3-3절.

스텁을 끼워 DB 없이 돈다. 소프트 삭제·재가입처럼 **DB 만 답할 수 있는 것**은
`test_team_db.py` 가 본다.
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
def team(client, owner):
    res = client.post(f"{V1}/teams", json=TEAM, headers=owner["headers"])
    assert res.status_code == 201, res.text
    return res.json()


class TestCreateTeam:
    def test_인증이_필요하다(self, client):
        res = client.post(f"{V1}/teams", json=TEAM)
        assert res.status_code == 401
        assert error_code(res) == "UNAUTHORIZED"

    def test_만든_사람이_주장으로_들어간다(self, client, owner, team):
        assert [m["role"] for m in team["members"]] == ["owner"]
        assert team["members"][0]["user_id"] == str(owner["id"])

    def test_등록되지_않은_종목은_422(self, client, owner):
        """`team.sport_code` 에는 외래키가 없다(부록 D.3). DB 가 안 막으니 여기서 막는다."""
        res = client.post(
            f"{V1}/teams",
            json={**TEAM, "sport_code": "quidditch"},
            headers=owner["headers"],
        )
        assert res.status_code == 422
        assert error_code(res) == "UNKNOWN_SPORT"

    def test_이름이_비면_422(self, client, owner):
        res = client.post(
            f"{V1}/teams", json={**TEAM, "name": ""}, headers=owner["headers"]
        )
        assert res.status_code == 422


class TestReadTeam:
    def test_소속이_아니어도_볼_수_있다(self, client, team):
        res = client.get(f"{V1}/teams/{team['id']}", headers=_headers())
        assert res.status_code == 200
        assert res.json()["name"] == TEAM["name"]

    def test_없는_팀은_404(self, client):
        res = client.get(f"{V1}/teams/{uuid4()}", headers=_headers())
        assert res.status_code == 404
        assert error_code(res) == "TEAM_NOT_FOUND"


class TestJoinTeam:
    def test_본인은_그냥_가입한다(self, client, team):
        res = client.post(
            f"{V1}/teams/{team['id']}/members", json={}, headers=_headers()
        )
        assert res.status_code == 201, res.text
        assert [m["role"] for m in res.json()["members"]] == ["owner", "member"]

    def test_두_번_가입하면_409(self, client, team):
        headers = _headers()
        client.post(f"{V1}/teams/{team['id']}/members", json={}, headers=headers)
        res = client.post(
            f"{V1}/teams/{team['id']}/members", json={}, headers=headers
        )
        assert res.status_code == 409
        assert error_code(res) == "ALREADY_MEMBER"

    def test_주장은_남을_넣을_수_있다(self, client, owner, team):
        newbie = uuid4()
        register_user(newbie)
        res = client.post(
            f"{V1}/teams/{team['id']}/members",
            json={"user_id": str(newbie)},
            headers=owner["headers"],
        )
        assert res.status_code == 201, res.text
        assert str(newbie) in [m["user_id"] for m in res.json()["members"]]

    def test_일반_구성원은_남을_못_넣는다(self, client, team):
        headers = _headers()
        client.post(f"{V1}/teams/{team['id']}/members", json={}, headers=headers)

        other = uuid4()
        register_user(other)
        res = client.post(
            f"{V1}/teams/{team['id']}/members",
            json={"user_id": str(other)},
            headers=headers,
        )
        assert res.status_code == 403
        assert error_code(res) == "FORBIDDEN"

    def test_없는_사용자를_넣으면_404(self, client, owner, team):
        res = client.post(
            f"{V1}/teams/{team['id']}/members",
            json={"user_id": str(uuid4())},
            headers=owner["headers"],
        )
        assert res.status_code == 404
        assert error_code(res) == "USER_NOT_FOUND"


class TestLeaveTeam:
    def _join(self, client, team, headers):
        assert (
            client.post(
                f"{V1}/teams/{team['id']}/members", json={}, headers=headers
            ).status_code
            == 201
        )

    def test_본인은_탈퇴할_수_있다(self, client, team):
        headers = _headers()
        self._join(client, team, headers)
        member_id = client.get(f"{V1}/teams/{team['id']}", headers=headers).json()[
            "members"
        ][1]["user_id"]

        res = client.delete(
            f"{V1}/teams/{team['id']}/members/{member_id}", headers=headers
        )
        assert res.status_code == 204
        assert res.content == b""

    def test_주장은_남을_뺄_수_있다(self, client, owner, team):
        headers = _headers()
        self._join(client, team, headers)
        member_id = client.get(f"{V1}/teams/{team['id']}", headers=headers).json()[
            "members"
        ][1]["user_id"]

        res = client.delete(
            f"{V1}/teams/{team['id']}/members/{member_id}", headers=owner["headers"]
        )
        assert res.status_code == 204

    def test_일반_구성원은_남을_못_뺀다(self, client, owner, team):
        headers = _headers()
        self._join(client, team, headers)
        res = client.delete(
            f"{V1}/teams/{team['id']}/members/{owner['id']}", headers=headers
        )
        assert res.status_code == 403
        assert error_code(res) == "FORBIDDEN"

    def test_마지막_주장은_나갈_수_없다(self, client, owner, team):
        """나가면 아무도 남을 넣을 수 없는 팀이 된다. 소유권 이양 API 가 없다."""
        res = client.delete(
            f"{V1}/teams/{team['id']}/members/{owner['id']}", headers=owner["headers"]
        )
        assert res.status_code == 409
        assert error_code(res) == "LAST_OWNER"

    def test_소속이_아닌_사람을_빼면_404(self, client, owner, team):
        res = client.delete(
            f"{V1}/teams/{team['id']}/members/{uuid4()}", headers=owner["headers"]
        )
        assert res.status_code == 404
        assert error_code(res) == "NOT_A_MEMBER"

    def test_인증이_필요하다(self, client, team, owner):
        res = client.delete(f"{V1}/teams/{team['id']}/members/{owner['id']}")
        assert res.status_code == 401
