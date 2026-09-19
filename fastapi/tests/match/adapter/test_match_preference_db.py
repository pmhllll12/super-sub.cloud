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

import json
import uuid
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

import pytest
from sqlalchemy import text

from app.analysis.adapter.outbound.orm.analysis_job_orm import AnalysisJobOrm
from app.analysis.adapter.outbound.orm.video_orm import VideoOrm
from app.analysis.adapter.outbound.pg.report_ingest_pg_repository import (
    ReportIngestPgRepository,
)
from app.analysis.application.use_cases.report_parser import parse_report
from app.card.domain.entities.squad_entity import DEFAULT_FORMATION
from app.review.adapter.outbound.pg.review_pg_repository import ReviewPgRepository
from app.review.domain.entities.review_entity import ReviewEntity
from tests.conftest import V1, error_code

pytestmark = pytest.mark.db

PASSWORD = "supersub2026"


def _position_id(code: str, sport_code: str = "football") -> uuid.UUID:
    """`alembic/versions/20260902_match_tables.py`와 같은 계산 — 시드가
    `uuid5`로 고정돼 있어 DB를 안 거치고도 같은 id를 얻는다."""
    return uuid5(NAMESPACE_URL, f"supersub:position:{sport_code}:{code}")


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


def _required_for_default() -> int:
    """기본 판이 요구하는 인원 — `"5:5"` → 5. 상수를 두 번 적지 않으려는 것."""
    return int(DEFAULT_FORMATION.split(":")[0])


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
    def test_크기_단추를_한_번도_안_눌러도_서로_후보가_된다(self, db_client):
        """🔴 **운영에서 팀 매칭이 0건이던 결함**(2026-09-18).

        위아래의 다른 시험들은 `_full_squad` 가 **formation 을 손으로 PATCH**
        해 준다. 그런데 실제 사용자는 그 단추를 누르지 않는다 — 화면이 값이
        없을 때도 기본 판(5:5)을 **켜진 것처럼** 그리기 때문이다. 그래서
        저장은 「바꿀 때만」 일어났고 DB 는 `NULL` 로 남았으며, 첫 하드 필터가
        `formation` 동등 비교라 **운영 7팀 중 6팀이 서로를 못 봤다.**

        이 시험만 `PATCH /teams/{id}/squad` 를 **일부러 안 부른다.** 여기가
        「만들기」와 「매칭」이 이어지는지 보는 유일한 자리다 —
        `DEFAULT_FORMATION` 을 지우거나 `create_for_team` 에서 빼면 여기가
        빨개진다. 🔴 **편의를 위해 `_full_squad` 로 바꾸지 말 것** — 그 순간
        이 시험은 아무것도 안 지킨다.
        """
        slot = {"weekday": 5, "start_time": "10:00:00", "end_time": "12:00:00"}
        teams = []
        for name in ("A", "B"):
            owner = _account(db_client, f"주장{name}")
            team_id = _team(db_client, owner, name)
            # 🔴 스쿼드를 **만들기만** 한다. 크기는 안 건드린다.
            db_client.post(f"{V1}/teams/{team_id}/squad", headers=owner["headers"])
            mates = []
            for i in range(_required_for_default() - 1):
                mate = _account(db_client, f"팀원{name}{i}")
                db_client.post(
                    f"{V1}/teams/{team_id}/members", json={}, headers=mate["headers"]
                )
                mates.append(mate)
            for member in [owner] + mates:
                card = db_client.post(
                    f"{V1}/me/card", headers=member["headers"]
                ).json()
                res = db_client.post(
                    f"{V1}/teams/{team_id}/squad/members",
                    json={"player_card_id": card["id"], "position_code": "FW"},
                    headers=owner["headers"],
                )
                assert res.status_code == 201, res.text
            db_client.put(
                f"{V1}/teams/{team_id}/match-preferences",
                json={"region_ids": [], "slots": [slot]},
                headers=owner["headers"],
            )
            teams.append((owner, team_id))

        (owner_a, team_a), (_, team_b) = teams
        rows = db_client.get(
            f"{V1}/teams/{team_a}/match-candidates", headers=owner_a["headers"]
        ).json()
        assert str(team_b) in [r["team_id"] for r in rows], (
            "크기 단추를 안 눌렀다고 상대가 안 잡히면 안 된다 — "
            f"받은 후보: {rows}"
        )

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


