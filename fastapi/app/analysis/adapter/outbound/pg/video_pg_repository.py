"""`VideoPort` 의 PostgreSQL 구현.

🔴 **`user` 컨텍스트를 임포트하지 않는다.** 종목이 있는지 확인해야 하는데
`sport` 는 저쪽 테이블이라, 모듈을 가져오지 않고 **필요한 컬럼만**
`table()`/`column()` 으로 읽는다(경기가 `team` 을 읽는 것과 같은 방식).

⚠️ 대가: 저쪽 컬럼 이름이 바뀌면 **파이썬이 잡아 주지 않는다.**
`tests/analysis/adapter/test_video_db.py` 가 유일한 방어선이다 — 지우지 말 것.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import column, select, table
from sqlalchemy.orm import Session

from app.analysis.adapter.outbound.orm.analysis_job_orm import AnalysisJobOrm
from app.analysis.adapter.outbound.orm.video_orm import VideoOrm
from app.analysis.adapter.outbound.orm.video_validation_orm import VideoValidationOrm
from app.analysis.application.dtos.video_dto import UNSET
from app.analysis.application.ports.output.video_port import VideoPort
from app.analysis.domain.entities.video_entity import ValidationEntity, VideoEntity

# 소유하지 않는 테이블에서 **읽기만** 한다. 위 docstring 참조.
_sport = table("sport", column("code"))
_user = table("user", column("id"), column("nickname"))


class VideoPgRepository(VideoPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def sport_exists(self, sport_code: str) -> bool:
        stmt = select(_sport.c.code).where(_sport.c.code == sport_code)
        return self._session.execute(stmt).first() is not None

    def uploader_nickname(self, user_id: UUID) -> str | None:
        return self._session.execute(
            select(_user.c.nickname).where(_user.c.id == user_id)
        ).scalar_one_or_none()

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
                is_public=video.is_public,
                kept=video.kept,
                original_filename=video.original_filename,
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
                .where(VideoOrm.user_id == user_id, VideoOrm.kept.is_(True))
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

    def get(self, video_id: UUID) -> VideoEntity | None:
        video = self._session.get(VideoOrm, video_id)
        if video is None:
            return None
        validation = self._session.execute(
            select(VideoValidationOrm).where(
                VideoValidationOrm.video_id == video_id
            )
        ).scalar_one_or_none()
        latest = self._latest_jobs([video_id]).get(video_id)
        return _to_entity(video, validation, latest)

    def delete(self, video_id: UUID, user_id: UUID) -> VideoEntity | None:
        video = self._session.get(VideoOrm, video_id)
        if video is None or video.user_id != user_id:
            return None
        entity = _to_entity(video, None, None)  # S3 정리에 storage_key 만 필요
        self._session.delete(video)  # FK ON DELETE CASCADE 가 자식을 정리한다
        self._session.commit()
        return entity

    def sweep_provisional(self, ttl_hours: int) -> list[VideoEntity]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=ttl_hours)
        # 이 영상에 아직 안 끝난 작업이 붙어 있나 — 있으면 지우지 않는다.
        active_job = (
            select(AnalysisJobOrm.id)
            .where(
                AnalysisJobOrm.video_id == VideoOrm.id,
                AnalysisJobOrm.status.in_(("queued", "running")),
            )
            .exists()
        )
        stale = (
            self._session.execute(
                select(VideoOrm).where(
                    VideoOrm.kept.is_(False),
                    VideoOrm.created_at < cutoff,
                    ~active_job,
                )
            )
            .scalars()
            .all()
        )
        if not stale:
            return []
        entities = [_to_entity(v, None, None) for v in stale]
        for v in stale:
            self._session.delete(v)  # 판정·작업 연쇄는 FK CASCADE
        self._session.commit()
        return entities

    def update_video(
        self,
        video_id: UUID,
        user_id: UUID,
        *,
        is_public: bool | Any = UNSET,
        title: str | None | Any = UNSET,
        description: str | None | Any = UNSET,
    ) -> VideoEntity | None:
        video = self._session.get(VideoOrm, video_id)
        if video is None or video.user_id != user_id:
            return None
        if is_public is not UNSET:
            video.is_public = is_public
        if title is not UNSET:
            video.title = title
        if description is not UNSET:
            video.description = description
        self._session.commit()

        validation = self._session.execute(
            select(VideoValidationOrm).where(
                VideoValidationOrm.video_id == video_id
            )
        ).scalar_one_or_none()
        latest = self._latest_jobs([video_id]).get(video_id)
        return _to_entity(video, validation, latest)

    def list_public(self, limit: int) -> list[VideoEntity]:
        videos = (
            self._session.execute(
                select(VideoOrm)
                .where(VideoOrm.is_public.is_(True), VideoOrm.kept.is_(True))
                .order_by(VideoOrm.created_at.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
        # 목록은 반려 사유·분석 상태를 보여주지 않는다 — 판정·작업을 안 읽는다.
        return [_to_entity(v, None, None) for v in videos]

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
        is_public=video.is_public,
        title=video.title,
        description=video.description,
        kept=video.kept,
        original_filename=video.original_filename,
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
