"""경기 조건·후보(`paik` 18·19·20·21번)를 실제 PostgreSQL에 대고 확인한다.

스텁이 답할 수 없는 것들이다:

- 🔴 `match_preference` 저장소가 `team`·`team_member`·`squad`·`squad_member`·
  `position`·`region`을 원시 SQL로 읽는다 — 저쪽 컬럼 이름이 바뀌면 파이썬이
  못 잡는다. **여기가 유일한 방어선이다.**
- 지역 시드(60개)가 실제로 들어가 있는가, 지역 계층(같은 구/같은 시)이 실제
  값으로 갈리는가
- 하드 필터(판 크기·로스터 충원)가 실제 스쿼드 데이터로 걸리는가
"""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import V1, error_code

pytestmark = pytest.mark.db

PASSWORD = "supersub2026"


def _account(db_client, nickname):
    nickname = f"{nickname}{uuid.uuid4().hex[:6]}"
    email = f"matchpref-{uuid.uuid4().hex[:12]}@super-sub.example"
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
        "nickname": nickname,
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


def _region_id(db_client, owner, label):
    rows = db_client.get(f"{V1}/regions", headers=owner["headers"]).json()
    return next(r["id"] for r in rows if r["label"] == label)


def _team(db_client, owner, name="팀", region="서울"):
    res = db_client.post(
        f"{V1}/teams",
        json={"name": f"{name}{uuid.uuid4().hex[:6]}", "region": region, "sport_code": "football"},
        headers=owner["headers"],
    )
    assert res.status_code == 201, res.text
    return uuid.UUID(res.json()["id"])


def _full_squad(db_client, owner, team_id, formation, extra_members):
    """스쿼드를 만들고 `formation` 만큼 카드를 채운다. `extra_members`는
    이미 팀에 가입된, 주장 포함하지 않은 계정 리스트여야 한다.
    """
    db_client.post(f"{V1}/teams/{team_id}/squad", headers=owner["headers"])
    db_client.patch(
        f"{V1}/teams/{team_id}/squad",
        json={"formation": formation},
        headers=owner["headers"],
    )
    for member in [owner] + extra_members:
        card = db_client.post(f"{V1}/me/card", headers=member["headers"]).json()
        res = db_client.post(
            f"{V1}/teams/{team_id}/squad/members",
            json={"player_card_id": card["id"], "position_code": "FW"},
            headers=owner["headers"],
        )
        assert res.status_code == 201, res.text


class TestTeamPreference:
    def test_팀장만_조건을_정할_수_있다(self, db_client):
        owner = _account(db_client, "주장")
        other = _account(db_client, "남")
        team_id = _team(db_client, owner)

        res = db_client.put(
            f"{V1}/teams/{team_id}/match-preferences",
            json={"region_ids": [], "slots": []},
            headers=other["headers"],
        )
        assert res.status_code == 403, res.text
        assert error_code(res) == "FORBIDDEN"

    def test_저장하고_다시_읽으면_같다(self, db_client):
        owner = _account(db_client, "주장")
        team_id = _team(db_client, owner)
        region_id = _region_id(db_client, owner, "서울 강남구")

        res = db_client.put(
            f"{V1}/teams/{team_id}/match-preferences",
            json={
                "region_ids": [str(region_id)],
                "slots": [{"weekday": 5, "start_time": "10:00:00", "end_time": "12:00:00"}],
            },
            headers=owner["headers"],
        )
        assert res.status_code == 200, res.text

        got = db_client.get(
            f"{V1}/teams/{team_id}/match-preferences", headers=owner["headers"]
        ).json()
        assert got["region_ids"] == [str(region_id)]
        assert got["slots"][0]["weekday"] == 5

    def test_시작이_끝보다_뒤면_422(self, db_client):
        owner = _account(db_client, "주장")
        team_id = _team(db_client, owner)

        res = db_client.put(
            f"{V1}/teams/{team_id}/match-preferences",
            json={
                "region_ids": [],
                "slots": [{"weekday": 0, "start_time": "12:00:00", "end_time": "10:00:00"}],
            },
            headers=owner["headers"],
        )
        assert res.status_code == 422, res.text
        assert error_code(res) == "INVALID_TIME_SLOT"

    def test_다시_저장하면_통째로_교체된다(self, db_client):
        owner = _account(db_client, "주장")
        team_id = _team(db_client, owner)
        r1 = _region_id(db_client, owner, "서울 강남구")
        r2 = _region_id(db_client, owner, "서울 서초구")

        db_client.put(
            f"{V1}/teams/{team_id}/match-preferences",
            json={"region_ids": [str(r1)], "slots": []},
            headers=owner["headers"],
        )
        db_client.put(
            f"{V1}/teams/{team_id}/match-preferences",
            json={"region_ids": [str(r2)], "slots": []},
            headers=owner["headers"],
        )
        got = db_client.get(
            f"{V1}/teams/{team_id}/match-preferences", headers=owner["headers"]
        ).json()
        assert got["region_ids"] == [str(r2)]


