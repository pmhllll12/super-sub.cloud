"""match/adapter/inbound/api/v1/match_preference_router.py — 계약 문서.
regions_router도 여기서 함께 본다(같은 기능 묶음, `paik` 18·19·20·21번).

스텁을 끼워 DB 없이 돈다. 실제 조인·외래키는 `test_match_preference_db.py`가 본다.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.security import issue_access_token
from app.match.adapter.outbound.stub.match_preference_stub_repository import (
    REGIONS_BY_ID,
    register_candidate_activity,
    register_candidate_card,
    register_candidate_grade,
    register_last_match,
    register_position,
    register_seated,
    register_squad,
    register_team,
    register_team_member,
    register_team_position,
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


def _set_member_position(client, user_id, position_id):
    register_position(position_id)
    res = client.put(
        f"{V1}/me/match-preferences",
        json={"region_ids": [], "slots": [], "position_ids": [str(position_id)]},
        headers=_headers(user_id),
    )
    assert res.status_code == 200, res.text


class TestSquadCandidates:
    """`GET /teams/{id}/squad/candidates` — 빈 자리 추천 후보 (미결 `paik` 27번)."""

    def test_소속이_아니면_403(self, client):
        team_id, owner, outsider = uuid4(), uuid4(), uuid4()
        register_team(team_id)
        register_team_member(team_id, owner, "owner", "주장")

        res = client.get(
            f"{V1}/teams/{team_id}/squad/candidates",
            params={"position_code": "GK"},
            headers=_headers(outsider),
        )
        assert res.status_code == 403, res.text

    def test_없는_포지션_코드는_422(self, client):
        team_id, owner = uuid4(), uuid4()
        register_team(team_id)
        register_team_member(team_id, owner, "owner", "주장")

        res = client.get(
            f"{V1}/teams/{team_id}/squad/candidates",
            params={"position_code": "없는자리"},
            headers=_headers(owner),
        )
        assert res.status_code == 422, res.text
        assert error_code(res) == "UNKNOWN_POSITION"

    def test_등급이_없어도_후보로_온다(self, client):
        team_id, owner, candidate = uuid4(), uuid4(), uuid4()
        position_id = uuid4()
        register_team(team_id)
        register_team_member(team_id, owner, "owner", "주장")
        register_team_position(team_id, "GK", position_id)
        _set_member_position(client, candidate, position_id)
        register_candidate_card(candidate, "candidate-slug")

        res = client.get(
            f"{V1}/teams/{team_id}/squad/candidates",
            params={"position_code": "GK"},
            headers=_headers(owner),
        )
        assert res.status_code == 200, res.text
        rows = res.json()
        assert len(rows) == 1
        assert rows[0]["user_id"] == str(candidate)
        assert rows[0]["grade"] is None
        assert rows[0]["provisional"] is None

    def test_자기_팀과_이미_앉은_사람은_제외된다(self, client):
        team_id, owner, teammate, seated = uuid4(), uuid4(), uuid4(), uuid4()
        position_id = uuid4()
        register_team(team_id)
        register_team_member(team_id, owner, "owner", "주장")
        register_team_position(team_id, "GK", position_id)
        _set_member_position(client, teammate, position_id)
        register_team_member(team_id, teammate, "member", "이미팀원")
        _set_member_position(client, seated, position_id)
        register_seated(team_id, seated)

        res = client.get(
            f"{V1}/teams/{team_id}/squad/candidates",
            params={"position_code": "GK"},
            headers=_headers(owner),
        )
        assert res.status_code == 200, res.text
        assert res.json() == []

    def test_등급을_직접_고르면_그_칸만_하드필터한다(self, client):
        team_id, owner = uuid4(), uuid4()
        cand_b, cand_c = uuid4(), uuid4()
        position_id = uuid4()
        register_team(team_id)
        register_team_member(team_id, owner, "owner", "주장")
        register_team_position(team_id, "GK", position_id)
        for uid, grade in ((cand_b, "B"), (cand_c, "C")):
            _set_member_position(client, uid, position_id)
            register_candidate_grade(uid, grade, provisional=False)

        res = client.get(
            f"{V1}/teams/{team_id}/squad/candidates",
            params={"position_code": "GK", "grade": "B"},
            headers=_headers(owner),
        )
        assert res.status_code == 200, res.text
        rows = res.json()
        assert [r["user_id"] for r in rows] == [str(cand_b)]
        assert rows[0]["grade"] == "B"
        assert rows[0]["provisional"] is False

    def test_등급_상관없음이면_거르지_않고_실력축_거리로_정렬한다(self, client):
        """팀 평균은 이미 앉은 사람(등급 B, 실력값 2)에서 낸다. 후보 A(거리 1,
        최근)·C(거리 1, 오래전)·D(거리 2)·등급 없음 순으로 와야 한다."""
        team_id, owner, seated = uuid4(), uuid4(), uuid4()
        cand_a, cand_c, cand_d, cand_none = uuid4(), uuid4(), uuid4(), uuid4()
        position_id = uuid4()
        register_team(team_id)
        register_team_member(team_id, owner, "owner", "주장")
        register_team_position(team_id, "GK", position_id)

        _set_member_position(client, seated, position_id)
        register_candidate_grade(seated, "B")
        register_seated(team_id, seated)

        now = datetime.now(timezone.utc)
        for uid, grade, active in (
            (cand_a, "A", now),
            (cand_c, "C", now - timedelta(days=30)),
            (cand_d, "D", now),
            (cand_none, None, now),
        ):
            _set_member_position(client, uid, position_id)
            if grade is not None:
                register_candidate_grade(uid, grade)
            register_candidate_activity(uid, active)

        res = client.get(
            f"{V1}/teams/{team_id}/squad/candidates",
            params={"position_code": "GK", "grade": "any"},
            headers=_headers(owner),
        )
        assert res.status_code == 200, res.text
        order = [r["user_id"] for r in res.json()]
        assert order == [str(cand_a), str(cand_c), str(cand_d), str(cand_none)]

    def test_거리_점수는_응답에_없다(self, client):
        team_id, owner, cand = uuid4(), uuid4(), uuid4()
        position_id = uuid4()
        register_team(team_id)
        register_team_member(team_id, owner, "owner", "주장")
        register_team_position(team_id, "GK", position_id)
        _set_member_position(client, cand, position_id)
        register_candidate_grade(cand, "A", provisional=True)

        res = client.get(
            f"{V1}/teams/{team_id}/squad/candidates",
            params={"position_code": "GK"},
            headers=_headers(owner),
        )
        assert res.status_code == 200, res.text
        assert set(res.json()[0]) == {
            "user_id", "nickname", "card_public_slug", "grade", "provisional",
        }
