"""card/adapter/inbound/api/v1/squad_router.py — 계약 문서 3-7절.

스텁을 끼워 DB 없이 돈다. 실제 조인·유일 제약은 `test_squad_db.py` 가 본다.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.card.adapter.outbound.stub.squad_stub_repository import (
    register_card,
    register_role,
    register_team,
    reset_squads,
)
from app.core.security import issue_access_token
from tests.conftest import V1, error_code


def _headers(user_id):
    return {"Authorization": f"Bearer {issue_access_token(user_id)}"}


@pytest.fixture(autouse=True)
def _clean():
    reset_squads()
    yield
    reset_squads()


@pytest.fixture
def football():
    """축구 팀 하나와 주장·구성원, 그리고 각자의 카드."""
    team_id, owner, member, outsider = uuid4(), uuid4(), uuid4(), uuid4()
    register_team(team_id, "football")
    register_role(team_id, owner, "owner")
    register_role(team_id, member, "member")

    owner_card, member_card, outsider_card = uuid4(), uuid4(), uuid4()
    register_card(owner_card, owner, "주장")
    register_card(member_card, member, "구성원")
    register_card(outsider_card, outsider, "남")
    return {
        "id": team_id,
        "owner": owner,
        "member": member,
        "outsider": outsider,
        "owner_card": owner_card,
        "member_card": member_card,
        "outsider_card": outsider_card,
    }


def _create(client, team, actor):
    return client.post(f"{V1}/teams/{team['id']}/squad", headers=_headers(actor))


def _enlist(client, team, actor, card_id, position_code="GK", **extra):
    return client.post(
        f"{V1}/teams/{team['id']}/squad/members",
        json={
            "player_card_id": str(card_id),
            "position_code": position_code,
            **extra,
        },
        headers=_headers(actor),
    )


def _move(client, team, actor, member_id, **body):
    return client.patch(
        f"{V1}/teams/{team['id']}/squad/members/{member_id}",
        json=body,
        headers=_headers(actor),
    )


def _set_formation(client, team, actor, formation):
    return client.patch(
        f"{V1}/teams/{team['id']}/squad",
        json={"formation": formation},
        headers=_headers(actor),
    )


class TestCreateSquad:
    def test_인증이_필요하다(self, client, football):
        assert client.post(f"{V1}/teams/{football['id']}/squad").status_code == 401

    def test_주장은_만들_수_있다(self, client, football):
        res = _create(client, football, football["owner"])
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["team_id"] == str(football["id"])
        assert body["public_slug"]
        assert body["members"] == []

    def test_구성원은_만들_수_없다(self, client, football):
        res = _create(client, football, football["member"])
        assert res.status_code == 403
        assert error_code(res) == "FORBIDDEN"

    def test_소속이_아니면_만들_수_없다(self, client, football):
        res = _create(client, football, football["outsider"])
        assert res.status_code == 403

    def test_없는_팀은_404_다(self, client):
        res = client.post(f"{V1}/teams/{uuid4()}/squad", headers=_headers(uuid4()))
        assert res.status_code == 404
        assert error_code(res) == "TEAM_NOT_FOUND"

    def test_두_번_불러도_슬러그가_그대로다(self, client, football):
        """🔴 멱등이다. 재시도로 공유 링크가 바뀌면 안 된다."""
        first = _create(client, football, football["owner"])
        second = _create(client, football, football["owner"])

        assert first.status_code == 201
        assert second.status_code == 200
        assert first.json()["public_slug"] == second.json()["public_slug"]
        assert first.json()["id"] == second.json()["id"]


class TestReadTeamSquad:
    def test_인증이_필요하다(self, client, football):
        assert client.get(f"{V1}/teams/{football['id']}/squad").status_code == 401

    def test_구성원은_볼_수_있다(self, client, football):
        _create(client, football, football["owner"])
        res = client.get(
            f"{V1}/teams/{football['id']}/squad", headers=_headers(football["member"])
        )
        assert res.status_code == 200, res.text

    def test_소속이_아니면_볼_수_없다(self, client, football):
        """팀 id 로 남의 팀 구성을 훑는 것을 막는다."""
        _create(client, football, football["owner"])
        res = client.get(
            f"{V1}/teams/{football['id']}/squad",
            headers=_headers(football["outsider"]),
        )
        assert res.status_code == 403

    def test_아직_안_만들었으면_404_다(self, client, football):
        res = client.get(
            f"{V1}/teams/{football['id']}/squad", headers=_headers(football["owner"])
        )
        assert res.status_code == 404
        assert error_code(res) == "SQUAD_NOT_FOUND"


class TestEnlist:
    def test_주장은_팀원_카드를_등재할_수_있다(self, client, football):
        _create(client, football, football["owner"])
        res = _enlist(client, football, football["owner"], football["member_card"])
        assert res.status_code == 201, res.text

        members = res.json()["members"]
        assert len(members) == 1
        assert members[0]["player_card_id"] == str(football["member_card"])
        assert members[0]["nickname"] == "구성원"
        assert members[0]["position_code"] == "GK"
        assert members[0]["position_label"] == "골키퍼"
        assert members[0]["card_public_slug"]

    def test_구성원은_등재할_수_없다(self, client, football):
        _create(client, football, football["owner"])
        res = _enlist(client, football, football["member"], football["member_card"])
        assert res.status_code == 403

    def test_팀원이_아닌_사람의_카드는_거부한다(self, client, football):
        """🔴 스쿼드는 **팀의** 카드 묶음이다."""
        _create(client, football, football["owner"])
        res = _enlist(client, football, football["owner"], football["outsider_card"])
        assert res.status_code == 422
        assert error_code(res) == "NOT_TEAM_MEMBER"

    def test_없는_카드는_404_다(self, client, football):
        _create(client, football, football["owner"])
        res = _enlist(client, football, football["owner"], uuid4())
        assert res.status_code == 404
        assert error_code(res) == "CARD_NOT_FOUND"

    def test_다른_종목의_포지션은_거부한다(self, client, football):
        """야구 `P`(투수)는 축구 팀에 없다."""
        _create(client, football, football["owner"])
        res = _enlist(
            client, football, football["owner"], football["member_card"], "P"
        )
        assert res.status_code == 422
        assert error_code(res) == "UNKNOWN_POSITION"

    def test_같은_카드를_두_번_넣으면_409_다(self, client, football):
        """부록 D.7 — 스쿼드당 카드 1회 등재."""
        _create(client, football, football["owner"])
        _enlist(client, football, football["owner"], football["member_card"])
        res = _enlist(
            client, football, football["owner"], football["member_card"], "DF"
        )
        assert res.status_code == 409
        assert error_code(res) == "ALREADY_ENLISTED"

    def test_스쿼드가_없으면_404_다(self, client, football):
        res = _enlist(client, football, football["owner"], football["member_card"])
        assert res.status_code == 404
        assert error_code(res) == "SQUAD_NOT_FOUND"


class TestDischarge:
    def test_주장은_뺄_수_있다(self, client, football):
        _create(client, football, football["owner"])
        enlisted = _enlist(
            client, football, football["owner"], football["member_card"]
        ).json()
        member_id = enlisted["members"][0]["id"]

        res = client.delete(
            f"{V1}/teams/{football['id']}/squad/members/{member_id}",
            headers=_headers(football["owner"]),
        )
        assert res.status_code == 200, res.text
        assert res.json()["members"] == []

    def test_구성원은_뺄_수_없다(self, client, football):
        _create(client, football, football["owner"])
        enlisted = _enlist(
            client, football, football["owner"], football["member_card"]
        ).json()
        member_id = enlisted["members"][0]["id"]

        res = client.delete(
            f"{V1}/teams/{football['id']}/squad/members/{member_id}",
            headers=_headers(football["member"]),
        )
        assert res.status_code == 403

    def test_없는_등재는_404_다(self, client, football):
        _create(client, football, football["owner"])
        res = client.delete(
            f"{V1}/teams/{football['id']}/squad/members/{uuid4()}",
            headers=_headers(football["owner"]),
        )
        assert res.status_code == 404
        assert error_code(res) == "MEMBER_NOT_FOUND"

    def test_남의_스쿼드_등재는_뺄_수_없다(self, client, football):
        """🔴 id 만 알면 남의 스쿼드에서 카드를 뺄 수 있으면 안 된다."""
        _create(client, football, football["owner"])
        mine = _enlist(
            client, football, football["owner"], football["member_card"]
        ).json()["members"][0]["id"]

        other_team, other_owner = uuid4(), uuid4()
        register_team(other_team, "football")
        register_role(other_team, other_owner, "owner")
        client.post(f"{V1}/teams/{other_team}/squad", headers=_headers(other_owner))

        res = client.delete(
            f"{V1}/teams/{other_team}/squad/members/{mine}",
            headers=_headers(other_owner),
        )
        assert res.status_code == 404
        assert error_code(res) == "MEMBER_NOT_FOUND"


class TestGridOnEnlist:
    """등재하면서 홈 판 칸에 올리기 (미결 `paik` 9번)."""

    def test_칸과_함께_등재한다(self, client, football):
        _create(client, football, football["owner"])
        res = _enlist(
            client, football, football["owner"], football["member_card"],
            grid_col=1, grid_row=2,
        )
        assert res.status_code == 201, res.text
        m = res.json()["members"][0]
        assert (m["grid_col"], m["grid_row"]) == (1, 2)

    def test_칸_없이_등재하면_null_이다(self, client, football):
        _create(client, football, football["owner"])
        m = _enlist(
            client, football, football["owner"], football["member_card"]
        ).json()["members"][0]
        assert m["grid_col"] is None and m["grid_row"] is None

    def test_칸을_한쪽만_주면_422_다(self, client, football):
        _create(client, football, football["owner"])
        res = _enlist(
            client, football, football["owner"], football["member_card"],
            grid_col=1,
        )
        assert res.status_code == 422

    def test_픽셀_좌표는_거부한다(self, client, football):
        _create(client, football, football["owner"])
        res = _enlist(
            client, football, football["owner"], football["member_card"],
            grid_col=340, grid_row=512,
        )
        assert res.status_code == 422


class TestSetFormation:
    """홈 판의 판 크기 저장 (미결 `paik` 9번)."""

    def test_주장은_판_크기를_저장한다(self, client, football):
        _create(client, football, football["owner"])
        res = _set_formation(client, football, football["owner"], "5:5")
        assert res.status_code == 200, res.text
        assert res.json()["formation"] == "5:5"

    def test_기본은_null_이다(self, client, football):
        squad = _create(client, football, football["owner"]).json()
        assert squad["formation"] is None

    def test_구성원은_못_바꾼다(self, client, football):
        _create(client, football, football["owner"])
        assert _set_formation(
            client, football, football["member"], "5:5"
        ).status_code == 403

    def test_스쿼드가_없으면_404_다(self, client, football):
        res = _set_formation(client, football, football["owner"], "5:5")
        assert res.status_code == 404
        assert error_code(res) == "SQUAD_NOT_FOUND"

    def test_인증이_필요하다(self, client, football):
        res = client.patch(
            f"{V1}/teams/{football['id']}/squad", json={"formation": "5:5"}
        )
        assert res.status_code == 401


class TestMoveMember:
    """등재의 포지션·판 배치 바꾸기 (미결 `paik` 9번). 3-7 「포지션 바꾸기」도 여기."""

    def _enlisted(self, client, football):
        _create(client, football, football["owner"])
        return _enlist(
            client, football, football["owner"], football["member_card"], "GK"
        ).json()["members"][0]["id"]

    def test_포지션과_칸을_함께_바꾼다(self, client, football):
        member_id = self._enlisted(client, football)
        res = _move(
            client, football, football["owner"], member_id,
            position_code="DF", grid_col=0, grid_row=2,
        )
        assert res.status_code == 200, res.text
        m = res.json()["members"][0]
        assert m["position_code"] == "DF"
        assert (m["grid_col"], m["grid_row"]) == (0, 2)

    def test_칸을_비우면_판에서만_빠진다(self, client, football):
        member_id = self._enlisted(client, football)
        _move(
            client, football, football["owner"], member_id,
            position_code="GK", grid_col=1, grid_row=0,
        )
        res = _move(
            client, football, football["owner"], member_id,
            position_code="GK", grid_col=None, grid_row=None,
        )
        assert res.status_code == 200, res.text
        m = res.json()["members"][0]
        assert m["position_code"] == "GK"           # 등재는 남는다
        assert m["grid_col"] is None and m["grid_row"] is None

    def test_칸을_한쪽만_주면_422_다(self, client, football):
        member_id = self._enlisted(client, football)
        res = _move(
            client, football, football["owner"], member_id,
            position_code="GK", grid_row=1,
        )
        assert res.status_code == 422

    def test_없는_포지션은_422_다(self, client, football):
        member_id = self._enlisted(client, football)
        res = _move(
            client, football, football["owner"], member_id, position_code="XX"
        )
        assert res.status_code == 422
        assert error_code(res) == "UNKNOWN_POSITION"

    def test_없는_등재는_404_다(self, client, football):
        _create(client, football, football["owner"])
        res = _move(
            client, football, football["owner"], uuid4(), position_code="GK"
        )
        assert res.status_code == 404
        assert error_code(res) == "MEMBER_NOT_FOUND"

    def test_구성원은_못_옮긴다(self, client, football):
        member_id = self._enlisted(client, football)
        res = _move(
            client, football, football["member"], member_id, position_code="DF"
        )
        assert res.status_code == 403

    def test_남의_스쿼드_등재는_못_옮긴다(self, client, football):
        """🔴 discharge 와 같은 벽 — id 만으로 남의 스쿼드를 건드릴 수 없다."""
        member_id = self._enlisted(client, football)

        other_team, other_owner = uuid4(), uuid4()
        register_team(other_team, "football")
        register_role(other_team, other_owner, "owner")
        client.post(f"{V1}/teams/{other_team}/squad", headers=_headers(other_owner))

        res = client.patch(
            f"{V1}/teams/{other_team}/squad/members/{member_id}",
            json={"position_code": "GK"},
            headers=_headers(other_owner),
        )
        assert res.status_code == 404
        assert error_code(res) == "MEMBER_NOT_FOUND"


class TestPublicSquad:
    def test_인증_없이_볼_수_있다(self, client, football):
        """공유용이다 — 공개 카드와 같은 결이다."""
        slug = _create(client, football, football["owner"]).json()["public_slug"]
        res = client.get(f"{V1}/squads/{slug}")
        assert res.status_code == 200, res.text
        assert res.json()["public_slug"] == slug

    def test_없는_슬러그는_404_다(self, client):
        res = client.get(f"{V1}/squads/없는슬러그")
        assert res.status_code == 404
        assert error_code(res) == "SQUAD_NOT_FOUND"
