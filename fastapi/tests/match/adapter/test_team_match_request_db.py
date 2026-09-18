"""팀 대 팀 경기 신청을 **실제 PostgreSQL** 에 대고 확인한다. `paik` 17번.

스텁이 답할 수 없는 것들이다:

- `opponent_team_id`가 실제로 저장·조회되는가
- **알림이 실제로 쌓이는가**(대상 팀 주장에게 신청, 신청 팀에 수락/거절,
  동시 확정 방지로 정리된 쪽 양쪽에게) — `notification`은 `match`가 임포트
  못 하는 남의 테이블이라 원시 SQL로 직접 대조한다
- 동시 확정 방지가 실제 트랜잭션에서 두 팀 다 정리하는가
- 🔴 **팀 이름·지역을 `team` 에서 그때그때 읽는가**(`paik` 31번) — `team` 은
  `user` 컨텍스트라 원시 SQL(`table()`/`column()`)로 읽는다. 저쪽 컬럼 이름이
  바뀌어도 파이썬이 안 잡아 주므로 **여기가 유일한 방어선이다**
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


class TestDuplicateGuard:
    """겹쳐 걸기 방지가 **실물 SQL 로도** 도는가 (2026-09-18).

    계약 테스트(`test_team_match_request_router.py`)는 스텁의 파이썬 비교를 볼
    뿐이다. 여기서 보는 것은 저 `or_`/`and_` 조합이 PostgreSQL 에서 같은 답을
    내는가, 그리고 **지난 경기는 안 막는가**다 — 뒤엣것은 API 로는 과거 시각을
    못 넣어서(`PAST_MATCH`) 스텁으로 만들 수 없는 상황이다.
    """

    def _create(self, db_client, world, **kw):
        return db_client.post(
            f"{V1}/teams/{world['team_a']}/match-requests",
            json={
                "target_team_id": str(world["team_b"]),
                "played_at": kw.get("played_at", _future()),
                "place": "강남 풋살장",
            },
            headers=world["a_owner"]["headers"],
        )

    def test_잡힌_경기가_있으면_실물에서도_409(self, db_client, world):
        request_id = self._create(db_client, world).json()["id"]
        accepted = db_client.post(
            f"{V1}/teams/{world['team_b']}/match-requests/{request_id}/accept",
            headers=world["b_owner"]["headers"],
        )
        assert accepted.status_code == 200, accepted.text

        again = self._create(db_client, world)
        assert again.status_code == 409, again.text
        assert error_code(again) == "TEAM_MATCH_REQUEST_ALREADY_LIVE"

    def test_지난_경기는_막지_않는다(self, db_client, db_session, world):
        """🔴 안 그러면 **한 번 붙은 팀과는 다시는 못 붙는다.**"""
        request_id = self._create(db_client, world).json()["id"]
        db_client.post(
            f"{V1}/teams/{world['team_b']}/match-requests/{request_id}/accept",
            headers=world["b_owner"]["headers"],
        )
        # API 로는 과거 시각을 넣을 수 없으므로(`PAST_MATCH`) 직접 민다.
        db_session.execute(
            text(
                "update team_match_request set proposed_played_at = :t"
                " where id = :i"
            ),
            {"t": datetime.now(timezone.utc) - timedelta(days=1), "i": request_id},
        )
        db_session.commit()

        again = self._create(db_client, world)
        assert again.status_code == 201, again.text


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


class TestTeamNamesFromRealTable:
    """`paik` 31번 — 표시용 팀 값이 실제 `team` 테이블에서 온다."""

    def _create(self, db_client, world):
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
        return res.json()

    def test_두_팀의_이름과_지역이_실물에서_온다(self, db_client, world):
        body = self._create(db_client, world)
        assert body["requester_team_name"] == "팀A"
        assert body["target_team_name"] == "팀B"
        assert body["requester_team_region"] == "서울"
        assert body["target_team_region"] == "서울"

    def test_팀_이름을_고치면_다음_조회에_바로_반영된다(self, db_client, world):
        """🔴 이것이 「화면에서 캐시하지 마십시오」의 근거다(항목의 「하지 말 것」).

        값이 신청 행에 **복사돼 있었다면** 옛 이름이 그대로 남는다 — 매번
        `team` 에서 읽기 때문에 안 남는다.
        """
        self._create(db_client, world)

        renamed = db_client.patch(
            f"{V1}/teams/{world['team_a']}",
            json={"name": "천둥FC", "region": "부산 해운대구"},
            headers=world["a_owner"]["headers"],
        )
        assert renamed.status_code == 200, renamed.text

        rows = db_client.get(
            f"{V1}/teams/{world['team_b']}/match-requests",
            headers=world["b_owner"]["headers"],
        ).json()
        assert [r["requester_team_name"] for r in rows] == ["천둥FC"]
        assert [r["requester_team_region"] for r in rows] == ["부산 해운대구"]


class TestSquadSlugFromRealTable:
    """`paik` 22번 후속 — 대기 화면이 상대 팀 판을 그릴 **공개 슬러그**.

    🔴 **화면에 박힌 마지막 mock 을 걷는 값이다.** 이게 없으면 대기 팝업이
    상대 팀 이름·판을 붙박이 목록에서 찾고, 그 목록에 없는 진짜 팀이 수락하면
    이름이 「상대 팀」으로 나오고 판이 빈다.

    🔴 `squad` 는 `card` 컨텍스트라 **원시 SQL 로 읽는다** — 그래서 이 DB
    테스트가 유일한 방어선이다(`fastapi/CLAUDE.md` 「테스트는 두 층이다」).
    """

    def _create(self, db_client, world):
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
        return res.json()

    def test_스쿼드가_없으면_None_이고_그게_정상이다(self, db_client, world):
        """🔴 빈 문자열로 채우지 않는다 — 스쿼드 생성이 멱등이라 늦게 생긴다."""
        body = self._create(db_client, world)
        assert body["requester_squad_public_slug"] is None
        assert body["target_squad_public_slug"] is None

    @staticmethod
    def _make_squad(db_client, world, db_session):
        """B 팀 스쿼드를 열고, 시험이 끝나면 지운다.

        🔴 **스쿼드 삭제 경로가 계약에 없다**(계약 3-7절 「아직 없는 것」).
        그리고 `squad.team_id` 는 **RESTRICT** 다 — 부록 D.6 이 팀 해체 시의
        처리를 안 정해서 일부러 그렇게 둔 것이라, 남겨 두면 픽스처가 팀을 못
        지운다. 그래서 여기서 직접 거둔다.
        """
        made = db_client.post(
            f"{V1}/teams/{world['team_b']}/squad",
            headers=world["b_owner"]["headers"],
        )
        assert made.status_code in (200, 201), made.text
        return made.json()["public_slug"]

    @staticmethod
    def _drop_squad(db_session, world):
        db_session.execute(
            text("delete from squad where team_id = :t"), {"t": world["team_b"]}
        )
        db_session.commit()

    def test_스쿼드를_만들면_그_슬러그가_실린다(self, db_client, world, db_session):
        slug = self._make_squad(db_client, world, db_session)
        try:
            body = self._create(db_client, world)
            assert body["target_squad_public_slug"] == slug
            # 상대만 생겼으므로 우리 쪽은 그대로 없다.
            assert body["requester_squad_public_slug"] is None
        finally:
            self._drop_squad(db_session, world)

    def test_그_슬러그로_판을_실제로_읽을_수_있다(self, db_client, world, db_session):
        """🔴 **소속이 아니어도 읽힌다**(SEC-005) — 그게 이 값을 싣는 이유다."""
        slug = self._make_squad(db_client, world, db_session)
        try:
            body = self._create(db_client, world)
            # A 팀 주장은 B 팀 소속이 아니다.
            read = db_client.get(f"{V1}/squads/{body['target_squad_public_slug']}")
            assert read.status_code == 200, read.text
            assert read.json()["public_slug"] == slug
        finally:
            self._drop_squad(db_session, world)
