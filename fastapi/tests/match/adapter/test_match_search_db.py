"""경기 탐색이 **실제 PostgreSQL 에서** 도는지 확인한다.

계약 테스트(`test_match_search_router.py`)는 스텁을 끼우므로 조인과 LIKE 이스케이프를
보지 못한다. 여기서 보는 것은 셋이다.

1. `match -> team` 조인으로 이름·지역·종목이 실제로 채워진다
2. **지역 부분 일치의 LIKE 메타문자가 리터럴로 처리된다** — `%` 한 글자로 전체가
   걸리면 안 된다
3. 다가오는 경기만, 이른 것부터

🔴 그리고 **`team`·`sport` 를 원시 쿼리로 읽는 자리**가 여기 걸린다. `team.name` 이나
`team.region` 의 이름이 바뀌면 파이썬이 잡아 주지 않으므로 이 검사가 유일한
방어선이다 — 지우지 말 것.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from tests.conftest import V1

pytestmark = pytest.mark.db

PASSWORD = "supersub2026"


def _at(days):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


@pytest.fixture
def owner(db_client):
    email = f"search-{uuid.uuid4().hex[:12]}@super-sub.example"
    signup = db_client.post(
        f"{V1}/auth/signup",
        json={"email": email, "password": PASSWORD, "nickname": "주장"},
    )
    assert signup.status_code == 201, signup.text
    login = db_client.post(
        f"{V1}/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert login.status_code == 200, login.text
    return {"headers": {"Authorization": f"Bearer {login.json()['access_token']}"}}


@pytest.fixture
def world(db_client, db_session, owner):
    """지역 이름에 **LIKE 메타문자를 일부러 넣은** 팀을 하나 섞는다."""
    tag = uuid.uuid4().hex[:8]
    plan = [
        ("football", f"강남FC-{tag}", f"서울 강남구 {tag}", "GK", 3),
        ("football", f"해운대FC-{tag}", f"부산 해운대구 {tag}", "FW", 1),
        ("baseball", f"잠실-{tag}", f"서울 송파구 {tag}", "P", 5),
        # 🔴 `%` 가 든 지역. 이스케이프가 안 되면 검색어 `%` 로 전체가 걸린다.
        ("football", f"메타FC-{tag}", f"100% 제주 {tag}", "MF", 2),
    ]
    made = {}
    for sport, name, region, position, days in plan:
        created = db_client.post(
            f"{V1}/teams",
            json={"name": name, "region": region, "sport_code": sport},
            headers=owner["headers"],
        )
        assert created.status_code == 201, created.text
        team_id = created.json()["id"]

        match = db_client.post(
            f"{V1}/teams/{team_id}/matches",
            json={
                "played_at": _at(days),
                "place": f"{name} 구장",
                "needs": [{"position_code": position, "head_count": 2}],
            },
            headers=owner["headers"],
        )
        assert match.status_code == 201, match.text
        made[name] = {"team_id": team_id, "match_id": match.json()["id"]}

    yield {"tag": tag, "teams": made}

    ids = [t["team_id"] for t in made.values()]
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
    db_session.commit()


def _search(db_client, owner, **params):
    return db_client.get(f"{V1}/matches", params=params, headers=owner["headers"])


class TestJoin:
    def test_팀_이름과_지역과_종목이_조인으로_채워진다(self, db_client, owner, world):
        """🔴 `team.name`·`team.region`·`team.sport_code` 를 원시 쿼리로 읽는 자리다."""
        tag = world["tag"]
        body = _search(db_client, owner, region=tag).json()
        assert body["total"] == 4

        item = next(i for i in body["items"] if i["team_name"].startswith("강남FC"))
        assert item["region"] == f"서울 강남구 {tag}"
        assert item["sport_code"] == "football"
        assert item["needs"][0]["position_code"] == "GK"
        assert item["needs"][0]["position_label"] == "골키퍼"

    def test_종목으로_좁힌다(self, db_client, owner, world):
        body = _search(db_client, owner, region=world["tag"], sport_code="baseball").json()
        assert body["total"] == 1
        assert body["items"][0]["team_name"].startswith("잠실")

    def test_없는_종목은_422_다(self, db_client, owner, world):
        """`sport` 를 원시 쿼리로 읽는 자리. 위 검사가 양성 대조다."""
        res = _search(db_client, owner, sport_code="curling")
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "UNKNOWN_SPORT"


class TestLikeEscaping:
    def test_퍼센트_한_글자로_전체가_걸리지_않는다(self, db_client, owner, world):
        """🔴 이스케이프가 없으면 `%` 가 패턴이 되어 **모든 경기**가 걸린다.

        `100% 제주` 라는 지역을 일부러 만들어 뒀으므로, 리터럴로 처리되면
        **그 한 건만** 걸려야 한다.
        """
        body = _search(db_client, owner, region="%").json()
        names = [i["team_name"] for i in body["items"]]
        assert all(n.startswith("메타FC") for n in names), names
        assert body["total"] == 1

    def test_언더바도_리터럴이다(self, db_client, owner, world):
        """`_` 는 LIKE 에서 한 글자를 뜻한다. 리터럴이면 아무것도 안 걸린다."""
        body = _search(db_client, owner, region="_").json()
        assert body["total"] == 0

    def test_퍼센트가_든_지역을_그대로_찾을_수_있다(self, db_client, owner, world):
        body = _search(db_client, owner, region="100%").json()
        assert body["total"] == 1
        assert body["items"][0]["team_name"].startswith("메타FC")


class TestUpcomingAndOrder:
    def test_이른_경기가_앞에_온다(self, db_client, owner, world):
        items = _search(db_client, owner, region=world["tag"]).json()["items"]
        played = [i["played_at"] for i in items]
        assert played == sorted(played)

    def test_지난_경기는_안_담긴다(self, db_client, db_session, owner, world):
        """등록 경로가 지난 시각을 막으므로 저장된 행을 뒤로 옮겨서 확인한다."""
        gone = world["teams"][f"해운대FC-{world['tag']}"]["match_id"]
        db_session.execute(
            text("update match set played_at = now() - interval '1 day' where id = :id"),
            {"id": uuid.UUID(gone)},
        )
        db_session.commit()

        ids = [i["id"] for i in _search(db_client, owner, region=world["tag"]).json()["items"]]
        assert gone not in ids


class TestPaging:
    def test_total_은_페이지와_무관하게_전체다(self, db_client, owner, world):
        body = _search(db_client, owner, region=world["tag"], page=1, size=2).json()
        assert body["total"] == 4
        assert len(body["items"]) == 2

    def test_넘긴_페이지는_빈_목록이되_total_은_그대로다(self, db_client, owner, world):
        body = _search(db_client, owner, region=world["tag"], page=9, size=2).json()
        assert body["items"] == []
        assert body["total"] == 4
