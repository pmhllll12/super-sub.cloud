"""match/adapter/inbound/api/v1/match_preference_router.py — 계약 문서.
regions_router도 여기서 함께 본다(같은 기능 묶음, `paik` 18·19·20·21번).

스텁을 끼워 DB 없이 돈다. 실제 조인·외래키는 `test_match_preference_db.py`가 본다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.core.security import issue_access_token
from app.match.adapter.outbound.stub.match_preference_stub_repository import (
    REGIONS_BY_ID,
    register_last_match,
    register_squad,
    register_team,
    register_team_member,
    reset_match_preferences,
)
from tests.conftest import V1, error_code


def _headers(user_id):
    return {"Authorization": f"Bearer {issue_access_token(user_id)}"}


def _some_region_id():
    return next(iter(REGIONS_BY_ID))


@pytest.fixture(autouse=True)
def _clean():
    reset_match_preferences()
    yield
    reset_match_preferences()


class TestRegions:
    def test_로그인하면_목록을_본다(self, client):
        user_id = uuid4()
        res = client.get(f"{V1}/regions", headers=_headers(user_id))
        assert res.status_code == 200, res.text
        assert len(res.json()) > 0
        assert {"id", "city", "district", "label"} <= set(res.json()[0])

    def test_로그인_안_하면_401(self, client):
        assert client.get(f"{V1}/regions").status_code == 401


class TestTeamPreference:
    def test_팀장이_아니면_403(self, client):
        team_id, owner, other = uuid4(), uuid4(), uuid4()
        register_team(team_id)
        register_team_member(team_id, owner, "owner", "주장")
        register_team_member(team_id, other, "member", "남")

        res = client.put(
            f"{V1}/teams/{team_id}/match-preferences",
            json={"region_ids": [], "slots": []},
            headers=_headers(other),
        )
        assert res.status_code == 403, res.text
        assert error_code(res) == "FORBIDDEN"

    def test_없는_팀은_404(self, client):
        res = client.put(
            f"{V1}/teams/{uuid4()}/match-preferences",
            json={"region_ids": [], "slots": []},
            headers=_headers(uuid4()),
        )
        assert res.status_code == 404, res.text
        assert error_code(res) == "TEAM_NOT_FOUND"

    def test_시작이_끝보다_뒤면_422(self, client):
        team_id, owner = uuid4(), uuid4()
        register_team(team_id)
        register_team_member(team_id, owner, "owner", "주장")

        res = client.put(
            f"{V1}/teams/{team_id}/match-preferences",
            json={
                "region_ids": [],
                "slots": [{"weekday": 0, "start_time": "12:00:00", "end_time": "10:00:00"}],
            },
            headers=_headers(owner),
        )
        assert res.status_code == 422, res.text
        assert error_code(res) == "INVALID_TIME_SLOT"

    def test_요일이_범위_밖이면_422(self, client):
        team_id, owner = uuid4(), uuid4()
        register_team(team_id)
        register_team_member(team_id, owner, "owner", "주장")

        res = client.put(
            f"{V1}/teams/{team_id}/match-preferences",
            json={
                "region_ids": [],
                "slots": [{"weekday": 7, "start_time": "10:00:00", "end_time": "12:00:00"}],
            },
            headers=_headers(owner),
        )
        assert res.status_code == 422

    def test_없는_지역이면_422(self, client):
        team_id, owner = uuid4(), uuid4()
        register_team(team_id)
        register_team_member(team_id, owner, "owner", "주장")

        res = client.put(
            f"{V1}/teams/{team_id}/match-preferences",
            json={"region_ids": [str(uuid4())], "slots": []},
            headers=_headers(owner),
        )
        assert res.status_code == 422, res.text
        assert error_code(res) == "UNKNOWN_REGION"

    def test_팀장이면_저장하고_읽는다(self, client):
        team_id, owner = uuid4(), uuid4()
        register_team(team_id)
        register_team_member(team_id, owner, "owner", "주장")
        region_id = _some_region_id()

        put_res = client.put(
            f"{V1}/teams/{team_id}/match-preferences",
            json={
                "region_ids": [str(region_id)],
                "slots": [{"weekday": 5, "start_time": "10:00:00", "end_time": "12:00:00"}],
            },
            headers=_headers(owner),
        )
        assert put_res.status_code == 200, put_res.text

        get_res = client.get(
            f"{V1}/teams/{team_id}/match-preferences", headers=_headers(owner)
        )
        assert get_res.json()["region_ids"] == [str(region_id)]


class TestMemberPreference:
    def test_기본은_빈_조건이다(self, client):
        res = client.get(f"{V1}/me/match-preferences", headers=_headers(uuid4()))
        assert res.status_code == 200
        body = res.json()
        assert body["region_ids"] == []
        assert body["slots"] == []
        assert body["position_ids"] == []

    def test_시간_검증은_개인_조건에도_적용된다(self, client):
        res = client.put(
            f"{V1}/me/match-preferences",
            json={
                "region_ids": [],
                "slots": [{"weekday": 0, "start_time": "12:00:00", "end_time": "10:00:00"}],
                "position_ids": [],
            },
            headers=_headers(uuid4()),
        )
        assert res.status_code == 422
        assert error_code(res) == "INVALID_TIME_SLOT"

    def test_없는_포지션이면_422(self, client):
        res = client.put(
            f"{V1}/me/match-preferences",
            json={"region_ids": [], "slots": [], "position_ids": [str(uuid4())]},
            headers=_headers(uuid4()),
        )
        assert res.status_code == 422
        assert error_code(res) == "UNKNOWN_POSITION"


class TestListMemberPreferences:
    def test_팀장이_아니면_403(self, client):
        team_id, owner, other = uuid4(), uuid4(), uuid4()
        register_team(team_id)
        register_team_member(team_id, owner, "owner", "주장")
        register_team_member(team_id, other, "member", "남")

        res = client.get(
            f"{V1}/teams/{team_id}/members/match-preferences", headers=_headers(other)
        )
        assert res.status_code == 403, res.text

    def test_팀장은_팀원_목록을_본다(self, client):
        team_id, owner, member = uuid4(), uuid4(), uuid4()
        register_team(team_id)
        register_team_member(team_id, owner, "owner", "주장")
        register_team_member(team_id, member, "member", "구성원")

        res = client.get(
            f"{V1}/teams/{team_id}/members/match-preferences", headers=_headers(owner)
        )
        assert res.status_code == 200, res.text
        nicknames = {row["nickname"] for row in res.json()}
        assert nicknames == {"주장", "구성원"}


class TestMatchCandidates:
    def test_소속이_아니면_403(self, client):
        team_id, owner, outsider = uuid4(), uuid4(), uuid4()
        register_team(team_id)
        register_team_member(team_id, owner, "owner", "주장")

        res = client.get(
            f"{V1}/teams/{team_id}/match-candidates", headers=_headers(outsider)
        )
        assert res.status_code == 403, res.text

    def test_스쿼드가_없으면_빈_목록(self, client):
        team_id, owner = uuid4(), uuid4()
        register_team(team_id)
        register_team_member(team_id, owner, "owner", "주장")

        res = client.get(
            f"{V1}/teams/{team_id}/match-candidates", headers=_headers(owner)
        )
        assert res.status_code == 200
        assert res.json() == []

    def test_판_크기가_같고_로스터가_찬_후보만_사실값_근거로_온다(self, client):
        team_a, owner_a = uuid4(), uuid4()
        team_b, owner_b = uuid4(), uuid4()
        register_team(team_a, "우리팀", "서울 강남구")
        register_team(team_b, "상대팀", "서울 강남구")
        register_team_member(team_a, owner_a, "owner", "주장A")
        register_team_member(team_b, owner_b, "owner", "주장B")
        register_squad(team_a, "5:5", 5)
        register_squad(team_b, "5:5", 5)
        region_id = _some_region_id()
        register_last_match(team_b, datetime.now(timezone.utc))

        client.put(
            f"{V1}/teams/{team_a}/match-preferences",
            json={
                "region_ids": [str(region_id)],
                "slots": [{"weekday": 5, "start_time": "10:00:00", "end_time": "12:00:00"}],
            },
            headers=_headers(owner_a),
        )
        client.put(
            f"{V1}/teams/{team_b}/match-preferences",
            json={
                "region_ids": [str(region_id)],
                "slots": [{"weekday": 5, "start_time": "11:00:00", "end_time": "13:00:00"}],
            },
            headers=_headers(owner_b),
        )

        res = client.get(
            f"{V1}/teams/{team_a}/match-candidates", headers=_headers(owner_a)
        )
        assert res.status_code == 200, res.text
        rows = res.json()
        assert len(rows) == 1
        row = rows[0]
        assert row["team_id"] == str(team_b)
        assert row["formation"] == "5:5"
        kinds = {r["kind"] for r in row["reasons"]}
        assert kinds == {"time", "region"}
        assert "score" not in row