def _grade_envelope(grade: str, provisional: bool = False, card_notes=None):
    """`card_notes` 를 주면 봉투 1.5 의 `result.card` 가 실린다(`paik` 33번)."""
    envelope = {
        "schema_version": "1.0",
        "source_video": "s3://b/videos/u/v.mp4",
        "analyzed_at": "20260910T120000Z",
        "code_version": "abc1234",
        "rubric": {"sport": "football", "motion": "instep_shot", "version": "0.1"},
        "swing_side": "right",
        "sampled_fps": 30.0,
        "frames": 300,
        "frame_metrics_seconds": {"impact_frame": 2.07},
        "judge_model": "exaone-4.0-1.2b",
        "features": {
            "trunk_forward_lean_deg_at_impact": 12.4,
            "plant_knee_angle_at_impact": 158.0,
            "impact_frame": 62,
        },
        "result": {
            "score": 90,
            "grade": grade,
            "summary": "빈 자리 후보 검사용 리포트입니다.",
            "pipeline_version": "pose-v0.1",
            "provisional": provisional,
            "breakdown": [
                {
                    "criterion_id": "plant_knee_flexion",
                    "name": "디딤발 무릎 굽히기",
                    "grade": 2,
                    "weight": 0.15,
                    "contribution": 15.0,
                    "title": "흔들리지 않는 축",
                    "band": "150~170",
                    "out_of_band": "",
                    "stat": 88.5,
                    "evidence": "안정적으로 놓였습니다.",
                    "metric_ref": "plant_knee_angle_at_impact",
                },
            ],
            "skipped": [],
        },
    }
    if card_notes is not None:
        envelope["result"]["card"] = {"title": None, "notes": card_notes}
    return envelope


