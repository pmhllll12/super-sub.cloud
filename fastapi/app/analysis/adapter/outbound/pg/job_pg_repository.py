"""`JobPort` 의 PostgreSQL 구현.

큐를 집는 자리라 **동시성이 전부**다. 아래 두 주석이 이 파일의 존재 이유다.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.analysis.adapter.outbound.orm.analysis_job_orm import AnalysisJobOrm
from app.analysis.adapter.outbound.orm.video_orm import VideoOrm
from app.analysis.application.ports.output.job_port import JobPort
from app.analysis.domain.entities.job_entity import ClaimedJobEntity
from app.analysis.domain.rules.job_rules import (
    FAILED,
    QUEUED,
    RECLAIM_FINAL,
    RECLAIM_FIRST,
    RUNNING,
)


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

    def reclaim_stale(self, timeout_minutes: int) -> tuple[int, int]:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
        stale = (
            AnalysisJobOrm.status == RUNNING,
            AnalysisJobOrm.started_at < cutoff,
        )

        # 두 UPDATE 는 **서로 겹치지 않는다.** 큐로 되돌리는 쪽이 `status` 를
        # `queued` 로 바꾸므로, 되돌린 행은 `stale`(= `running`) 조건에서 빠져
        # 나머지 한 문장에 다시 걸리지 않는다. 그래서 **순서는 결과를 바꾸지
        # 않는다** — 읽는 순서(끝낼 것 먼저, 되살릴 것 나중)로 두었을 뿐이다.
        #
        # ⚠️ 처음에 "순서를 바꾸면 되돌린 것이 곧바로 실패로 간다"고 적었는데
        #    **틀렸다.** 순서를 뒤집는 변이를 넣어도 검사가 통과해서 알았다.
        #    🔴 되돌리는 쪽이 `status` 를 안 바꾸게 고치면 그때는 순서가
        #    중요해진다 — 조건이 `running` 하나에만 기대고 있다.
        failed = self._session.execute(
            update(AnalysisJobOrm)
            .where(*stale, AnalysisJobOrm.failure_reason.is_not(None))
            .values(
                status=FAILED,
                failure_reason=RECLAIM_FINAL,
                finished_at=datetime.now(timezone.utc),
            )
        ).rowcount

        requeued = self._session.execute(
            update(AnalysisJobOrm)
            .where(*stale, AnalysisJobOrm.failure_reason.is_(None))
            .values(
                status=QUEUED,
                started_at=None,
                # 회수했다는 것을 남긴다. 다음에 또 멈추면 이 값이 있어서
                # 실패로 간다 — 컬럼을 안 늘리고 횟수를 한 번 세는 방법이다.
                failure_reason=RECLAIM_FIRST,
            )
        ).rowcount

        if failed or requeued:
            self._session.commit()
        else:
            self._session.rollback()
        return requeued, failed

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
