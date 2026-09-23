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

from sqlalchemy import Text, cast, column, func, or_, select, table, update
from sqlalchemy.orm import Session

from app.analysis.adapter.outbound.orm.analysis_job_orm import AnalysisJobOrm
from app.analysis.adapter.outbound.orm.analysis_metric_orm import AnalysisMetricOrm
from app.analysis.adapter.outbound.orm.analysis_report_orm import AnalysisReportOrm
from app.analysis.adapter.outbound.orm.video_orm import VideoOrm
from app.analysis.adapter.outbound.orm.video_validation_orm import VideoValidationOrm
from app.analysis.application.dtos.video_dto import UNSET, UserRef
from app.analysis.application.ports.output.video_port import VideoPort
from app.analysis.domain.entities.video_entity import (
    CardGradeRow,
    PriorAnalysisOutcome,
    ValidationEntity,
    VideoEntity,
)
from app.analysis.domain.rules.job_rules import ANALYZE, FAILED, SUCCEEDED

# 소유하지 않는 테이블에서 **읽기만** 한다. 위 docstring 참조.
_sport = table("sport", column("code"), column("active"))
_user = table("user", column("id"), column("nickname"), column("email"))
# `card` 컨텍스트 테이블. 슬러그→`user_id` 만 읽는다(경계 유지).
_player_card = table("player_card", column("public_slug"), column("user_id"))
# `review` 컨텍스트 테이블. 등급 화면의 신뢰 축(미결 `paik` 25·26번)만 읽는다 —
# `id`·`reviewee_id`(review)와 `review_id`·`option_code`(review_selection).
_review = table("review", column("id"), column("reviewee_id"))
_review_selection = table(
    "review_selection", column("review_id"), column("option_code")
)
# 신뢰 축에 쓰는 선택지 둘 — 재매칭 의사의 반대편(`paik` 26번 ⑴). 매너·실력
# 선택지는 여기서 세지 않는다(전부 긍정형이라 눈금이 안 선다).
_TRUST_POSITIVE_CODE = "repeat_yes"
_TRUST_OPTION_CODES = (_TRUST_POSITIVE_CODE, "caution_would_not_repeat")


