"""팀을 **실제 PostgreSQL** 에 대고 확인한다.

스텁이 답할 수 없는 것들이다:

- 🔴 **탈퇴가 행을 지우지 않고 `left_at` 을 채우는가** (부록 D.6 — 경기·평가 이력이
  이 행을 참조하므로 삭제 연쇄에 넣지 않는다)
- 재가입이 **새 행**으로 남아 이력이 보존되는가 (유일 제약이 `joined_at` 을 묶는다)
- 나간 팀이 `GET /me` 의 `teams` 에서 빠지는가 (도메인 규칙과 저장소의 연결)
- `sport` 테이블에 없는 종목이 실제로 걸리는가 (외래키가 없어 앱이 막는다)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from tests.conftest import V1, error_code

pytestmark = pytest.mark.db

PASSWORD = "supersub2026"
TEAM = {"name": "번개FC", "region": "서울 강남", "sport_code": "football"}


def _account(db_client, nickname):
    nickname = f"{nickname}{uuid.uuid4().hex[:6]}"
    email = f"team-{uuid.uuid4().hex[:12]}@super-sub.example"
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
        "email": email,
        "id": uuid.UUID(signup.json()["id"]),
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


@pytest.fixture
def people(db_client, db_session):
    """주장 하나와 구성원 하나. 끝나면 팀·소속·계정을 전부 지운다."""
    owner = _account(db_client, "주장")
    member = _account(db_client, "구성원")

    yield {"owner": owner, "member": member}

    ids = [str(owner["id"]), str(member["id"])]
    db_session.execute(
        text("delete from team_member where user_id = any(:u)"), {"u": ids}
    )
    # 🔴 경기가 팀을 참조하므로 팀보다 **먼저** 지운다(외래키 방향의 역순).
    # 팀 정보 수정 검사(`TestUpdateTeamInDb`)가 경기 탐색까지 보느라 경기를
    # 만든다 — 안 지우면 아래 팀 삭제가 `match_team_id_fkey` 로 막힌다.
    orphan_teams = (
        "select id from team where id not in (select team_id from team_member) "
        "and name = :n"
    )
    db_session.execute(
        text(
            "delete from match_position_need where match_id in "
            f"(select id from match where team_id in ({orphan_teams}))"
        ),
        {"n": TEAM["name"]},
    )
    db_session.execute(
        text(f"delete from match where team_id in ({orphan_teams})"),
        {"n": TEAM["name"]},
    )
    db_session.execute(
        text(
            "delete from team where id not in (select team_id from team_member) "
            "and name = :n"
        ),
        {"n": TEAM["name"]},
    )
    db_session.execute(
        text('delete from "user" where email = any(:e)'),
        {"e": [owner["email"], member["email"]]},
    )
    db_session.commit()


def _create(db_client, people):
    res = db_client.post(f"{V1}/teams", json=TEAM, headers=people["owner"]["headers"])
    assert res.status_code == 201, res.text
    return res.json()


def _rows(db_session, team_id, user_id):
    return db_session.execute(
        text(
            "select role, left_at from team_member "
            "where team_id = :t and user_id = :u order by joined_at"
        ),
        {"t": team_id, "u": str(user_id)},
    ).all()


class TestCreateTeamInDb:
    def test_팀과_주장_소속이_함께_남는다(self, db_client, db_session, people):
        team = _create(db_client, people)

        row = db_session.execute(
            text("select name, region, sport_code from team where id = :t"),
            {"t": team["id"]},
        ).one()
        assert (row.name, row.region, row.sport_code) == (
            TEAM["name"],
            TEAM["region"],
            TEAM["sport_code"],
        )

        rows = _rows(db_session, team["id"], people["owner"]["id"])
        assert [(r.role, r.left_at) for r in rows] == [("owner", None)]

    def test_등록되지_않은_종목은_422(self, db_client, people):
        """`sport` 테이블을 실제로 조회한다 — 외래키가 없어 DB 는 안 막는다."""
        res = db_client.post(
            f"{V1}/teams",
            json={**TEAM, "sport_code": "quidditch"},
            headers=people["owner"]["headers"],
        )
        assert res.status_code == 422
        assert error_code(res) == "UNKNOWN_SPORT"

    def test_지금_받는_종목은_통과한다(self, db_client, people):
        """`ho` 39번으로 축구만 `active` 다 — 세 종목 다 통과하던 검사를 바꿨다."""
        res = db_client.post(
            f"{V1}/teams",
            json={**TEAM, "sport_code": "football"},
            headers=people["owner"]["headers"],
        )
        assert res.status_code == 201, res.text

    def test_내려간_종목은_행은_있지만_새로_못_만든다(
        self, db_client, db_session, people
    ):
        """🔴 「없는 종목」과 다르다 — 행은 그대로 있어야 한다(`ho` 39번).

        이미 그 종목으로 올라간 데이터(2026-09-16 실측 `video` 야구 165건)가
        참조하고 있어 지울 수 없다. 그래서 `UNKNOWN_SPORT`(없다)가 아니라
        `SPORT_NOT_AVAILABLE`(지금 안 받는다)로 가른다.
        """
        for code in ("baseball", "basketball"):
            still_there = db_session.execute(
                text("select active from sport where code = :c"), {"c": code}
            ).scalar_one()
            assert still_there is False, f"{code} 행이 사라졌다"

            res = db_client.post(
                f"{V1}/teams",
                json={**TEAM, "sport_code": code},
                headers=people["owner"]["headers"],
            )
            assert res.status_code == 422, f"{code}: {res.text}"
            assert error_code(res) == "SPORT_NOT_AVAILABLE"


class TestMembershipInDb:
    def test_가입하면_member_행이_는다(self, db_client, db_session, people):
        team = _create(db_client, people)
        res = db_client.post(
            f"{V1}/teams/{team['id']}/members",
            json={},
            headers=people["member"]["headers"],
        )
        assert res.status_code == 201, res.text

        rows = _rows(db_session, team["id"], people["member"]["id"])
        assert [(r.role, r.left_at) for r in rows] == [("member", None)]

    def test_탈퇴해도_행이_남고_left_at_이_찬다(self, db_client, db_session, people):
        """🔴 부록 D.6 — 경기·평가 이력이 이 행을 참조한다. 지우면 이력이 끊긴다."""
        team = _create(db_client, people)
        db_client.post(
            f"{V1}/teams/{team['id']}/members",
            json={},
            headers=people["member"]["headers"],
        )
        res = db_client.delete(
            f"{V1}/teams/{team['id']}/members/{people['member']['id']}",
            headers=people["member"]["headers"],
        )
        assert res.status_code == 204

        rows = _rows(db_session, team["id"], people["member"]["id"])
        assert len(rows) == 1, "행이 지워졌다 — 소프트 삭제여야 한다"
        assert rows[0].left_at is not None

    def test_재가입하면_새_행이고_이력이_남는다(self, db_client, db_session, people):
        team = _create(db_client, people)
        headers = people["member"]["headers"]
        db_client.post(f"{V1}/teams/{team['id']}/members", json={}, headers=headers)
        db_client.delete(
            f"{V1}/teams/{team['id']}/members/{people['member']['id']}",
            headers=headers,
        )
        again = db_client.post(
            f"{V1}/teams/{team['id']}/members", json={}, headers=headers
        )
        assert again.status_code == 201, again.text

        rows = _rows(db_session, team["id"], people["member"]["id"])
        assert len(rows) == 2, "재가입이 새 행이어야 이력이 남는다"
        assert rows[0].left_at is not None and rows[1].left_at is None

    def test_나간_팀은_내_정보에_안_나온다(self, db_client, people):
        """`membership_rules.active_memberships` 가 실제 데이터에서도 도는지 본다."""
        team = _create(db_client, people)
        headers = people["member"]["headers"]
        db_client.post(f"{V1}/teams/{team['id']}/members", json={}, headers=headers)

        joined = db_client.get(f"{V1}/me", headers=headers).json()["teams"]
        assert [t["team_id"] for t in joined] == [team["id"]]

        db_client.delete(
            f"{V1}/teams/{team['id']}/members/{people['member']['id']}",
            headers=headers,
        )
        assert db_client.get(f"{V1}/me", headers=headers).json()["teams"] == []


class TestMemberCardReference:
    """구성원 목록이 **실제 `player_card` 를 조인해서** 카드를 가리키는가.

    스텁은 딕셔너리로 흉내 내므로 조인이 맞는지 못 본다. 여기가 방어선이다 —
    🔴 `player_card` 는 `card` 컨텍스트라 원시 쿼리로 읽는다. **저쪽 컬럼
    이름이 바뀌면 파이썬이 안 잡아 준다.**
    """

    def test_카드를_만들면_구성원_목록에_실린다(self, db_client, db_session, people):
        owner = people["owner"]
        team = _create(db_client, people)
        url = f"{V1}/teams/{team['id']}"

        # 카드가 없는 동안은 둘 다 null 이어야 한다.
        before = db_client.get(url, headers=owner["headers"]).json()["members"][0]
        assert before["player_card_id"] is None
        assert before["card_public_slug"] is None

        created = db_client.post(f"{V1}/me/card", headers=owner["headers"])
        assert created.status_code in (200, 201), created.text
        slug = created.json()["public_slug"]

        after = db_client.get(url, headers=owner["headers"]).json()["members"][0]
        assert after["card_public_slug"] == slug
        assert after["player_card_id"] is not None

        # 🔴 등재에 쓸 값이 실제 `player_card.id` 와 같아야 한다 — 다르면
        #    스쿼드 등재가 외래키에서 거부된다.
        real_id = db_session.execute(
            text("select id from player_card where user_id = :u"),
            {"u": owner["id"]},
        ).scalar_one()
        assert after["player_card_id"] == str(real_id)

    def test_카드가_없는_구성원도_목록에_남는다(self, db_client, db_session, people):
        """🔴 안쪽 조인이면 여기서 사라진다. 팀에는 여전히 있는 사람이다."""
        owner, member = people["owner"], people["member"]
        team = _create(db_client, people)
        db_client.post(
            f"{V1}/teams/{team['id']}/members",
            json={"user_id": str(member["id"])},
            headers=owner["headers"],
        )
        db_client.post(f"{V1}/me/card", headers=owner["headers"])

        members = db_client.get(
            f"{V1}/teams/{team['id']}", headers=owner["headers"]
        ).json()["members"]
        by_user = {m["user_id"]: m for m in members}

        assert len(by_user) == 2, "카드 없는 구성원이 조인에서 빠졌다"
        assert by_user[str(owner["id"])]["player_card_id"] is not None
        assert by_user[str(member["id"])]["player_card_id"] is None



class TestUpdateTeamInDb:
    """`PATCH /teams/{id}` 를 **실제 PostgreSQL** 에 대고 확인한다 (2026-09-16).

    스텁이 답할 수 없는 것: 행이 실제로 바뀌는가, 그리고 🔴 **바뀐 지역이
    경기 탐색(`GET /matches?region=`)에 곧바로 반영되는가** — 그 검색이
    `team.region` 을 조인해 거르기 때문에 이 경로를 낸 이유가 거기 있다.
    """

    def test_지역이_실제로_바뀐다(self, db_client, db_session, people):
        team = _create(db_client, people)
        res = db_client.patch(
            f"{V1}/teams/{team['id']}",
            json={"region": "부산 해운대구"},
            headers=people["owner"]["headers"],
        )
        assert res.status_code == 200, res.text

        row = db_session.execute(
            text("select name, region from team where id = :i"), {"i": team["id"]}
        ).one()
        assert row.region == "부산 해운대구"
        assert row.name == TEAM["name"]

    def test_바꾼_지역으로_경기_탐색에_걸린다(self, db_client, people):
        """이 경로를 낸 이유 — 지역이 틀리면 그 팀 경기가 검색에서 통째로 빠진다."""
        team = _create(db_client, people)
        tag = uuid.uuid4().hex[:8]
        db_client.patch(
            f"{V1}/teams/{team['id']}",
            json={"region": f"부산 해운대구 {tag}"},
            headers=people["owner"]["headers"],
        )

        made = db_client.post(
            f"{V1}/teams/{team['id']}/matches",
            json={
                "played_at": (
                    datetime.now(timezone.utc) + timedelta(days=5)
                ).isoformat(),
                "place": "해운대 구장",
                "needs": [{"position_code": "GK", "head_count": 1}],
            },
            headers=people["owner"]["headers"],
        )
        assert made.status_code == 201, made.text

        found = db_client.get(
            f"{V1}/matches",
            params={"region": tag},
            headers=people["owner"]["headers"],
        )
        assert found.status_code == 200, found.text
        assert [i["team_name"] for i in found.json()["items"]] == [TEAM["name"]]

    def test_주장이_아니면_행이_안_바뀐다(self, db_client, db_session, people):
        team = _create(db_client, people)
        db_client.post(
            f"{V1}/teams/{team['id']}/members",
            json={},
            headers=people["member"]["headers"],
        )

        res = db_client.patch(
            f"{V1}/teams/{team['id']}",
            json={"region": "대구"},
            headers=people["member"]["headers"],
        )
        assert res.status_code == 403

        region = db_session.execute(
            text("select region from team where id = :i"), {"i": team["id"]}
        ).scalar_one()
        assert region == TEAM["region"]
