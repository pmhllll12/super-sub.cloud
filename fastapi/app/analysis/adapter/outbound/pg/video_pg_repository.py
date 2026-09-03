"""`VideoPort` 의 PostgreSQL 구현.

🔴 **`user` 컨텍스트를 임포트하지 않는다.** 종목이 있는지 확인해야 하는데
`sport` 는 저쪽 테이블이라, 모듈을 가져오지 않고 **필요한 컬럼만**
`table()`/`column()` 으로 읽는다(경기가 `team` 을 읽는 것과 같은 방식).

⚠️ 대가: 저쪽 컬럼 이름이 바뀌면 **파이썬이 잡아 주지 않는다.**
`tests/analysis/adapter/test_video_db.py` 가 유일한 방어선이다 — 지우지 말 것.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import column, select, table
from sqlalchemy.orm import Session

from app.analysis.adapter.outbound.orm.analysis_job_orm import AnalysisJobOrm
from app.analysis.adapter.outbound.orm.video_orm import VideoOrm
from app.analysis.adapter.outbound.orm.video_validation_orm import VideoValidationOrm
from app.analysis.application.ports.output.video_port import VideoPort
from app.analysis.domain.entities.video_entity import ValidationEntity, VideoEntity

# 소유하지 않는 테이블에서 **읽기만** 한다. 위 docstring 참조.
_sport = table("sport", column("code"))


class VideoPgRepository(VideoPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def sport_exists(self, sport_code: str) -> bool:
        stmt = select(_sport.c.code).where(_sport.c.code == sport_code)
        return self._session.execute(stmt).first() is not None

    def register(self, video: VideoEntity) -> None:
        """영상·판정·(통과 시) 작업을 한 트랜잭션에서 만든다."""
        validation = video.validation
        assert validation is not None, "등록은 검사 결과와 함께 온다"

        self._session.add(
            VideoOrm(
                id=video.id,
                user_id=video.user_id,
                sport_code=video.sport_code,
                storage_key=video.storage_key,
                duration_ms=video.duration_ms,
                side=video.side,
                created_at=video.created_at,
            )
        )
        # 🔴 `flush()` 로 순서를 고정한다. 판정과 작업이 `video.id` 를 참조하므로
        #    영상이 먼저 들어가야 한다 — 순서를 ORM 에 맡겼다가 자식이 먼저 나간
        #    적이 있다(2026-08-26, `user_credential`).
        self._session.flush()

        self._session.add(
            VideoValidationOrm(
                # 판정 행의 id 는 밖에서 쓰이지 않는다 — 영상당 1건이라 조회는
                # 언제나 `video_id` 로 한다. 그래서 여기서 만든다.
                id=uuid4(),
                video_id=video.id,
                passed=validation.passed,
                reject_reason=validation.reject_reason,
                checked_at=validation.checked_at,
            )
        )
        if video.analysis_job_id is not None:
            self._session.add(
                AnalysisJobOrm(
                    id=video.analysis_job_id,
                    video_id=video.id,
                    status=video.analysis_status,
                    created_at=video.created_at,
                )
            )
        self._session.commit()

    def list_by_user(self, user_id: UUID) -> list[VideoEntity]:
        rows = (
            self._session.execute(
                select(VideoOrm, VideoValidationOrm)
                .outerjoin(
                    VideoValidationOrm, VideoValidationOrm.video_id == VideoOrm.id
                )
                .where(VideoOrm.user_id == user_id)
                .order_by(VideoOrm.created_at.desc())
            )
            .tuples()
            .all()
        )
        if not rows:
            return []

        latest = self._latest_jobs([v.id for v, _ in rows])
        return [
            _to_entity(video, validation, latest.get(video.id))
            for video, validation in rows
        ]

    def _latest_jobs(
        self, video_ids: list[UUID]
    ) -> dict[UUID, AnalysisJobOrm]:
        """영상별 **가장 최근** 작업.

        같은 영상을 다시 분석하면 작업이 여러 건이다(`analysis_job` 은 일부러
        유일 제약이 없다). 화면은 최근 것 하나만 보여주므로 여기서 고른다 —
        오래된 순으로 읽어 덮어쓰면 마지막에 최근 것이 남는다.
        """
        jobs = (
            self._session.execute(
                select(AnalysisJobOrm)
                .where(AnalysisJobOrm.video_id.in_(video_ids))
                .order_by(AnalysisJobOrm.created_at)
            )
            .scalars()
            .all()
        )
        return {job.video_id: job for job in jobs}


def _to_entity(
    video: VideoOrm,
    validation: VideoValidationOrm | None,
    job: AnalysisJobOrm | None,
) -> VideoEntity:
    return VideoEntity(
        id=video.id,
        user_id=video.user_id,
        sport_code=video.sport_code,
        storage_key=video.storage_key,
        duration_ms=video.duration_ms,
        side=video.side,
        created_at=video.created_at,
        validation=(
            None
            if validation is None
            else ValidationEntity(
                passed=validation.passed,
                reject_reason=validation.reject_reason,
                checked_at=validation.checked_at,
            )
        ),
        analysis_job_id=None if job is None else job.id,
        analysis_status=None if job is None else job.status,
    )