class VideoPgRepository(VideoPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def sport_exists(self, sport_code: str) -> bool:
        stmt = select(_sport.c.code).where(_sport.c.code == sport_code)
        return self._session.execute(stmt).first() is not None

    def sport_is_active(self, sport_code: str) -> bool:
        stmt = select(_sport.c.code).where(
            _sport.c.code == sport_code, _sport.c.active.is_(True)
        )
        return self._session.execute(stmt).first() is not None

    def uploader_nickname(self, user_id: UUID) -> str | None:
        return self._session.execute(
            select(_user.c.nickname).where(_user.c.id == user_id)
        ).scalar_one_or_none()

    def resolve_user(self, identifier: str) -> UserRef | None:
        try:
            where = _user.c.id == UUID(identifier)
        except ValueError:
            # UUID 가 아니면 이메일로 본다(대소문자 무시).
            where = func.lower(_user.c.email) == identifier.lower()
        row = self._session.execute(
            select(_user.c.id, _user.c.nickname, _user.c.email).where(where)
        ).first()
        if row is None:
            return None
        return UserRef(id=row.id, nickname=row.nickname, email=row.email)

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
                width=video.width,
                height=video.height,
                is_public=video.is_public,
                kept=video.kept,
                original_filename=video.original_filename,
                created_at=video.created_at,
                content_hash=video.content_hash,
                duplicate_of_video_id=video.duplicate_of_video_id,
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
                    job_type=ANALYZE,
                    status=video.analysis_status,
                    created_at=video.created_at,
                    subject_box=video.subject_box,
                    subject_at_ms=video.subject_at_ms,
                    focus=video.focus,
                )
            )
        self._session.commit()

    def list_by_user(self, user_id: UUID) -> list[VideoEntity]:
        return self._by_user(user_id, kept_only=True)

    def count_kept_by_user(self, user_id: UUID, *, analyzed: bool) -> int:
        # `list_by_user` 와 **같은 조건**을 센다 — 행은 읽어 오지 않는다.
        # 🔴 갈래는 화면과 같이 `analysis_job` 행의 유무로 가른다. 목록이
        # 채우는 `analysis_job_id`(가장 최근 작업)와 같은 축이다.
        has_job = (
            select(AnalysisJobOrm.id)
            .where(AnalysisJobOrm.video_id == VideoOrm.id)
            .exists()
        )
        return int(
            self._session.execute(
                select(func.count())
                .select_from(VideoOrm)
                .where(
                    VideoOrm.user_id == user_id,
                    VideoOrm.kept.is_(True),
                    has_job if analyzed else ~has_job,
                )
            ).scalar_one()
        )

    def list_all_by_user(self, user_id: UUID) -> list[VideoEntity]:
        # 관리자는 아직 저장 안 한(`kept=false`) 임시분까지 본다.
        return self._by_user(user_id, kept_only=False)

    def _by_user(self, user_id: UUID, *, kept_only: bool) -> list[VideoEntity]:
        conditions = [VideoOrm.user_id == user_id]
        if kept_only:
            conditions.append(VideoOrm.kept.is_(True))
        rows = (
            self._session.execute(
                select(VideoOrm, VideoValidationOrm)
                .outerjoin(
                    VideoValidationOrm, VideoValidationOrm.video_id == VideoOrm.id
                )
                .where(*conditions)
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

    def find_featured_by_card_slug(
        self, card_public_slug: str
    ) -> VideoEntity | None:
        # 슬러그 → user_id 는 `player_card` 를 원시 쿼리로만 읽는다(경계 유지).
        owner = self._session.execute(
            select(_player_card.c.user_id).where(
                _player_card.c.public_slug == card_public_slug
            )
        ).scalar_one_or_none()
        if owner is None:
            return None

        video = self._session.execute(
            select(VideoOrm)
            .where(VideoOrm.user_id == owner, VideoOrm.is_featured.is_(True))
        ).scalar_one_or_none()
        if video is None:
            return None

        validation = self._session.execute(
            select(VideoValidationOrm).where(
                VideoValidationOrm.video_id == video.id
            )
        ).scalar_one_or_none()
        # 🔴 반려된 클립은 대표에서 뺀다 — 인터랙터가 세울 때 막지만, 세운 뒤
        #    재검사로 반려됐거나 옛 데이터가 있으면 여기서도 걸러야 한다.
        if not (validation and validation.passed):
            return None
        return _to_entity(video, validation, None)

    def find_card_grade(self, card_public_slug: str) -> CardGradeRow | None:
        # 슬러그 → user_id 는 `player_card` 를 원시 쿼리로만 읽는다(경계 유지) —
        # `find_featured_by_card_slug` 와 같은 패턴.
        owner = self._session.execute(
            select(_player_card.c.user_id).where(
                _player_card.c.public_slug == card_public_slug
            )
        ).scalar_one_or_none()
        if owner is None:
            return None

        # 대표 영상의 최신 리포트. 반려된 클립은 `analysis_job` 이 없어서(등록
        # 시 통과한 것만 작업이 생긴다) 이 조인이 자연히 걸러 낸다.
        report = self._session.execute(
            select(
                AnalysisReportOrm.overall_grade,
                AnalysisReportOrm.provisional,
                AnalysisReportOrm.card_notes,
            )
            .select_from(VideoOrm)
            .join(AnalysisJobOrm, AnalysisJobOrm.video_id == VideoOrm.id)
            .join(
                AnalysisMetricOrm,
                AnalysisMetricOrm.analysis_job_id == AnalysisJobOrm.id,
            )
            .join(
                AnalysisReportOrm,
                AnalysisReportOrm.analysis_metric_id == AnalysisMetricOrm.id,
            )
            .where(VideoOrm.user_id == owner, VideoOrm.is_featured.is_(True))
            .order_by(AnalysisMetricOrm.created_at.desc())
            .limit(1)
        ).first()

        # 신뢰 축. `review`·`review_selection` 은 `review` 컨텍스트 테이블이라
        # 원시 쿼리로만 읽는다 — 위 테이블 정의 참조.
        joined = _review.join(
            _review_selection, _review_selection.c.review_id == _review.c.id
        )
        trust_total = self._session.execute(
            select(func.count(func.distinct(_review.c.id)))
            .select_from(joined)
            .where(
                _review.c.reviewee_id == owner,
                _review_selection.c.option_code.in_(_TRUST_OPTION_CODES),
            )
        ).scalar_one()
        trust_positive = self._session.execute(
            select(func.count(func.distinct(_review.c.id)))
            .select_from(joined)
            .where(
                _review.c.reviewee_id == owner,
                _review_selection.c.option_code == _TRUST_POSITIVE_CODE,
            )
        ).scalar_one()

        return CardGradeRow(
            overall_grade=report.overall_grade if report else None,
            provisional=report.provisional if report else None,
            trust_positive=trust_positive,
            trust_total=trust_total,
            card_notes=report.card_notes if report else None,
        )

    def mark_kept(
        self, video_id: UUID, user_id: UUID, *, storage_key: str
    ) -> VideoEntity | None:
        video = self._session.get(VideoOrm, video_id)
        if video is None or video.user_id != user_id:
            return None
        video.kept = True
        video.storage_key = storage_key
        self._session.commit()

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
        return self._delete(video)

    def admin_delete(self, video_id: UUID) -> VideoEntity | None:
        # 소유 검사가 없다 — 관리자 인증이 그 자리를 대신한다.
        video = self._session.get(VideoOrm, video_id)
        if video is None:
            return None
        return self._delete(video)

    def find_prior_outcome(
        self, user_id: UUID, content_hash: str
    ) -> PriorAnalysisOutcome | None:
        # 🔴 `.is_(None)` 만으로는 안 걸린다. `subject_box`·`focus`는 SQLAlchemy
        # `JSON` 타입이라 지정 없이 등록한 값도 SQL `NULL`이 아니라 **JSON
        # `null` 리터럴**로 저장된다(`none_as_null` 기본값). 그래서 텍스트로
        # 캐스팅해 둘 다 잡는다 — 저장 방식이 앞으로 바뀌어도(`NULL`로만
        # 저장되게 고치는 등) 이 조건은 그대로 맞는다.
        no_subject_box = or_(
            AnalysisJobOrm.subject_box.is_(None),
            cast(AnalysisJobOrm.subject_box, Text) == "null",
        )
        no_focus = or_(
            AnalysisJobOrm.focus.is_(None),
            cast(AnalysisJobOrm.focus, Text) == "null",
        )
        row = self._session.execute(
            select(
                AnalysisJobOrm.video_id,
                AnalysisJobOrm.status,
                AnalysisJobOrm.failure_reason,
            )
            .join(VideoOrm, VideoOrm.id == AnalysisJobOrm.video_id)
            .where(
                VideoOrm.user_id == user_id,
                VideoOrm.content_hash == content_hash,
                AnalysisJobOrm.status.in_((SUCCEEDED, FAILED)),
                no_subject_box,
                no_focus,
            )
            .order_by(AnalysisJobOrm.created_at.desc())
            .limit(1)
        ).first()
        if row is None:
            return None
        return PriorAnalysisOutcome(
            video_id=row.video_id,
            status=row.status,
            failure_reason=row.failure_reason,
        )

    def _delete(self, video: VideoOrm) -> VideoEntity:
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
        is_featured: bool | Any = UNSET,
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
        if is_featured is not UNSET:
            if is_featured:
                # 🔴 **먼저 내린다** — 부분 유일 인덱스(`uq_video_featured_per_user`)
                #    가 사람당 하나만 허용하므로, 남을 안 내리면 이 UPDATE 가
                #    유일 위반으로 터진다. 같은 트랜잭션이라 창이 없다.
                self._session.execute(
                    update(VideoOrm)
                    .where(
                        VideoOrm.user_id == user_id,
                        VideoOrm.is_featured.is_(True),
                        VideoOrm.id != video_id,
                    )
                    .values(is_featured=False)
                )
            video.is_featured = is_featured
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

    def uploader_info(
        self, user_ids: list[UUID]
    ) -> dict[UUID, tuple[str, str | None]]:
        if not user_ids:
            return {}
        nicknames = dict(
            self._session.execute(
                select(_user.c.id, _user.c.nickname).where(
                    _user.c.id.in_(user_ids)
                )
            ).all()
        )
        slugs = dict(
            self._session.execute(
                select(_player_card.c.user_id, _player_card.c.public_slug).where(
                    _player_card.c.user_id.in_(user_ids)
                )
            ).all()
        )
        return {
            uid: (nickname, slugs.get(uid))
            for uid, nickname in nicknames.items()
        }

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
        width=video.width,
        height=video.height,
        is_public=video.is_public,
        is_featured=video.is_featured,
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
        analysis_failure_reason=None if job is None else job.failure_reason,
        content_hash=video.content_hash,
        duplicate_of_video_id=video.duplicate_of_video_id,
    )
