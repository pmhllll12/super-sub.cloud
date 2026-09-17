"""탈퇴와 삭제 연쇄를 실제 PostgreSQL 로 확인한다. 5장 SEC-006 · 부록 D.6.

연쇄를 코드가 아니라 **외래키 규칙**으로 걸었으므로, 확인도 "실제로 지워지는가"로
해야 한다. 계정 하나에 카드·호칭·영상·분석 체인을 다 붙여 놓고 지운 뒤 남은 행을 센다.

**정의 테이블(`title_definition`·`metric_definition`)은 살아남아야 한다** — 개인
데이터가 아니라 참조하는 목록이고, 사람이 지워졌다고 사라지면 다른 사람 것이 깨진다.

⚠️ 저장소 객체(원본·썸네일·추출 프레임)는 이 검사의 범위 밖이다. 객체 저장소가
아직 없어서(5장 ASM-003) SEC-006 은 절반만 구현된 상태다.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.analysis.adapter.outbound.orm.analysis_job_orm import AnalysisJobOrm
from app.analysis.adapter.outbound.orm.analysis_metric_orm import AnalysisMetricOrm
from app.analysis.adapter.outbound.orm.analysis_metric_value_orm import (
    AnalysisMetricValueOrm,
)
from app.analysis.adapter.outbound.orm.analysis_report_orm import AnalysisReportOrm
from app.analysis.adapter.outbound.orm.metric_definition_orm import (
    MetricDefinitionOrm,
)
from app.analysis.adapter.outbound.orm.video_orm import VideoOrm
from app.card.adapter.outbound.orm.player_card_orm import PlayerCardOrm
from app.card.adapter.outbound.orm.title_definition_orm import TitleDefinitionOrm
from app.card.adapter.outbound.orm.user_title_orm import UserTitleOrm
from tests.conftest import V1, error_code

pytestmark = pytest.mark.db

PASSWORD = "supersub2026"


def _count(session, sql: str, params: dict) -> int:
    session.rollback()  # 다른 트랜잭션이 커밋한 결과를 읽는다
    return session.execute(text(sql), params).scalar_one()


@pytest.fixture
def account(db_client, db_session):
    """카드·호칭·영상·분석 체인을 전부 갖춘 계정. 연쇄가 지울 것들이다."""
    email = f"delete-{uuid.uuid4().hex[:12]}@super-sub.example"
    signup = db_client.post(
        f"{V1}/auth/signup",
        json={"email": email, "password": PASSWORD, "nickname": f"탈퇴시험{uuid.uuid4().hex[:6]}"},
    )
    assert signup.status_code == 201, signup.text
    user_id = uuid.UUID(signup.json()["id"])

    now = datetime.now(timezone.utc)
    title_code = f"title-{uuid.uuid4().hex[:8]}"
    metric_code = f"metric-{uuid.uuid4().hex[:8]}"
    video_id, job_id, metric_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    db_session.add(
        TitleDefinitionOrm(
            code=title_code, label="주말 개근", category="활동", sport_code="football"
        )
    )
    db_session.add(
        MetricDefinitionOrm(code=metric_code, label="무릎 각도", unit="deg")
    )
    db_session.add(
        PlayerCardOrm(
            id=uuid.uuid4(),
            user_id=user_id,
            public_slug=f"slug-{uuid.uuid4().hex[:10]}",
            og_image_key="cards/x.png",
        )
    )
    db_session.add(
        VideoOrm(
            id=video_id,
            user_id=user_id,
            sport_code="football",
            storage_key=f"videos/{video_id}.mp4",
            created_at=now,
        )
    )
    db_session.flush()
    db_session.add(
        UserTitleOrm(
            id=uuid.uuid4(), user_id=user_id, title_code=title_code, granted_at=now
        )
    )
    db_session.add(
        AnalysisJobOrm(id=job_id, video_id=video_id, status="succeeded", created_at=now)
    )
    db_session.flush()
    db_session.add(
        AnalysisMetricOrm(
            id=metric_id,
            analysis_job_id=job_id,
            pipeline_version="2026.08.28",
            created_at=now,
        )
    )
    db_session.flush()
    db_session.add(
        AnalysisMetricValueOrm(
            id=uuid.uuid4(),
            analysis_metric_id=metric_id,
            metric_code=metric_code,
            value=Decimal("141.7000"),
        )
    )
    db_session.add(
        AnalysisReportOrm(
            id=uuid.uuid4(),
            analysis_metric_id=metric_id,
            summary="디딤발이 앞섰습니다.",
            model_name="exaone-4.0-1.2b",
            created_at=now,
        )
    )
    db_session.commit()

    login = db_client.post(f"{V1}/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200

    yield {
        "email": email,
        "user_id": user_id,
        "title_code": title_code,
        "metric_code": metric_code,
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }

    # 탈퇴한 뒤라면 아무것도 안 남는다. 실패한 검사를 위해 남은 것만 지운다.
    db_session.rollback()
    db_session.execute(text('delete from "user" where id = :u'), {"u": str(user_id)})
    db_session.execute(
        text("delete from title_definition where code = :c"), {"c": title_code}
    )
    db_session.execute(
        text("delete from metric_definition where code = :c"), {"c": metric_code}
    )
    db_session.commit()


class TestDeleteMe:
    def test_계정과_파생_데이터가_함께_지워진다(self, db_client, db_session, account):
        res = db_client.request(
            "DELETE",
            f"{V1}/me",
            headers=account["headers"],
            json={"password": PASSWORD},
        )
        assert res.status_code == 204

        user_id = str(account["user_id"])
        assert _count(db_session, 'select count(*) from "user" where id = :u', {"u": user_id}) == 0
        for table, sql in (
            ("user_credential", "select count(*) from user_credential where user_id = :u"),
            ("player_card", "select count(*) from player_card where user_id = :u"),
            ("user_title", "select count(*) from user_title where user_id = :u"),
            ("video", "select count(*) from video where user_id = :u"),
        ):
            assert _count(db_session, sql, {"u": user_id}) == 0, f"{table} 이 남았다"

        # 영상 아래 체인도 함께 사라져야 한다(부록 D.6).
        left = _count(
            db_session,
            "select count(*) from analysis_metric_value v "
            "join analysis_metric m on m.id = v.analysis_metric_id "
            "join analysis_job j on j.id = m.analysis_job_id "
            "join video vd on vd.id = j.video_id where vd.user_id = :u",
            {"u": user_id},
        )
        assert left == 0

    def test_정의_테이블은_살아남는다(self, db_client, db_session, account):
        """사람이 지워졌다고 호칭·지표 정의가 사라지면 남의 데이터가 깨진다."""
        db_client.request(
            "DELETE", f"{V1}/me", headers=account["headers"], json={"password": PASSWORD}
        )

        assert (
            _count(
                db_session,
                "select count(*) from title_definition where code = :c",
                {"c": account["title_code"]},
            )
            == 1
        )
        assert (
            _count(
                db_session,
                "select count(*) from metric_definition where code = :c",
                {"c": account["metric_code"]},
            )
            == 1
        )

    def test_비밀번호가_틀리면_지워지지_않는다(self, db_client, db_session, account):
        res = db_client.request(
            "DELETE",
            f"{V1}/me",
            headers=account["headers"],
            json={"password": "wrong-password"},
        )
        assert res.status_code == 401
        assert error_code(res) == "INVALID_CREDENTIALS"
        assert (
            _count(
                db_session,
                'select count(*) from "user" where id = :u',
                {"u": str(account["user_id"])},
            )
            == 1
        )

    def test_비밀번호를_안_보내면_422(self, db_client, account):
        """되돌릴 수 없는 동작이라 토큰만으로는 실행하지 않는다."""
        res = db_client.request("DELETE", f"{V1}/me", headers=account["headers"])
        assert res.status_code == 422
        assert error_code(res) == "PASSWORD_REQUIRED"

    def test_지운_계정의_토큰은_막힌다(self, db_client, account):
        db_client.request(
            "DELETE", f"{V1}/me", headers=account["headers"], json={"password": PASSWORD}
        )

        after = db_client.get(f"{V1}/me", headers=account["headers"])
        assert after.status_code == 401
        assert error_code(after) == "INVALID_TOKEN"


# --- 남는 기록이 있는 사람의 탈퇴 (2026-09-17, 부록 D.6 · D.8) -----------------------
#
# 🔴 이 검사가 생기기 전에는 경기 지원·평가·신고·불참·크레딧·코치 연결·스쿼드 등재가
# 있는 사람의 탈퇴가 **외래키 위반으로 DB 에서 거부**됐다. 위 `account` 는 그런 기록이
# 없는 사람이라 통과했을 뿐이다.
#
# 처리 규칙(사용자 결정): **내 것은 함께 지우고, 남의 데이터이기도 한 것은 작성자만
# 비워 남긴다.** 내가 남에게 쓴 평가는 그 사람의 신뢰 등급 원자료이고, 내가 한 신고는
# 상대의 제재 근거다 — 지우면 남의 것이 바뀐다.


def _signup(db_client, tag):
    email = f"withdraw-{tag}-{uuid.uuid4().hex[:10]}@super-sub.example"
    res = db_client.post(
        f"{V1}/auth/signup",
        json={"email": email, "password": PASSWORD, "nickname": f"{tag}{uuid.uuid4().hex[:6]}"},
    )
    assert res.status_code == 201, res.text
    login = db_client.post(f"{V1}/auth/login", json={"email": email, "password": PASSWORD})
    return {
        "id": uuid.UUID(res.json()["id"]),
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


@pytest.fixture
def withdrawing(db_client, db_session):
    """막는 기록 일곱 종류를 전부 가진 사람(me)과 그 상대(other)."""
    me, other = _signup(db_client, "탈퇴자"), _signup(db_client, "상대")
    now = datetime.now(timezone.utc)
    ids = {k: uuid.uuid4() for k in (
        "team", "match", "card", "squad", "squad_member", "application",
        "review_by_me", "review_of_me", "report_by_me", "report_of_me",
        "no_show", "credit", "coach", "referral",
    )}
    gk = db_session.execute(
        text("select id from position where sport_code = 'football' and code = 'GK'")
    ).scalar_one()
    option = db_session.execute(
        text("select code from review_option order by sort_order limit 1")
    ).scalar_one()
    stmts = [
        ("insert into team (id, name, region, sport_code) values (:team, '탈퇴검사팀', '서울', 'football')", {}),
        ("insert into match (id, team_id, played_at, place) values (:match, :team, :now, '검사구장')", {}),
        ("insert into player_card (id, user_id, public_slug, og_image_key) values (:card, :me, :slug, '')",
         {"slug": f"wd-{uuid.uuid4().hex[:12]}"}),
        ("insert into squad (id, team_id, public_slug) values (:squad, :team, :sslug)",
         {"sslug": f"wds-{uuid.uuid4().hex[:12]}"}),
        ("insert into squad_member (id, squad_id, player_card_id, position_id) values (:squad_member, :squad, :card, :gk)", {}),
        ("insert into match_application (id, match_id, user_id) values (:application, :match, :me)", {}),
        ("insert into review (id, match_id, reviewer_id, reviewee_id, submitted_at) values (:review_by_me, :match, :me, :other, :now)", {}),
        ("insert into review_selection (review_id, option_code) values (:review_by_me, :option)", {}),
        ("insert into review (id, match_id, reviewer_id, reviewee_id, submitted_at) values (:review_of_me, :match, :other, :me, :now)", {}),
        ("insert into review_selection (review_id, option_code) values (:review_of_me, :option)", {}),
        ("insert into report (id, reporter_id, target_user_id, reason, created_at) values (:report_by_me, :me, :other, '검사', :now)", {}),
        ("insert into report (id, reporter_id, target_user_id, reason, created_at) values (:report_of_me, :other, :me, '검사', :now)", {}),
        ("insert into no_show (id, match_id, user_id, recorded_at) values (:no_show, :match, :me, :now)", {}),
        ("insert into analysis_credit (id, user_id, delta, reason, created_at) values (:credit, :me, 3, 'grant', :now)", {}),
        ("insert into coach (id, name, contact, sport_code) values (:coach, '검사코치', 'x', 'football')", {}),
        ("insert into coach_referral (id, user_id, coach_id, fee, created_at) values (:referral, :me, :coach, 0, :now)", {}),
    ]
    base = {**ids, "me": me["id"], "other": other["id"], "now": now, "gk": gk, "option": option}
    for sql, extra in stmts:
        db_session.execute(text(sql), {**base, **extra})
    db_session.commit()

    yield {"me": me, "other": other, "ids": ids}

    db_session.rollback()
    for sql in (
        "delete from review_selection where review_id in (select id from review where match_id = :match)",
        "delete from review where match_id = :match",
        "delete from report where id in (:report_by_me, :report_of_me)",
        "delete from no_show where match_id = :match",
        "delete from match_application where match_id = :match",
        "delete from squad_member where squad_id = :squad",
        "delete from squad where id = :squad",
        "delete from match where id = :match",
        "delete from team where id = :team",
        "delete from coach_referral where coach_id = :coach",
        "delete from coach where id = :coach",
        "delete from analysis_credit where id = :credit",
        "delete from player_card where id = :card",
        'delete from "user" where id in (:me, :other)',
    ):
        db_session.execute(text(sql), base)
    db_session.commit()


class TestDeleteMeWithRecords:
    def _withdraw(self, db_client, w):
        return db_client.request(
            "DELETE", f"{V1}/me", headers=w["me"]["headers"], json={"password": PASSWORD}
        )

    def test_남는_기록이_있어도_탈퇴된다(self, db_client, db_session, withdrawing):
        """🔴 이전에는 외래키 위반으로 DB 가 계정 삭제를 거부했다."""
        res = self._withdraw(db_client, withdrawing)
        assert res.status_code == 204, res.text
        assert _count(db_session, 'select count(*) from "user" where id = :u',
                      {"u": withdrawing["me"]["id"]}) == 0

    def test_내_기록은_함께_지워진다(self, db_client, db_session, withdrawing):
        self._withdraw(db_client, withdrawing)
        i = withdrawing["ids"]
        for label, sql, key in (
            ("경기 지원", "select count(*) from match_application where id = :x", "application"),
            ("나에 대한 평가", "select count(*) from review where id = :x", "review_of_me"),
            ("그 평가의 선택 결과", "select count(*) from review_selection where review_id = :x", "review_of_me"),
            ("나를 신고한 기록", "select count(*) from report where id = :x", "report_of_me"),
            ("내 불참", "select count(*) from no_show where id = :x", "no_show"),
            ("크레딧", "select count(*) from analysis_credit where id = :x", "credit"),
            ("코치 연결", "select count(*) from coach_referral where id = :x", "referral"),
            ("스쿼드 등재", "select count(*) from squad_member where id = :x", "squad_member"),
        ):
            assert _count(db_session, sql, {"x": i[key]}) == 0, f"{label} 이 남았다"

    def test_남에게_쓴_평가와_한_신고는_작성자만_비워_남는다(
        self, db_client, db_session, withdrawing
    ):
        """상대의 신뢰 등급 원자료와 제재 근거는 바뀌면 안 된다."""
        self._withdraw(db_client, withdrawing)
        i, other = withdrawing["ids"], withdrawing["other"]["id"]
        db_session.rollback()
        review = db_session.execute(
            text("select reviewer_id, reviewee_id from review where id = :x"), {"x": i["review_by_me"]}
        ).one()
        assert review.reviewer_id is None
        assert review.reviewee_id == other
        assert _count(db_session, "select count(*) from review_selection where review_id = :x",
                      {"x": i["review_by_me"]}) == 1, "상대가 받은 평가의 선택 결과가 사라졌다"
        report = db_session.execute(
            text("select reporter_id, target_user_id from report where id = :x"), {"x": i["report_by_me"]}
        ).one()
        assert report.reporter_id is None
        assert report.target_user_id == other

    def test_공유_데이터는_살아남는다(self, db_client, db_session, withdrawing):
        """경기·스쿼드·코치는 사람 한 명의 것이 아니다."""
        self._withdraw(db_client, withdrawing)
        i = withdrawing["ids"]
        for table, key in (("match", "match"), ("squad", "squad"), ("coach", "coach")):
            assert _count(db_session, f"select count(*) from {table} where id = :x",
                          {"x": i[key]}) == 1, f"{table} 이 사라졌다"
