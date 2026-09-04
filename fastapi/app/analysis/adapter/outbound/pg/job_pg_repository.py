"""`JobPort` 의 PostgreSQL 구현.

큐를 집는 자리라 **동시성이 전부**다. 아래 두 주석이 이 파일의 존재 이유다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.analysis.adapter.outbound.orm.analysis_job_orm import AnalysisJobOrm
from app.analysis.adapter.outbound.orm.video_orm import VideoOrm
from app.analysis.application.ports.output.job_port import JobPort
from app.analysis.domain.entities.job_entity import ClaimedJobEntity
from app.analysis.domain.rules.job_rules import QUEUED, RUNNING


class JobPgRepository(JobPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def claim_next(self) -> ClaimedJobEntity | None:
        # 🔴 고를 행을 **잠그고** 고른다. `FOR UPDATE` 가 없으면 두 워커가 같은
        #    행을 골라 둘 다 running 으로 바꾼다(뒤엣것이 앞엣것을 덮는다).
        #    `SKIP LOCKED` 가 없으면 두 번째 워커가 첫 번째의 트랜잭션이 끝날
        #    때까지 **멈춰 선다** — 큐가 한 줄로 직렬화된다.
        oldest = (
            select(AnalysisJobOrm.id)
            .where(AnalysisJobOrm.status == QUEUED)
            .order_by(AnalysisJobOrm.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
            .scalar_subquery()
        )

        # 그 한 행만 바꾸고 id 를 받아 온다. 고르기와 바꾸기가 한 문장이다.
        claimed = self._session.execute(
            update(AnalysisJobOrm)
            .where(AnalysisJobOrm.id == oldest)
            .values(status=RUNNING, started_at=datetime.now(timezone.utc))
            .returning(AnalysisJobOrm.id, AnalysisJobOrm.video_id)
        ).first()

        if claimed is None:
            # 큐가 비었다. 커밋할 것이 없지만 잠금을 붙들고 있지 않도록 닫는다.
            self._session.rollback()
            return None

        job_id, video_id = claimed
        video = self._session.get(VideoOrm, video_id)
        if video is None:
            # 외래키가 CASCADE 라 정상 경로에서는 올 수 없다. 그래도 조용히
            # 넘기지 않는다 — 여기서 None 을 내면 워커는 "큐가 비었다"로 읽는다.
            self._session.rollback()
            raise RuntimeError(f"작업 {job_id} 의 영상 {video_id} 가 없다")

        self._session.commit()
        return ClaimedJobEntity(
            job_id=job_id,
            video_id=video_id,
            storage_key=video.storage_key,
            sport_code=video.sport_code,
            side=video.side,
            duration_ms=video.duration_ms,
        )

    def finish(
        self, job_id: UUID, status: str, failure_reason: str | None
    ) -> str | None:
        # `running` 일 때만 바꾼다. 조건을 SQL 에 두는 이유는 읽고 나서 쓰면
        # 그 사이에 다른 보고가 끼어들 수 있어서다.
        changed = self._session.execute(
            update(AnalysisJobOrm)
            .where(AnalysisJobOrm.id == job_id, AnalysisJobOrm.status == RUNNING)
            .values(
                status=status,
                failure_reason=failure_reason,
                finished_at=datetime.now(timezone.utc),
            )
        ).rowcount

        if changed:
            self._session.commit()
            return None

        # 못 바꿨다. 없는 것과 상태가 다른 것을 갈라 준다 — 호출한 쪽이 404 와
        # 409 를 구별해야 워커가 "재시도해도 소용없다"를 알 수 있다.
        current = self._session.execute(
            select(AnalysisJobOrm.status).where(AnalysisJobOrm.id == job_id)
        ).scalar_one_or_none()
        self._session.rollback()
        return current if current is not None else "missing"