class TestSquadCandidates:
    """`GET /teams/{id}/squad/candidates` (미결 `paik` 27번) — `member_match_
    position`·`squad_member`·`team_member`·`analysis_report`·`review` 다섯을
    실제 조인으로 확인한다. 컬럼 이름이 바뀌면 스텁은 못 잡는다.
    """

    def _give_featured_grade(
        self, db_session, user_id, *, grade, provisional=False, card_notes=None
    ):
        now = datetime.now(timezone.utc)
        video_id, job_id = uuid.uuid4(), uuid.uuid4()
        db_session.add(
            VideoOrm(
                id=video_id, user_id=user_id, sport_code="football",
                storage_key=f"videos/{video_id}.mp4", duration_ms=10_000,
                side="right", is_featured=True, created_at=now,
            )
        )
        db_session.flush()
        db_session.add(
            AnalysisJobOrm(id=job_id, video_id=video_id, status="succeeded", created_at=now)
        )
        db_session.commit()
        parsed = parse_report(
            json.dumps(_grade_envelope(grade, provisional, card_notes)).encode()
        )
        ReportIngestPgRepository(db_session).replace_for_job(job_id, parsed)

    def _minimal_match(self, db_session, team_id):
        match_id = uuid.uuid4()
        db_session.execute(
            text(
                "insert into match (id, team_id, played_at, place) "
                "values (:i, :t, now() - interval '1 day', '검사구장')"
            ),
            {"i": match_id, "t": team_id},
        )
        db_session.commit()
        return match_id

    def _add_review(self, db_session, *, match_id, reviewer_id, reviewee_id, codes):
        ok = ReviewPgRepository(db_session).save_review(
            ReviewEntity(
                id=uuid.uuid4(), match_id=match_id, reviewer_id=reviewer_id,
                reviewee_id=reviewee_id, submitted_at=datetime.now(timezone.utc),
                selected_codes=codes,
            )
        )
        assert ok, "리뷰 저장 실패 — FK/유일 제약 확인"

    def test_포지션_등급_제외를_실제_조인으로_확인한다(self, db_client, db_session):
        owner = _account(db_client, "주장")
        team_id = _team(db_client, owner, "빈자리")
        gk = _position_id("GK")

        # 지원자 1: GK 등록 + 등급 A + 리뷰 4건 전원 재매칭(신뢰 우세 → S).
        cand_s = _account(db_client, "지원자S")
        db_client.put(
            f"{V1}/me/match-preferences",
            json={"region_ids": [], "slots": [], "position_ids": [str(gk)]},
            headers=cand_s["headers"],
        )
        self._give_featured_grade(db_session, cand_s["id"], grade="A")
        for i in range(4):
            reviewer = _account(db_client, f"평가자{i}")
            self._add_review(
                db_session, match_id=self._minimal_match(db_session, team_id),
                reviewer_id=reviewer["id"], reviewee_id=cand_s["id"],
                codes=["repeat_yes"],
            )

        # 지원자 2: GK 등록, 분석 전(등급 없음) — null로 와야 한다.
        cand_none = _account(db_client, "지원자무등급")
        db_client.put(
            f"{V1}/me/match-preferences",
            json={"region_ids": [], "slots": [], "position_ids": [str(gk)]},
            headers=cand_none["headers"],
        )

        # 다른 포지션(FW)만 등록한 사람 — GK 후보에 안 나와야 한다.
        cand_wrong_position = _account(db_client, "공격수")
        fw = _position_id("FW")
        db_client.put(
            f"{V1}/me/match-preferences",
            json={"region_ids": [], "slots": [], "position_ids": [str(fw)]},
            headers=cand_wrong_position["headers"],
        )

        # 이미 이 팀 소속인 사람이 GK를 등록해도 후보에서 빠져야 한다.
        teammate = _account(db_client, "이미팀원")
        db_client.post(
            f"{V1}/teams/{team_id}/members", json={}, headers=teammate["headers"]
        )
        db_client.put(
            f"{V1}/me/match-preferences",
            json={"region_ids": [], "slots": [], "position_ids": [str(gk)]},
            headers=teammate["headers"],
        )

        res = db_client.get(
            f"{V1}/teams/{team_id}/squad/candidates",
            params={"position_code": "GK"},
            headers=owner["headers"],
        )
        assert res.status_code == 200, res.text
        rows = {r["user_id"]: r for r in res.json()}

        assert str(teammate["id"]) not in rows
        assert str(cand_wrong_position["id"]) not in rows

        assert rows[str(cand_s["id"])]["grade"] == "S"
        assert rows[str(cand_s["id"])]["provisional"] is False

        assert rows[str(cand_none["id"])]["grade"] is None
        assert rows[str(cand_none["id"])]["provisional"] is None

    def test_후보_불릿이_실제_analysis_report에서_온다(
        self, db_client, db_session
    ):
        """`paik` 33번 — `analysis_report.card_notes` 를 원시 SQL 로 읽는 자리.

        🔴 `analysis` 는 다른 컨텍스트라 `table()`/`column()` 으로 읽는다 —
        저쪽 컬럼 이름이 바뀌어도 파이썬이 안 잡아 준다. 스텁은 값을 손으로
        채우므로 **여기가 유일한 방어선이다.**
        """
        owner = _account(db_client, "주장")
        team_id = _team(db_client, owner, "불릿후보")
        gk = _position_id("GK")
        notes = ["차는 다리를 끝까지 뻗습니다", "디딤발을 공 옆에 붙입니다"]

        cand = _account(db_client, "불릿있음")
        db_client.put(
            f"{V1}/me/match-preferences",
            json={"region_ids": [], "slots": [], "position_ids": [str(gk)]},
            headers=cand["headers"],
        )
        self._give_featured_grade(
            db_session, cand["id"], grade="A", card_notes=notes
        )

        # 같은 포지션인데 옛 봉투로 적재된 사람 — `null` 이어야 한다.
        cand_old = _account(db_client, "불릿없음")
        db_client.put(
            f"{V1}/me/match-preferences",
            json={"region_ids": [], "slots": [], "position_ids": [str(gk)]},
            headers=cand_old["headers"],
        )
        self._give_featured_grade(db_session, cand_old["id"], grade="A")

        res = db_client.get(
            f"{V1}/teams/{team_id}/squad/candidates",
            params={"position_code": "GK"},
            headers=owner["headers"],
        )
        assert res.status_code == 200, res.text
        rows = {r["user_id"]: r for r in res.json()}

        assert rows[str(cand["id"])]["notes"] == notes
        # 🔴 등급은 정상인데 불릿만 없는 경우다 — 「분석이 없다」가 아니다.
        assert rows[str(cand_old["id"])]["notes"] is None
        assert rows[str(cand_old["id"])]["grade"] == "A"

    def test_이미_스쿼드에_앉은_사람은_제외된다(self, db_client, db_session):
        owner = _account(db_client, "주장")
        team_id = _team(db_client, owner, "빈자리앉음")

        db_client.post(f"{V1}/teams/{team_id}/squad", headers=owner["headers"])
        card = db_client.post(f"{V1}/me/card", headers=owner["headers"]).json()
        enlisted = db_client.post(
            f"{V1}/teams/{team_id}/squad/members",
            json={"player_card_id": card["id"], "position_code": "GK"},
            headers=owner["headers"],
        )
        assert enlisted.status_code == 201, enlisted.text

        # 주장 본인은 team_member라 어차피 제외되므로, 이 시험은 "자기 팀
        # 소속 제외"·"이미 앉은 사람 제외"가 함께 걸리는 가장 흔한 경로(주장
        # 본인)로 확인한다 — 앱 규칙(NOT_TEAM_MEMBER)상 스쿼드 등재는 항상
        # 팀 소속을 전제하므로 "팀 소속은 아니지만 이미 앉은" 조합은 만들
        # 수 없다.
        res = db_client.get(
            f"{V1}/teams/{team_id}/squad/candidates",
            params={"position_code": "GK"},
            headers=owner["headers"],
        )
        assert res.status_code == 200, res.text
        assert str(owner["id"]) not in {r["user_id"] for r in res.json()}
