"""`GET /matches` — 경기 탐색. 계약 문서 3-4절.

스텁을 끼워 DB 없이 돈다. 실제 조인·부분 일치는 `test_match_search_db.py` 가 본다.

**이 경로가 없으면 용병은 지원할 경기를 찾을 수 없다** — 다른 목록은 전부 팀 id 를
알아야 한다. 그래서 검사가 보는 것은 "찾아지는가"와 "못 찾을 것이 안 나오는가"다.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.security import issue_access_token
from app.match.adapter.outbound.stub.match_stub_repository import (
    register_role,
    register_team,
    reset_matches,
)
from tests.conftest import V1, error_code


def _headers(user_id):
    return {"Authorization": f"Bearer {issue_access_token(user_id)}"}


def _at(days):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


@pytest.fixture(autouse=True)
def _clean():
    reset_matches()
    yield
    reset_matches()


@pytest.fixture
def world(client):
    """축구 팀 둘(서울·부산), 야구 팀 하나(서울). 각각 경기 하나씩."""
    made = {}
    plan = [
        ("football", "강남FC", "서울 강남구", "GK", 3),
        ("football", "해운대FC", "부산 해운대구", "FW", 1),
        ("baseball", "잠실베어스", "서울 송파구", "P", 5),
    ]
    for sport, name, region, position, days in plan:
        team_id, owner = uuid4(), uuid4()
        register_team(team_id, sport, name=name, region=region)
        register_role(team_id, owner, "owner")

        res = client.post(
            f"{V1}/teams/{team_id}/matches",
            json={
                "played_at": _at(days),
                "place": f"{name} 구장",
                "needs": [{"position_code": position, "head_count": 2}],
            },
            headers=_headers(owner),
        )
        assert res.status_code == 201, res.text
        made[name] = {"team_id": team_id, "owner": owner, "match": res.json()}
    return made


def _search(client, user_id=None, **params):
    return client.get(
        f"{V1}/matches", params=params, headers=_headers(user_id or uuid4())
    )


class TestAuth:
    def test_인증이_필요하다(self, client, world):
        assert client.get(f"{V1}/matches").status_code == 401


class TestSearch:
    def test_남의_팀_경기도_찾을_수_있다(self, client, world):
        """🔴 요점이다. 이 사람은 어느 팀에도 속해 있지 않다."""
        res = _search(client)
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["total"] == 3
        assert len(body["items"]) == 3

    def test_팀_이름과_지역과_종목이_함께_온다(self, client, world):
        """없으면 화면이 팀을 한 건씩 다시 물어야 한다."""
        item = next(
            i for i in _search(client).json()["items"] if i["team_name"] == "강남FC"
        )
        assert item["region"] == "서울 강남구"
        assert item["sport_code"] == "football"
        assert item["needs"][0]["position_code"] == "GK"
        assert item["needs"][0]["position_label"] == "골키퍼"

    def test_이른_경기가_앞에_온다(self, client, world):
        """목록은 모집 글이고 임박한 것이 급하다."""
        names = [i["team_name"] for i in _search(client).json()["items"]]
        assert names == ["해운대FC", "강남FC", "잠실베어스"]

    def test_종목으로_좁힌다(self, client, world):
        body = _search(client, sport_code="baseball").json()
        assert body["total"] == 1
        assert body["items"][0]["team_name"] == "잠실베어스"

    def test_지역은_부분_일치다(self, client, world):
        """"서울"로 찾으면 "서울 강남구"·"서울 송파구"가 둘 다 걸려야 한다."""
        body = _search(client, region="서울").json()
        assert body["total"] == 2
        assert {i["team_name"] for i in body["items"]} == {"강남FC", "잠실베어스"}

    def test_종목과_지역을_함께_쓴다(self, client, world):
        body = _search(client, sport_code="football", region="서울").json()
        assert body["total"] == 1
        assert body["items"][0]["team_name"] == "강남FC"

    def test_없는_종목은_빈_배열이_아니라_422_다(self, client, world):
        """🔴 오타와 "그 종목 경기가 없다"가 같아 보이면 안 된다."""
        res = _search(client, sport_code="curling")
        assert res.status_code == 422
        assert error_code(res) == "UNKNOWN_SPORT"

    def test_안_걸리는_지역은_빈_목록이다(self, client, world):
        """지역은 자유 문자열이라 검증할 대상이 없다 — 종목과 다르다."""
        body = _search(client, region="제주").json()
        assert body == {"items": [], "total": 0, "page": 1, "size": 20}


class TestUpcomingOnly:
    def test_지난_경기는_담기지_않는다(self, client, world):
        """등록은 지난 시각을 막지만(PAST_MATCH), 시간이 지나면 지난 경기가 된다."""
        past_team, past_owner = uuid4(), uuid4()
        register_team(past_team, "football", name="지난FC", region="서울")
        register_role(past_team, past_owner, "owner")

        # 등록 경로는 지난 시각을 거부하므로 저장소에 직접 넣는다.
        from app.match.adapter.outbound.stub.match_stub_repository import _MATCHES
        from app.match.domain.entities.match_entity import MatchEntity

        gone = MatchEntity(
            id=uuid4(),
            team_id=past_team,
            played_at=datetime.now(timezone.utc) - timedelta(days=1),
            place="지난 구장",
            needs=[],
        )
        _MATCHES[gone.id] = gone

        names = [i["team_name"] for i in _search(client).json()["items"]]
        assert "지난FC" not in names


class TestPaging:
    def test_페이지_형식이_admin_과_같다(self, client, world):
        body = _search(client, page=1, size=2).json()
        assert set(body) == {"items", "total", "page", "size"}
        assert body["total"] == 3
        assert body["page"] == 1 and body["size"] == 2
        assert len(body["items"]) == 2

    def test_다음_페이지에_나머지가_온다(self, client, world):
        first = _search(client, page=1, size=2).json()["items"]
        second = _search(client, page=2, size=2).json()["items"]
        assert len(second) == 1
        assert {i["id"] for i in first}.isdisjoint({i["id"] for i in second})

    def test_넘긴_페이지는_빈_목록이되_total_은_그대로다(self, client, world):
        body = _search(client, page=9, size=2).json()
        assert body["items"] == []
        assert body["total"] == 3

    def test_size_상한이_있다(self, client, world):
        assert _search(client, size=101).status_code == 422
        assert _search(client, page=0).status_code == 422
