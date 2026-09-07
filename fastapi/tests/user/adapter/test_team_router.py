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


class TestMemberCardReference:
    """구성원 목록이 **그 사람의 카드를 가리킬 수 있는가** (미결  2번).

    스쿼드 등재()가  를 받는데
    그 값을 얻을 경로가 없었다 —  는 ··
    · 까지만 줬고, 남의 카드 슬러그를 알 방법도 없었다.
    """

    def test_카드가_있으면_등재에_쓸_값과_링크에_쓸_값이_둘_다_온다(
        self, client, owner
    ):
        from app.user.adapter.outbound.stub.team_stub_repository import register_card

        card_id = uuid4()
        register_card(owner["id"], card_id, "brave-tiger-1234")

        res = client.post(f"{V1}/teams", json=TEAM, headers=owner["headers"])
        member = res.json()["members"][0]
        assert member["player_card_id"] == str(card_id)
        assert member["card_public_slug"] == "brave-tiger-1234"

    def test_카드가_없으면_null_이지만_목록에는_남는다(self, client, owner, team):
        """🔴 안쪽 조인으로 걸면 카드 없는 사람이 통째로 사라진다 —
        팀에는 여전히 있는 사람이다(그쪽 「하지 말 것」)."""
        member = team["members"][0]
        assert member["user_id"] == str(owner["id"])   # 목록에 남아 있다
        assert member["player_card_id"] is None
        assert member["card_public_slug"] is None

    def test_카드가_있는_사람과_없는_사람이_섞여도_둘_다_나온다(self, client, owner):
        from app.user.adapter.outbound.stub.team_stub_repository import (
            register_card,
            register_user,
        )

        other = uuid4()
        register_user(other)
        register_card(other, uuid4(), "quiet-heron-9876")

        created = client.post(f"{V1}/teams", json=TEAM, headers=owner["headers"])
        team_id = created.json()["id"]
        client.post(
            f"{V1}/teams/{team_id}/members",
            json={"user_id": str(other)},
            headers=owner["headers"],
        )

        res = client.get(f"{V1}/teams/{team_id}", headers=owner["headers"])
        by_user = {m["user_id"]: m for m in res.json()["members"]}
        assert len(by_user) == 2
        assert by_user[str(owner["id"])]["card_public_slug"] is None
        assert by_user[str(other)]["card_public_slug"] == "quiet-heron-9876"
