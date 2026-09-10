"""`analysis_job` 테이블. 부록 D 도메인 ② — PER-001.

분석 실행 1회다. **업로드 응답이 분석 완료를 기다리지 않는다**는 요구를 이 테이블이
받는다 — 업로드 시각과 완료 시각이 따로 남아야 그것을 확인할 수 있다.

같은 영상을 다시 분석할 수 있으므로 `video_id` 에 유일 제약을 걸지 않는다
(부록 D.7 에도 없다). 재분석 이력이 남는 편이 맞다 — 파이프라인 버전이 바뀌면
같은 영상에서 다른 지표가 나오고, 그 비교가 QUA-002 의 목적이다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AnalysisJobOrm(Base):
    __tablename__ = "analysis_job"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    video_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("video.id", ondelete="CASCADE"), nullable=False
    )

    # queued · running · succeeded · failed. 값 목록을 DB 제약으로 걸지 않는 이유는
    # 단계가 늘어날 때 마이그레이션 없이 넣기 위해서다.
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    # 실패 사유. 성공하면 비어 있다. 남기지 않으면 왜 실패했는지 물어볼 데가 없다.
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 🔴 시각 셋이 따로 있는 것이 PER-001 의 확인 방법이다. 하나로 합치면
    #    "업로드 응답이 분석을 기다렸는지"를 판별할 수 없다.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 워커가 만든 리포트를 가리키는 버킷 상대 S3 키 (미결 `paik` 11번).
    # 예: `reports/<user_id>/<video_id>/report.json`. 완료 보고(`PATCH
    # /internal/analysis-jobs/{id}`)가 `succeeded` 일 때만 채워진다 — 실패한
    # 작업엔 가리킬 리포트가 없다. 자리 규칙은 워커(`analyze_s3`)가 정본이라
    # 백엔드는 받은 값을 그대로 둔다. 상한은 S3 객체 키 한계다.
    report_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # 「이 사람으로 분석」 대상 박스 (미결 `paik` 6번). 정규화 `[x, y, w, h]`
    # (0~1) 리스트 · 그 박스를 그린 영상 시각(ms). 등록(`POST /videos`)이
    # 검증해서 넣고, `claim` 응답에 실려 워커의 `--subject-box`/`--subject-at-ms`
    # 로 흘러간다(`side`·`focus` 와 같은 축). 🔴 **지정이 없으면 둘 다 NULL 이고
    # 그게 정상 경로다** — 「자동으로 고르기」. 둘 중 하나만 찬 상태는 앱이 막는다.
    subject_box: Mapped[list | None] = mapped_column(JSON, nullable=True)
    subject_at_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 「집중해서 볼 항목」 (미결 `paik` 8번). 루브릭 `criteria[].id` 리스트.
    # `subject_box` 와 같은 축 — 등록이 받아 넣고 `claim` 응답 → 워커 `--focus`.
    # 🔴 **NULL(빈 목록) = 「전체적으로」가 기본**이다. 채점을 바꿀지(가중치
    # 재정규화)는 워커/루브릭 판단이고(미결 8번 안 B), 백엔드는 값만 나른다.
    focus: Mapped[list | None] = mapped_column(JSON, nullable=True)
