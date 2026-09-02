"""경기 등록을 **실제 PostgreSQL** 에 대고 확인한다.

스텁이 답할 수 없는 것들이다:

- 🔴 **`match` 저장소가 `user` 컨텍스트의 세 테이블을 원시 SQL 로 읽는다**
  (`team` · `team_member` · `position`). 저쪽 컬럼 이름이 바뀌면 파이썬이 못 잡는다 —
  **여기가 유일한 방어선이다.**
- 야구의 `C`(포수)와 농구의 `C`(센터)가 실제로 갈리는가 (`uq_position_sport_code`)
- 탈퇴한 사람의 역할이 사라지는가 (`left_at` 을 거르는지)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from tests.conftest import V1, error_code

pytestmark = pytest.mark.db

PASSWORD = "supersub2026"


def _future(days=7):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _account(db_client, nickname):
    email = f"match-{uuid.uuid4().hex[:12]}@super-sub.example"
    signup = db_client.post(
        f"{V1}/auth/signup",
        json={"email": email, "password": PASSWORD, "nickname": nickname},
    )
    assert signup.status_code == 201, signup.text
    login = db_client.post(
        f"{V1}/auth/login", json={"email": email, "password": PASSWORD}
    )
    return {
        "email": email,
        "id": uuid.UUID(signup.json()["id"]),
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


@pytest.fixture
def world(db_client, db_session):
    """축구 팀·야구 팀·농구 팀 각 1개와 주장 1명, 일반 구성원 1명."""
    owner = _account(db_client, "주장")
    member = _account(db_client, "구성원")

    teams = {}
    for sport in ("football", "baseball", "basketball"):
        res = db_client.post(
            f"{V1}/teams",
            json={"name": f"{sport}팀", "region": "서울", "sport_code": sport},
            headers=owner["headers"],
        )
        assert res.status_code == 201, res.text
        teams[sport] = res.json()["id"]

    res = db_client.post(
        f"{V1}/teams/{teams['football']}/members",
        json={},
        headers=member["headers"],
    )
    assert res.status_code == 201, res.text

    yield {"owner": owner, "member": member, "teams": teams}

    ids = list(teams.values())
    db_session.execute(
        text(
            "delete from match_position_need where match_id in "
            "(select id from match where team_id = any(:t))"
        ),
        {"t": ids},
    )
    db_session.execute(text("delete from match where team_id = any(:t)"), {"t": ids})
    db_session.execute(
        text("delete from team_member where team_id = any(:t)"), {"t": ids}
    )
    db_session.execute(text("delete from team where id = any(:t)"), {"t": ids})
    db_session.execute(
        text('delete from "user" where email = any(:e)'),
        {"e": [owner["email"], member["email"]]},
    )
    db_session.commit()


def _create(db_client, world, sport, needs, headers=None):
    return db_client.post(
        f"{V1}/teams/{world['teams'][sport]}/matches",
        json={
            "played_at": _future(),
            "place": "강남 운동장",
            "needs": needs,
        },
        headers=headers or world["owner"]["headers"],
    )


class TestCreateMatchInDb:
    def test_경기와_필요_포지션_행이_남는다(self, db_client, db_session, world):
        res = _create(
            db_client,
            world,
            "football",
            [{"position_code": "GK", "head_count": 1},
             {"position_code": "FW", "head_count": 2}],
        )
        assert res.status_code == 201, res.text
        match_id = res.json()["id"]

        row = db_session.execute(
            text("select team_id, place from match where id = :m"), {"m": match_id}
        ).one()
        assert str(row.team_id) == world["teams"]["football"]

        needs = db_session.execute(
            text(
                "select p.code, n.head_count from match_position_need n "
                "join position p on p.id = n.position_id "
                "where n.match_id = :m order by p.code"
            ),
            {"m": match_id},
        ).all()
        assert [(r.code, r.head_count) for r in needs] == [("FW", 2), ("GK", 1)]

    def test_야구_C_와_농구_C_는_다른_포지션이다(self, db_client, db_session, world):
        """🔴 `position` 이 대리키를 쓰는 이유가 이것이다(부록 D.7)."""
        baseball = _create(
            db_client, world, "baseball", [{"position_code": "C", "head_count": 1}]
        )
        basketball = _create(
            db_client, world, "basketball", [{"position_code": "C", "head_count": 1}]
        )
        assert (baseball.status_code, basketball.status_code) == (201, 201)
        assert baseball.json()["needs"][0]["position_label"] == "포수"
        assert basketball.json()["needs"][0]["position_label"] == "센터"

        rows = db_session.execute(
            text(
                "select distinct n.position_id from match_position_need n "
                "where n.match_id = any(:m)"
            ),
            {"m": [baseball.json()["id"], basketball.json()["id"]]},
        ).all()
        assert len(rows) == 2, "같은 포지션 행을 가리키고 있다"

    def test_다른_종목의_포지션은_422(self, db_client, world):
        """축구 팀에 야구 포지션. `position` 을 팀 종목으로 좁혀 찾는지 본다."""
        res = _create(
            db_client, world, "football", [{"position_code": "P", "head_count": 1}]
        )
        assert res.status_code == 422
        assert error_code(res) == "UNKNOWN_POSITION"

    def test_일반_구성원은_403(self, db_client, world):
        res = _create(
            db_client,
            world,
            "football",
            [{"position_code": "GK", "head_count": 1}],
            headers=world["member"]["headers"],
        )
        assert res.status_code == 403
        assert error_code(res) == "FORBIDDEN"

    def test_탈퇴하면_등록_권한도_사라진다(self, db_client, db_session, world):
        """`team_member` 는 소프트 삭제라 행이 남는다. `left_at` 을 안 거르면 통과한다."""
        team_id = world["teams"]["football"]
        db_session.execute(
            text(
                "update team_member set left_at = now() "
                "where team_id = :t and user_id = :u"
            ),
            {"t": team_id, "u": str(world["owner"]["id"])},
        )
        db_session.commit()

        res = _create(
            db_client, world, "football", [{"position_code": "GK", "head_count": 1}]
        )
        assert res.status_code == 403, res.text


class TestReadMatchFromDb:
    def test_포지션_이름이_position_테이블에서_온다(self, db_client, world):
        created = _create(
            db_client, world, "football", [{"position_code": "MF", "head_count": 3}]
        ).json()

        res = db_client.get(
            f"{V1}/matches/{created['id']}", headers=world["member"]["headers"]
        )
        assert res.status_code == 200, res.text
        assert res.json()["needs"] == [
            {"position_code": "MF", "position_label": "미드필더", "head_count": 3}
        ]


class TestListTeamMatchesFromDb:
    def test_지난_경기는_목록에서_빠진다(self, db_client, db_session, world):
        """🔴 등록은 미래만 되지만 **그 뒤로 시간이 흐른다.**

        `find_match` 로는 여전히 읽힌다 — 기록이 사라지는 것이 아니라 모집 목록에서
        빠질 뿐이다.
        """
        upcoming = _create(
            db_client, world, "football", [{"position_code": "GK", "head_count": 1}]
        ).json()
        past = _create(
            db_client, world, "football", [{"position_code": "FW", "head_count": 2}]
        ).json()
        db_session.execute(
            text("update match set played_at = now() - interval '1 day' where id = :m"),
            {"m": past["id"]},
        )
        db_session.commit()

        res = db_client.get(
            f"{V1}/teams/{world['teams']['football']}/matches",
            headers=world["member"]["headers"],
        )
        assert res.status_code == 200, res.text
        assert [m["id"] for m in res.json()] == [upcoming["id"]]

        # 지난 경기도 id 로는 읽힌다
        assert (
            db_client.get(
                f"{V1}/matches/{past['id']}", headers=world["member"]["headers"]
            ).status_code
            == 200
        )

    def test_다른_팀_경기는_섞이지_않는다(self, db_client, world):
        _create(db_client, world, "football", [{"position_code": "GK", "head_count": 1}])
        _create(db_client, world, "baseball", [{"position_code": "P", "head_count": 1}])

        res = db_client.get(
            f"{V1}/teams/{world['teams']['baseball']}/matches",
            headers=world["owner"]["headers"],
        )
        assert len(res.json()) == 1
        assert res.json()[0]["needs"][0]["position_label"] == "투수"

    def test_필요_포지션을_한_번에_읽는다(self, db_client, world):
        """N+1 을 막는 경로다. 결과가 경기마다 제대로 갈리는지 본다."""
        for needs in (
            [{"position_code": "GK", "head_count": 1}],
            [
                {"position_code": "FW", "head_count": 2},
                {"position_code": "MF", "head_count": 3},
            ],
        ):
            assert (
                _create(db_client, world, "football", needs).status_code == 201
            )

        body = db_client.get(
            f"{V1}/teams/{world['teams']['football']}/matches",
            headers=world["owner"]["headers"],
        ).json()
        assert sorted(len(m["needs"]) for m in body) == [1, 2]
