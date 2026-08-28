"""영상·분석 도메인의 제약이 **DB 에 실재하는지** 실제 PostgreSQL 로 확인한다.

부록 D.7 은 유일 제약을 표로 적어 두었지만, 표에 적힌 것과 DB 에 걸린 것은 다른
문제다. 여기서 실제로 위반해 보고 막히는지 본다 — **막히지 않으면 그 제약은 없는
것이다.**

정상호 쪽 적재 코드가 이 제약들을 밟게 된다(같은 항목 두 번, 오타 난 지표 코드).
파이썬이 아니라 DB 가 막아 주어야 적재 경로가 무엇이든 안전하다.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

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
from tests.conftest import V1

pytestmark = pytest.mark.db

PASSWORD = "supersub2026"


@pytest.fixture
def chain(db_client, db_session):
    """업로더 → 영상 → 분석 작업 → 지표 묶음까지 한 줄로 만든다.

    시드 데이터에 기대지 않는다 — 기대면 시드 실행 여부에 테스트가 묶인다.
    """
    email = f"analysis-{uuid.uuid4().hex[:12]}@super-sub.example"
    signup = db_client.post(
        f"{V1}/auth/signup",
        json={"email": email, "password": PASSWORD, "nickname": "업로더"},
    )
    assert signup.status_code == 201, signup.text
    user_id = uuid.UUID(signup.json()["id"])

    now = datetime.now(timezone.utc)
    video_id, job_id, metric_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    code = f"knee-angle-{uuid.uuid4().hex[:6]}"

    db_session.add(
        MetricDefinitionOrm(
            code=code, label="임팩트 시 무릎 각도", unit="deg", sport_code="football"
        )
    )
    db_session.add(
        VideoOrm(
            id=video_id,
            user_id=user_id,
            sport_code="football",
            storage_key=f"videos/{video_id}.mp4",
            duration_ms=10_200,
            side="right",
            created_at=now,
        )
    )
    # 🔴 flush 로 INSERT 순서를 고정한다. 없으면 자식이 먼저 나가 외래키가 터진다.
    db_session.flush()
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
    db_session.commit()

    yield {
        "user_id": user_id,
        "video_id": video_id,
        "job_id": job_id,
        "metric_id": metric_id,
        "code": code,
        "now": now,
    }

    # 외래키 방향의 역순으로 지운다.
    db_session.rollback()
    for sql, params in (
        ("delete from analysis_report where analysis_metric_id = :m", {"m": str(metric_id)}),
        ("delete from analysis_metric_value where analysis_metric_id = :m", {"m": str(metric_id)}),
        ("delete from analysis_metric where id = :m", {"m": str(metric_id)}),
        ("delete from analysis_job where id = :j", {"j": str(job_id)}),
        ("delete from video where id = :v", {"v": str(video_id)}),
        ("delete from metric_definition where code = :c", {"c": code}),
        ("delete from user_credential where user_id = :u", {"u": str(user_id)}),
        ("delete from \"user\" where id = :u", {"u": str(user_id)}),
    ):
        db_session.execute(text(sql), params)
    db_session.commit()


def _value(chain, **overrides):
    args = {
        "id": uuid.uuid4(),
        "analysis_metric_id": chain["metric_id"],
        "metric_code": chain["code"],
        "value": Decimal("141.7000"),
        "frame_index": 62,
    }
    args.update(overrides)
    return AnalysisMetricValueOrm(**args)


class TestMetricValue:
    def test_같은_항목을_두_번_넣으면_막힌다(self, chain, db_session):
        """부록 D.7 — 항목당 값 1건. 재적재가 값을 두 벌로 만들면 안 된다."""
        db_session.add(_value(chain))
        db_session.commit()

        db_session.add(_value(chain))
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_정의에_없는_지표_코드는_막힌다(self, chain, db_session):
        """오타 하나가 조용히 **새 지표**가 되는 것을 외래키가 막는다."""
        db_session.add(_value(chain, metric_code="knee-angel-typo"))
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_넣은_수치가_그대로_나온다(self, chain, db_session):
        """QUA-001 의 확인 방법이 '같은 영상은 같은 값' 이라 왕복이 정확해야 한다."""
        db_session.add(_value(chain, value=Decimal("141.7000")))
        db_session.commit()

        stored = db_session.execute(
            text(
                "select value from analysis_metric_value "
                "where analysis_metric_id = :m"
            ),
            {"m": str(chain["metric_id"])},
        ).scalar_one()
        assert stored == Decimal("141.7000")


class TestOnePerParent:
    def test_작업당_지표_묶음은_하나다(self, chain, db_session):
        """부록 D.7. 두 벌이 되면 어느 것이 그 작업의 결과인지 알 수 없다."""
        db_session.add(
            AnalysisMetricOrm(
                id=uuid.uuid4(),
                analysis_job_id=chain["job_id"],
                pipeline_version="2026.08.28",
                created_at=chain["now"],
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_지표_묶음당_요약도_하나다(self, chain, db_session):
        db_session.add(
            AnalysisReportOrm(
                id=uuid.uuid4(),
                analysis_metric_id=chain["metric_id"],
                summary="디딤발이 공보다 앞서 있습니다.",
                model_name="exaone-4.0-1.2b",
                created_at=chain["now"],
            )
        )
        db_session.commit()

        db_session.add(
            AnalysisReportOrm(
                id=uuid.uuid4(),
                analysis_metric_id=chain["metric_id"],
                summary="두 번째 요약.",
                model_name="exaone-4.0-1.2b",
                created_at=chain["now"],
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()