class TestMemberPreference:
    def test_저장하고_다시_읽으면_같다(self, db_client):
        me = _account(db_client, "나")
        region_id = _region_id(db_client, me, "서울 마포구")
        # `GET /positions`는 id를 안 준다(sport_code·code·label만) — position_ids
        # 왕복은 빈 리스트로만 확인한다.
        res = db_client.put(
            f"{V1}/me/match-preferences",
            json={
                "region_ids": [str(region_id)],
                "slots": [{"weekday": 1, "start_time": "19:00:00", "end_time": "21:00:00"}],
                "position_ids": [],
            },
            headers=me["headers"],
        )
        assert res.status_code == 200, res.text
        got = db_client.get(f"{V1}/me/match-preferences", headers=me["headers"]).json()
        assert got["region_ids"] == [str(region_id)]

    def test_팀_조건과_안_섞인다(self, db_client):
        owner = _account(db_client, "주장")
        team_id = _team(db_client, owner)
        r_team = _region_id(db_client, owner, "서울 강남구")
        r_me = _region_id(db_client, owner, "경기 수원시")

        db_client.put(
            f"{V1}/teams/{team_id}/match-preferences",
            json={"region_ids": [str(r_team)], "slots": []},
            headers=owner["headers"],
        )
        db_client.put(
            f"{V1}/me/match-preferences",
            json={"region_ids": [str(r_me)], "slots": [], "position_ids": []},
            headers=owner["headers"],
        )

        team_pref = db_client.get(
            f"{V1}/teams/{team_id}/match-preferences", headers=owner["headers"]
        ).json()
        member_pref = db_client.get(
            f"{V1}/me/match-preferences", headers=owner["headers"]
        ).json()
        assert team_pref["region_ids"] == [str(r_team)]
        assert member_pref["region_ids"] == [str(r_me)]


class TestListMemberPreferences:
    def test_팀장만_볼_수_있다(self, db_client):
        owner = _account(db_client, "주장")
        member = _account(db_client, "구성원")
        team_id = _team(db_client, owner)
        db_client.post(f"{V1}/teams/{team_id}/members", json={}, headers=member["headers"])

        res = db_client.get(
            f"{V1}/teams/{team_id}/members/match-preferences",
            headers=member["headers"],
        )
        assert res.status_code == 403, res.text

    def test_팀장은_팀원_조건을_본다(self, db_client):
        owner = _account(db_client, "주장")
        member = _account(db_client, "구성원")
        team_id = _team(db_client, owner)
        db_client.post(f"{V1}/teams/{team_id}/members", json={}, headers=member["headers"])

        r = _region_id(db_client, owner, "서울 강남구")
        db_client.put(
            f"{V1}/me/match-preferences",
            json={"region_ids": [str(r)], "slots": [], "position_ids": []},
            headers=member["headers"],
        )

        res = db_client.get(
            f"{V1}/teams/{team_id}/members/match-preferences",
            headers=owner["headers"],
        )
        assert res.status_code == 200, res.text
        rows = res.json()
        member_row = next(x for x in rows if x["user_id"] == str(member["id"]))
        assert member_row["nickname"] == member["nickname"]
        assert member_row["region_ids"] == [str(r)]


