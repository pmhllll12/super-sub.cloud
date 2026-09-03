"""스쿼드가 **실제 PostgreSQL 에서** 도는지 확인한다.

계약 테스트(`test_squad_router.py`)는 스텁을 끼우므로 조인·외래키·유일 제약을
보지 못한다. 여기서 보는 것은 넷이다.

1. 등재가 `player_card -> user` 와 `position` 을 실제로 조인해 표시값을 채운다
2. `squad_member (squad_id, player_card_id)` 유일 제약이 **DB 에 실재한다**(부록 D.7)
3. `squad.public_slug` 유일 제약이 실재한다
4. 스쿼드를 지우면 등재도 따라 지워진다(CASCADE)

🔴 그리고 **`team`·`team_member`·`position`·`user` 를 원시 쿼리로 읽는 자리**가
여기 걸린다. 저쪽 컬럼 이름이 바뀌면 파이썬이 잡아 주지 않으므로 이 검사가 유일한
방어선이다 — 지우지 말 것.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.card.adapter.outbound.orm.squad_orm import SquadOrm
from tests.conftest import V1

pytestmark = pytest.mark.db

PASSWORD = "supersub2026"


def _signup(db_client, nickname):
    email = f"squad-{uuid.uuid4().hex[:12]}@super-sub.example"
    res = db_client.post(
        f"{V1}/auth/signup",
        json={"email": email, "password": PASSWORD, "nickname": nickname},
    )
    assert res.status_code == 201, res.text
    login = db_client.post(
        f"{V1}/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    card = db_client.post(f"{V1}/me/card", headers=headers)
    assert card.status_code in (200, 201), card.text
    return {
        "id": uuid.UUID(res.json()["id"]),
        "headers": headers,
        "card_id": uuid.UUID(card.json()["id"]),
        "nickname": nickname,
    }


@pytest.fixture
def team(db_client):
    """축구 팀 하나와 주장·구성원. 둘 다 카드를 갖고 있다."""
    owner = _signup(db_client, "주장")
    member = _signup(db_client, "구성원")

    created = db_client.post(
        f"{V1}/teams",
        json={
            "name": f"스쿼드팀-{uuid.uuid4().hex[:6]}",
            "region": "서울",
            "sport_code": "football",
        },
        headers=owner["headers"],
    )
    assert created.status_code == 201, created.text
    team_id = uuid.UUID(created.json()["id"])

    # 본문이 비면 **본인이 가입**한다(`AddMemberSchema`). `json={}` 를 빠뜨리면
    # 본문 자체가 없어 422 다.
    joined = db_client.post(
        f"{V1}/teams/{team_id}/members", json={}, headers=member["headers"]
    )
    assert joined.status_code == 201, joined.text
    return {"id": team_id, "owner": owner, "member": member}


def _create_squad(db_client, team):
    res = db_client.post(
        f"{V1}/teams/{team['id']}/squad", headers=team["owner"]["headers"]
    )
    assert res.status_code == 201, res.text
    return res.json()


def _enlist(db_client, team, card_id, position_code="GK"):
    return db_client.post(
        f"{V1}/teams/{team['id']}/squad/members",
        json={"player_card_id": str(card_id), "position_code": position_code},
        headers=team["owner"]["headers"],
    )


class TestEnlist:
    def test_등재가_닉네임과_포지션을_조인해_채운다(self, db_client, team):
        """🔴 `user.nickname`·`position.label` 을 원시 쿼리로 읽는 자리다."""
        _create_squad(db_client, team)
        res = _enlist(db_client, team, team["member"]["card_id"])
        assert res.status_code == 201, res.text

        member = res.json()["members"][0]
        assert member["nickname"] == "구성원"
        assert member["position_code"] == "GK"
        assert member["position_label"] == "골키퍼"
        assert member["card_public_slug"]

    def test_팀_종목의_포지션만_찾는다(self, db_client, team):
        """야구 `P` 는 `position` 에 있지만 축구 팀에는 없다 — 양성 대조가 위 검사다."""
        _create_squad(db_client, team)
        res = _enlist(db_client, team, team["member"]["card_id"], "P")
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "UNKNOWN_POSITION"

    def test_팀원이_아닌_사람의_카드는_거부한다(self, db_client, team):
        """`team_member.left_at` 을 보는 자리다."""
        outsider = _signup(db_client, "남")
        _create_squad(db_client, team)
        res = _enlist(db_client, team, outsider["card_id"])
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "NOT_TEAM_MEMBER"


class TestConstraints:
    def test_같은_카드는_한_번만_등재된다(self, db_client, team):
        """부록 D.7. **막히지 않으면 그 제약은 없는 것이다.**"""
        _create_squad(db_client, team)
        assert _enlist(db_client, team, team["member"]["card_id"]).status_code == 201
        again = _enlist(db_client, team, team["member"]["card_id"], "DF")
        assert again.status_code == 409
        assert again.json()["error"]["code"] == "ALREADY_ENLISTED"

    def test_슬러그는_중복될_수_없다(self, db_client, db_session, team):
        squad = _create_squad(db_client, team)
        db_session.add(
            SquadOrm(
                id=uuid.uuid4(),
                team_id=team["id"],
                public_slug=squad["public_slug"],
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_스쿼드를_지우면_등재도_지워진다(self, db_client, db_session, team):
        squad = _create_squad(db_client, team)
        assert _enlist(db_client, team, team["member"]["card_id"]).status_code == 201
        squad_id = uuid.UUID(squad["id"])

        db_session.execute(
            text("DELETE FROM squad WHERE id = :id"), {"id": squad_id}
        )
        db_session.commit()

        left = db_session.execute(
            text("SELECT count(*) FROM squad_member WHERE squad_id = :id"),
            {"id": squad_id},
        ).scalar_one()
        assert left == 0


class TestReadPaths:
    def test_공개_슬러그로_인증_없이_읽힌다(self, db_client, team):
        squad = _create_squad(db_client, team)
        _enlist(db_client, team, team["member"]["card_id"])

        res = db_client.get(f"{V1}/squads/{squad['public_slug']}")
        assert res.status_code == 200, res.text
        assert res.json()["members"][0]["nickname"] == "구성원"

    def test_생성은_멱등이다(self, db_client, team):
        first = _create_squad(db_client, team)
        second = db_client.post(
            f"{V1}/teams/{team['id']}/squad", headers=team["owner"]["headers"]
        )
        assert second.status_code == 200
        assert second.json()["public_slug"] == first["public_slug"]

    def test_뺀_뒤에는_목록에서_사라진다(self, db_client, team):
        _create_squad(db_client, team)
        enlisted = _enlist(db_client, team, team["member"]["card_id"]).json()
        member_id = enlisted["members"][0]["id"]

        removed = db_client.delete(
            f"{V1}/teams/{team['id']}/squad/members/{member_id}",
            headers=team["owner"]["headers"],
        )
        assert removed.status_code == 200, removed.text
        assert removed.json()["members"] == []
