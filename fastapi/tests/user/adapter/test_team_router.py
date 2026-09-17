"""user/adapter/inbound/api/v1/team_router.py — 계약 문서 3-3절.

스텁을 끼워 DB 없이 돈다. 소프트 삭제·재가입처럼 **DB 만 답할 수 있는 것**은
`test_team_db.py` 가 본다.
"""

from uuid import uuid4

import pytest

from app.core.security import issue_access_token
from app.user.adapter.outbound.stub.team_stub_repository import (
    register_upcoming_match,
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

    def test_내려간_종목은_없는_종목과_다른_code_다(self, client, owner):
        """`ho` 39번 — 행은 있지만 루브릭이 없어 지금 안 받는 종목이다."""
        res = client.post(
            f"{V1}/teams",
            json={**TEAM, "sport_code": "baseball"},
            headers=owner["headers"],
        )
        assert res.status_code == 422
        assert error_code(res) == "SPORT_NOT_AVAILABLE"

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


class TestUpdateTeam:
    """`PATCH /teams/{id}` — 팀 이름·지역 수정 (2026-09-16 신설).

    지금까지 팀은 **만들 때 적은 값이 영영 고정**이었다. 지역은 경기 탐색
    (`GET /matches?region=`)이 거르는 값이라, 틀리면 그 팀이 검색에서
    통째로 안 걸린다.
    """

    def test_인증이_필요하다(self, client, team):
        res = client.patch(f"{V1}/teams/{team['id']}", json={"region": "부산"})
        assert res.status_code == 401

    def test_주장이_지역을_고친다(self, client, owner, team):
        res = client.patch(
            f"{V1}/teams/{team['id']}",
            json={"region": "부산 해운대구"},
            headers=owner["headers"],
        )
        assert res.status_code == 200, res.text
        assert res.json()["region"] == "부산 해운대구"

        # 다시 읽어도 남아 있어야 한다.
        again = client.get(f"{V1}/teams/{team['id']}", headers=owner["headers"])
        assert again.json()["region"] == "부산 해운대구"

    def test_이름도_고친다(self, client, owner, team):
        res = client.patch(
            f"{V1}/teams/{team['id']}", json={"name": "천둥FC"}, headers=owner["headers"]
        )
        assert res.status_code == 200, res.text
        assert res.json()["name"] == "천둥FC"

    def test_보낸_것만_바뀐다(self, client, owner, team):
        """지역만 보내면 이름은 그대로다."""
        res = client.patch(
            f"{V1}/teams/{team['id']}", json={"region": "대전"}, headers=owner["headers"]
        )
        assert res.json()["name"] == TEAM["name"]
        assert res.json()["region"] == "대전"

    def test_빈_본문이면_아무것도_안_바뀐다(self, client, owner, team):
        res = client.patch(f"{V1}/teams/{team['id']}", json={}, headers=owner["headers"])
        assert res.status_code == 200, res.text
        assert res.json()["name"] == TEAM["name"]
        assert res.json()["region"] == TEAM["region"]

    def test_주장이_아니면_403(self, client, owner, team):
        """구성원도 못 고친다 — 팀 정보는 소속 전체에게 보이는 값이다."""
        member_id = uuid4()
        register_user(member_id)
        client.post(
            f"{V1}/teams/{team['id']}/members", json={}, headers=_headers(member_id)
        )

        res = client.patch(
            f"{V1}/teams/{team['id']}",
            json={"region": "대구"},
            headers=_headers(member_id),
        )
        assert res.status_code == 403
        assert error_code(res) == "FORBIDDEN"

    def test_소속이_아니면_403(self, client, team):
        res = client.patch(
            f"{V1}/teams/{team['id']}", json={"region": "대구"}, headers=_headers()
        )
        assert res.status_code == 403

    def test_없는_팀은_404(self, client, owner):
        res = client.patch(
            f"{V1}/teams/{uuid4()}", json={"region": "대구"}, headers=owner["headers"]
        )
        assert res.status_code == 404
        assert error_code(res) == "TEAM_NOT_FOUND"

    def test_빈_문자열은_422(self, client, owner, team):
        res = client.patch(
            f"{V1}/teams/{team['id']}", json={"name": ""}, headers=owner["headers"]
        )
        assert res.status_code == 422

    def test_null_로는_못_지운다(self, client, owner, team):
        """🔴 둘 다 NOT NULL 이라 "안 정한 상태"가 없다 — 카드의 `tagline` 과 다르다."""
        res = client.patch(
            f"{V1}/teams/{team['id']}", json={"region": None}, headers=owner["headers"]
        )
        assert res.status_code == 422

    def test_종목은_못_바꾼다(self, client, owner, team):
        """🔴 포지션·스쿼드·경기가 그 값에 매달려 있다 — 본문에 자리가 없어 무시된다."""
        res = client.patch(
            f"{V1}/teams/{team['id']}",
            json={"sport_code": "baseball"},
            headers=owner["headers"],
        )
        assert res.status_code == 200, res.text
        assert res.json()["sport_code"] == TEAM["sport_code"]


class TestSetMemberRole:
    """주장 세우기 — `paik` 35번.

    🔴 그전에는 `LAST_OWNER` 가 "다른 주장을 먼저 세워야 합니다"라고 안내하면서
    **세울 경로를 주지 않았다.** 그 안내를 실행 가능하게 만드는 것이 이 경로다.
    """

    def _join(self, client, team, headers):
        assert (
            client.post(
                f"{V1}/teams/{team['id']}/members", json={}, headers=headers
            ).status_code
            == 201
        )

    def _member(self, client, team, headers):
        user_id = uuid4()
        register_user(user_id)
        member_headers = _headers(user_id)
        self._join(client, team, member_headers)
        return {"id": user_id, "headers": member_headers}

    def test_주장이_다른_사람을_주장으로_세운다(self, client, owner, team):
        member = self._member(client, team, owner["headers"])
        res = client.patch(
            f"{V1}/teams/{team['id']}/members/{member['id']}",
            json={"role": "owner"},
            headers=owner["headers"],
        )
        assert res.status_code == 200, res.text
        roles = {m["user_id"]: m["role"] for m in res.json()["members"]}
        assert roles[str(member["id"])] == "owner"
        # 🔴 기존 주장은 그대로 주장이다 — 넘기고 나가려면 세운 뒤 나간다.
        assert roles[str(owner["id"])] == "owner"

    def test_세우고_나면_기존_주장이_나갈_수_있다(self, client, owner, team):
        """이 항목의 요점이다 — 막혀 있던 길이 실제로 뚫렸는지 본다."""
        member = self._member(client, team, owner["headers"])
        blocked = client.delete(
            f"{V1}/teams/{team['id']}/members/{owner['id']}",
            headers=owner["headers"],
        )
        assert blocked.status_code == 409
        assert error_code(blocked) == "LAST_OWNER"

        client.patch(
            f"{V1}/teams/{team['id']}/members/{member['id']}",
            json={"role": "owner"},
            headers=owner["headers"],
        )
        freed = client.delete(
            f"{V1}/teams/{team['id']}/members/{owner['id']}",
            headers=owner["headers"],
        )
        assert freed.status_code == 204, freed.text

    def test_일반_구성원은_못_바꾼다(self, client, owner, team):
        member = self._member(client, team, owner["headers"])
        res = client.patch(
            f"{V1}/teams/{team['id']}/members/{member['id']}",
            json={"role": "owner"},
            headers=member["headers"],
        )
        assert res.status_code == 403

    def test_소속이_아닌_사람은_404(self, client, owner, team):
        res = client.patch(
            f"{V1}/teams/{team['id']}/members/{uuid4()}",
            json={"role": "owner"},
            headers=owner["headers"],
        )
        assert res.status_code == 404
        assert error_code(res) == "NOT_A_MEMBER"

    def test_모르는_역할은_422(self, client, owner, team):
        member = self._member(client, team, owner["headers"])
        res = client.patch(
            f"{V1}/teams/{team['id']}/members/{member['id']}",
            json={"role": "captain"},
            headers=owner["headers"],
        )
        assert res.status_code == 422


class TestDisbandTeam:
    """팀 해체 — `paik` 35번. **행을 지우지 않는다.**"""

    def test_주장이_해체하면_204(self, client, owner, team):
        res = client.delete(f"{V1}/teams/{team['id']}", headers=owner["headers"])
        assert res.status_code == 204, res.text

    def test_해체해도_팀은_읽힌다(self, client, owner, team):
        """🔴 지난 경기·평가가 이 팀 이름을 가리킨다 — 404 로 숨기지 않는다."""
        client.delete(f"{V1}/teams/{team['id']}", headers=owner["headers"])
        res = client.get(f"{V1}/teams/{team['id']}", headers=owner["headers"])
        assert res.status_code == 200
        assert res.json()["disbanded_at"] is not None
        # 구성원은 전부 내보내진다 — 그래야 `GET /me` 의 `teams` 에서 사라진다.
        assert res.json()["members"] == []

    def test_해체된_팀에는_못_들어간다(self, client, owner, team):
        """🔴 이것이 컬럼을 둔 이유다 — 자기-가입은 아무나 할 수 있어서
        표시가 없으면 해체한 팀이 되살아난다."""
        client.delete(f"{V1}/teams/{team['id']}", headers=owner["headers"])
        res = client.post(
            f"{V1}/teams/{team['id']}/members", json={}, headers=_headers()
        )
        assert res.status_code == 409
        assert error_code(res) == "TEAM_DISBANDED"

    def test_해체된_팀은_못_고치고_못_초대한다(self, client, owner, team):
        client.delete(f"{V1}/teams/{team['id']}", headers=owner["headers"])
        edited = client.patch(
            f"{V1}/teams/{team['id']}",
            json={"name": "부활FC"},
            headers=owner["headers"],
        )
        assert error_code(edited) == "TEAM_DISBANDED"

        invited = client.post(
            f"{V1}/teams/{team['id']}/invitations",
            json={"invited_user_id": str(uuid4())},
            headers=owner["headers"],
        )
        assert error_code(invited) == "TEAM_DISBANDED"

    def test_두_번_해체하면_409(self, client, owner, team):
        client.delete(f"{V1}/teams/{team['id']}", headers=owner["headers"])
        res = client.delete(f"{V1}/teams/{team['id']}", headers=owner["headers"])
        assert res.status_code == 409
        assert error_code(res) == "TEAM_DISBANDED"

    def test_일반_구성원은_해체_못_한다(self, client, owner, team):
        member_headers = _headers()
        client.post(
            f"{V1}/teams/{team['id']}/members", json={}, headers=member_headers
        )
        res = client.delete(f"{V1}/teams/{team['id']}", headers=member_headers)
        assert res.status_code == 403

    def test_앞으로_있을_경기가_있으면_409(self, client, owner, team):
        """🔴 상대 팀에는 약속이다 — 조용히 사라지면 그쪽 판이 깨진다."""
        from uuid import UUID

        register_upcoming_match(UUID(team["id"]))
        res = client.delete(f"{V1}/teams/{team['id']}", headers=owner["headers"])
        assert res.status_code == 409
        assert error_code(res) == "TEAM_HAS_UPCOMING_MATCH"

    def test_없는_팀은_404(self, client, owner):
        res = client.delete(f"{V1}/teams/{uuid4()}", headers=owner["headers"])
        assert res.status_code == 404

    def test_인증이_필요하다(self, client, team):
        assert client.delete(f"{V1}/teams/{team['id']}").status_code == 401
