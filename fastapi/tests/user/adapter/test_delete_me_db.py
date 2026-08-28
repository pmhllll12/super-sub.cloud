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
        json={"email": email, "password": PASSWORD, "nickname": "탈퇴시험"},
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
        MetricDefinitionOrm(
            code=metric_code, label="무릎 각도", unit="deg", sport_code="football"
        )
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