class TestMatchCandidates:
    def test_판_크기가_다르면_안_나온다(self, db_client):
        owner = _account(db_client, "주장A")
        team_a = _team(db_client, owner, "A")
        _full_squad(db_client, owner, team_a, "1:1", [])
        db_client.put(
            f"{V1}/teams/{team_a}/match-preferences",
            json={"region_ids": [], "slots": [{"weekday": 5, "start_time": "10:00:00", "end_time": "12:00:00"}]},
            headers=owner["headers"],
        )

        other_owner = _account(db_client, "주장B")
        team_b = _team(db_client, other_owner, "B")
        _full_squad(db_client, other_owner, team_b, "5:5", [])
        db_client.put(
            f"{V1}/teams/{team_b}/match-preferences",
            json={"region_ids": [], "slots": [{"weekday": 5, "start_time": "10:00:00", "end_time": "12:00:00"}]},
            headers=other_owner["headers"],
        )

        rows = db_client.get(
            f"{V1}/teams/{team_a}/match-candidates", headers=owner["headers"]
        ).json()
        assert str(team_b) not in [r["team_id"] for r in rows]

    def test_로스터가_안_찼으면_안_나온다(self, db_client):
        owner = _account(db_client, "주장A")
        mate = _account(db_client, "팀원A")
        team_a = _team(db_client, owner, "A")
        db_client.post(f"{V1}/teams/{team_a}/members", json={}, headers=mate["headers"])
        _full_squad(db_client, owner, team_a, "2:2", [mate])

        other_owner = _account(db_client, "주장B")
        team_b = _team(db_client, other_owner, "B")
        # 스쿼드는 만들되 formation만 "2:2"로 두고 카드는 1장만 채운다(부족 — 2명 필요).
        db_client.post(f"{V1}/teams/{team_b}/squad", headers=other_owner["headers"])
        db_client.patch(
            f"{V1}/teams/{team_b}/squad",
            json={"formation": "2:2"},
            headers=other_owner["headers"],
        )
        card = db_client.post(f"{V1}/me/card", headers=other_owner["headers"]).json()
        db_client.post(
            f"{V1}/teams/{team_b}/squad/members",
            json={"player_card_id": card["id"], "position_code": "FW"},
            headers=other_owner["headers"],
        )
        db_client.put(
            f"{V1}/teams/{team_b}/match-preferences",
            json={"region_ids": [], "slots": [{"weekday": 5, "start_time": "10:00:00", "end_time": "12:00:00"}]},
            headers=other_owner["headers"],
        )

        rows = db_client.get(
            f"{V1}/teams/{team_a}/match-candidates", headers=owner["headers"]
        ).json()
        assert str(team_b) not in [r["team_id"] for r in rows]

    def test_자기_팀은_안_나온다(self, db_client):
        owner = _account(db_client, "주장A")
        team_a = _team(db_client, owner, "A")
        _full_squad(db_client, owner, team_a, "1:1", [])

        rows = db_client.get(
            f"{V1}/teams/{team_a}/match-candidates", headers=owner["headers"]
        ).json()
        assert str(team_a) not in [r["team_id"] for r in rows]

    def test_지역_겹침과_시간_겹침이_사실값_근거로_온다(self, db_client):
        owner = _account(db_client, "주장A")
        team_a = _team(db_client, owner, "A")
        _full_squad(db_client, owner, team_a, "1:1", [])
        gangnam = _region_id(db_client, owner, "서울 강남구")
        db_client.put(
            f"{V1}/teams/{team_a}/match-preferences",
            json={
                "region_ids": [str(gangnam)],
                "slots": [{"weekday": 5, "start_time": "10:00:00", "end_time": "12:00:00"}],
            },
            headers=owner["headers"],
        )

        other_owner = _account(db_client, "주장B")
        team_b = _team(db_client, other_owner, "B")
        _full_squad(db_client, other_owner, team_b, "1:1", [])
        db_client.put(
            f"{V1}/teams/{team_b}/match-preferences",
            json={
                "region_ids": [str(gangnam)],
                "slots": [{"weekday": 5, "start_time": "11:00:00", "end_time": "13:00:00"}],
            },
            headers=other_owner["headers"],
        )

        rows = db_client.get(
            f"{V1}/teams/{team_a}/match-candidates", headers=owner["headers"]
        ).json()
        row = next(r for r in rows if r["team_id"] == str(team_b))
        kinds = {reason["kind"] for reason in row["reasons"]}
        assert "region" in kinds
        assert "time" in kinds
        time_reason = next(r for r in row["reasons"] if r["kind"] == "time")
        assert "11:00" in time_reason["detail"] and "12:00" in time_reason["detail"]
        # 🔴 유사도 점수는 절대 안 온다.
        assert "score" not in row and "similarity" not in row

    def test_조건을_하나도_안_올린_팀은_후보에_없다(self, db_client):
        owner = _account(db_client, "주장A")
        team_a = _team(db_client, owner, "A")
        _full_squad(db_client, owner, team_a, "1:1", [])
        db_client.put(
            f"{V1}/teams/{team_a}/match-preferences",
            json={"region_ids": [], "slots": [{"weekday": 5, "start_time": "10:00:00", "end_time": "12:00:00"}]},
            headers=owner["headers"],
        )

        other_owner = _account(db_client, "주장B")
        team_b = _team(db_client, other_owner, "B")
        _full_squad(db_client, other_owner, team_b, "1:1", [])
        # 경기 조건을 아예 등록하지 않는다.

        rows = db_client.get(
            f"{V1}/teams/{team_a}/match-candidates", headers=owner["headers"]
        ).json()
        assert str(team_b) not in [r["team_id"] for r in rows]
