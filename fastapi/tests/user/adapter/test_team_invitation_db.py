"""팀 초대를 **실제 PostgreSQL** 에 대고 확인한다. `min` 20번.

스텁이 답할 수 없는 것들이다:

- **알림이 실제로 쌓이는가**(받은 사람에게 발송, 팀 주장에게 수락·거절) —
  `notification`은 `user` 컨텍스트 안이지만 다른 테이블이라 원시 SQL로 대조한다
- 수락하면 `team_member` 행이 **실제로** 생기는가(기존 `JoinTeamUseCase` 재사용 경로)
- `team_invitation`이 저장·조회되는가
- 🔴 **`GET /me/invitations` 가 `squad.public_slug` 를 실제로 읽는가**
  (`paik` 37번) — `squad` 는 `card` 컨텍스트라 원시 SQL(`table()`/`column()`)
  로 읽는다. 저쪽 컬럼 이름이 바뀌어도 파이썬이 안 잡아 주므로 **여기가
  유일한 방어선이다**(`fastapi/CLAUDE.md` 「테스트는 두 층이다」)
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
    # 🔴 `squad.team_id` 는 RESTRICT 라(부록 D.6 이 팀 해체 처리를 안 정했다)
    # 팀보다 먼저 지워야 한다 — 안 그러면 다음 검사가 남은 행에 걸린다.
    db_session.execute(
        text("delete from squad_member where squad_id in "
             "(select id from squad where team_id = :t)"),
        {"t": team_id},
    )
    db_session.execute(text("delete from squad where team_id = :t"), {"t": team_id})
    db_session.execute(text("delete from team where id = :t"), {"t": team_id})
    for acc in (owner, candidate):
        db_session.execute(
            text('delete from "user" where id = :i'), {"i": acc["id"]}
        )
    db_session.commit()


def _invite(db_client, world, position_code=None):
    body = {"invited_user_id": str(world["candidate"]["id"])}
    if position_code is not None:
        body["position_code"] = position_code
    res = db_client.post(
        f"{V1}/teams/{world['team_id']}/invitations",
        json=body,
        headers=world["owner"]["headers"],
    )
    assert res.status_code == 201, res.text
    return uuid.UUID(res.json()["id"])


def _my_invitations(db_client, world):
    res = db_client.get(f"{V1}/me/invitations", headers=world["candidate"]["headers"])
    assert res.status_code == 200, res.text
    return res.json()


class TestReceivedRowCarriesTeam:
    """`paik` 37번 — 받는 사람은 그 팀 소속이 아니라 초대 한 줄만 보고 정한다."""

    def test_팀_이름_지역_종목이_실린다(self, db_client, world):
        _invite(db_client, world)
        row = _my_invitations(db_client, world)[0]
        assert row["team_name"] == TEAM["name"]
        assert row["team_region"] == TEAM["region"]
        assert row["team_sport_code"] == TEAM["sport_code"]

    def test_스쿼드_슬러그를_실제_squad_테이블에서_읽는다(
        self, db_client, db_session, world
    ):
        """🔴 `squad` 는 `card` 컨텍스트라 원시 SQL로 읽는 자리다.

        스텁으로는 컬럼 이름이 갈려도 통과한다 — 실물과 대조하는 것은 여기뿐이다.
        """
        created = db_client.post(
            f"{V1}/teams/{world['team_id']}/squad",
            headers=world["owner"]["headers"],
        )
        assert created.status_code in (200, 201), created.text
        slug = created.json()["public_slug"]

        _invite(db_client, world)
        assert _my_invitations(db_client, world)[0]["squad_public_slug"] == slug

        # 그 슬러그로 실제 판을 열 수 있어야 쓸모가 있다(누구나 읽는 경로).
        public = db_client.get(f"{V1}/squads/{slug}")
        assert public.status_code == 200, public.text

    def test_스쿼드가_없으면_null_이다(self, db_client, world):
        _invite(db_client, world)
        assert _my_invitations(db_client, world)[0]["squad_public_slug"] is None

    def test_부르는_자리가_실제로_저장되고_이름까지_나온다(
        self, db_client, db_session, world
    ):
        invitation_id = _invite(db_client, world, "GK")
        stored = db_session.execute(
            text("select position_id from team_invitation where id = :i"),
            {"i": invitation_id},
        ).scalar_one()
        assert stored is not None

        row = _my_invitations(db_client, world)[0]
        assert row["position_code"] == "GK"
        assert row["position_label"] == "골키퍼"


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


class TestAcceptSeatsOnSquad:
    """🔴 수락하면 **초대받은 자리로 스쿼드에 등재**된다(2026-09-17, 정어진).

    수락은 받은 사람이 하는데 등재 경로는 주장만 부를 수 있어, 전에는 수락해도 판에
    안 섰다(주장 화면에 「수락 대기중」이 남고 새로고침하면 사라졌다). `squad`·
    `squad_member`·`player_card` 는 `card` 컨텍스트라 원시 SQL로 쓰는 자리 — 여기가
    실물과 대조하는 유일한 곳이다.
    """

    def _squad_member(self, db_session, world):
        return db_session.execute(
            text(
                "select p.code, sm.grid_col, sm.grid_row from squad_member sm "
                "join squad s on s.id = sm.squad_id "
                "join player_card pc on pc.id = sm.player_card_id "
                "join position p on p.id = sm.position_id "
                "where s.team_id = :t and pc.user_id = :u"
            ),
            {"t": world["team_id"], "u": world["candidate"]["id"]},
        ).all()

    def _accept(self, db_client, world, invitation_id):
        res = db_client.post(
            f"{V1}/me/invitations/{invitation_id}/accept",
            headers=world["candidate"]["headers"],
        )
        assert res.status_code == 200, res.text

    def _prepare(self, db_client, world, *, squad=True, card=True):
        if squad:
            made = db_client.post(
                f"{V1}/teams/{world['team_id']}/squad", headers=world["owner"]["headers"]
            )
            assert made.status_code in (200, 201), made.text
        if card:
            made = db_client.post(f"{V1}/me/card", headers=world["candidate"]["headers"])
            assert made.status_code in (200, 201), made.text

    def test_부른_자리로_칸_없이_등재된다(self, db_client, db_session, world):
        self._prepare(db_client, world)
        self._accept(db_client, world, _invite(db_client, world, "GK"))
        assert [tuple(r) for r in self._squad_member(db_session, world)] == [("GK", None, None)]

    def test_주장_화면의_스쿼드_응답에도_실린다(self, db_client, db_session, world):
        self._prepare(db_client, world)
        self._accept(db_client, world, _invite(db_client, world, "DF"))
        squad = db_client.get(
            f"{V1}/teams/{world['team_id']}/squad", headers=world["owner"]["headers"]
        )
        assert squad.status_code == 200, squad.text
        assert [m["position_code"] for m in squad.json()["members"]] == ["DF"]

    def test_자리를_안_정한_초대는_등재하지_않는다(self, db_client, db_session, world):
        self._prepare(db_client, world)
        self._accept(db_client, world, _invite(db_client, world))
        assert self._squad_member(db_session, world) == []

    def test_스쿼드가_없어도_수락은_된다(self, db_client, db_session, world):
        self._prepare(db_client, world, squad=False)
        self._accept(db_client, world, _invite(db_client, world, "GK"))
        assert self._squad_member(db_session, world) == []

    def test_카드가_없어도_수락은_된다(self, db_client, db_session, world):
        self._prepare(db_client, world, card=False)
        self._accept(db_client, world, _invite(db_client, world, "GK"))
        assert self._squad_member(db_session, world) == []


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
