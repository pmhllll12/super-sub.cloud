"""메모리 저장소. 계약 테스트가 DB 없이 돌기 위한 것이다.

선택지 목록은 마이그레이션(`20260903_review_trust_tables` + `20260904_…sort_order`)
이 넣는 값과 같다. 여기서 갈리면 스텁으로는 통과하고 실물에서 깨진다.

⚠️ **유일 제약은 여기서 흉내만 낸다.** 실제로 동시 요청 둘을 갈라 주는지는 진짜
PostgreSQL 이라야 확인되고 `tests/review/adapter/test_review_db.py` 가 그 자리다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.review.application.ports.output.review_port import ReviewPort
from app.review.domain.entities.review_entity import (
    NoShowEntity,
    ReportEntity,
    ReviewEntity,
    ReviewOptionEntity,
)

_OPTIONS = [
    ReviewOptionEntity("manner_time", "manner", "시간을 잘 지켰다", 10),
    ReviewOptionEntity("manner_respect", "manner", "매너가 좋았다", 20),
    ReviewOptionEntity("manner_communication", "manner", "소통이 원활했다", 30),
    ReviewOptionEntity("skill_above_expected", "skill", "실력이 기대 이상이었다", 40),
    ReviewOptionEntity("skill_position_fit", "skill", "포지션 소화가 좋았다", 50),
    ReviewOptionEntity("skill_teamplay", "skill", "팀플레이가 좋았다", 60),
    ReviewOptionEntity("repeat_yes", "repeat", "다시 함께 뛰고 싶다", 70),
    ReviewOptionEntity(
        "caution_position_mismatch", "caution", "포지션이 안 맞았다", 80
    ),
    ReviewOptionEntity(
        "caution_would_not_repeat", "caution", "다시 함께 뛰고 싶지 않다", 90
    ),
]

_MATCHES: dict[UUID, datetime] = {}
_ROLES: dict[tuple[UUID, UUID], str] = {}
_CONFIRMED: set[tuple[UUID, UUID]] = set()
_USERS: set[UUID] = set()

_REVIEWS: dict[UUID, ReviewEntity] = {}
_NO_SHOWS: dict[UUID, NoShowEntity] = {}
_REPORTS: dict[UUID, ReportEntity] = {}


def reset_reviews() -> None:
    _MATCHES.clear()
    _ROLES.clear()
    _CONFIRMED.clear()
    _USERS.clear()
    _REVIEWS.clear()
    _NO_SHOWS.clear()
    _REPORTS.clear()


def register_match(match_id: UUID, played_at: datetime) -> None:
    """스텁에는 `match` 테이블이 없다. 검사가 "이 경기는 이 시각"이라고 알려 준다."""
    _MATCHES[match_id] = played_at


def register_role(match_id: UUID, user_id: UUID, role: str) -> None:
    _ROLES[(match_id, user_id)] = role


def register_confirmed(match_id: UUID, user_id: UUID) -> None:
    """그 경기에 확정된 사람. 실물은 `match_application` 의 두 시각이 다 찬 행이다."""
    _CONFIRMED.add((match_id, user_id))
    _USERS.add(user_id)


def register_user(user_id: UUID) -> None:
    _USERS.add(user_id)


def reviews_of(match_id: UUID) -> list[ReviewEntity]:
    return [r for r in _REVIEWS.values() if r.match_id == match_id]


def reports() -> list[ReportEntity]:
    return list(_REPORTS.values())


def no_shows() -> list[NoShowEntity]:
    return list(_NO_SHOWS.values())


class StubReviewRepository(ReviewPort):
    def list_options(self) -> list[ReviewOptionEntity]:
        return sorted(_OPTIONS, key=lambda o: o.sort_order)

    def option_codes(self) -> set[str]:
        return {o.code for o in _OPTIONS}

    def match_played_at(self, match_id: UUID) -> datetime | None:
        return _MATCHES.get(match_id)

    def team_role_of(self, match_id: UUID, user_id: UUID) -> str | None:
        return _ROLES.get((match_id, user_id))

    def is_confirmed_participant(self, match_id: UUID, user_id: UUID) -> bool:
        return (match_id, user_id) in _CONFIRMED

    def save_review(self, review: ReviewEntity) -> bool:
        already = any(
            r.match_id == review.match_id
            and r.reviewer_id == review.reviewer_id
            and r.reviewee_id == review.reviewee_id
            for r in _REVIEWS.values()
        )
        if already:
            return False
        _REVIEWS[review.id] = review
        return True

    def save_no_show(self, no_show: NoShowEntity) -> bool:
        already = any(
            n.match_id == no_show.match_id and n.user_id == no_show.user_id
            for n in _NO_SHOWS.values()
        )
        if already:
            return False
        _NO_SHOWS[no_show.id] = no_show
        return True

    def save_report(self, report: ReportEntity) -> None:
        _REPORTS[report.id] = report

    def user_exists(self, user_id: UUID) -> bool:
        return user_id in _USERS
