"""`ReviewPort` 의 PostgreSQL 구현.

🔴 **`match` · `match_application` · `team_member` · `user` 를 임포트하지 않는다.**
전부 다른 컨텍스트의 테이블이라 모듈을 가져오지 않고 **필요한 컬럼만**
`table()`/`column()` 으로 읽는다(`match` 가 `team` 을 읽는 것과 같은 방식).

⚠️ 대가: 저쪽 컬럼 이름이 바뀌면 **파이썬이 잡아 주지 않는다.**
`tests/review/adapter/test_review_db.py` 가 유일한 방어선이다 — 지우지 말 것.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import column, insert, select, table
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.review.adapter.outbound.orm.no_show_orm import NoShowOrm
from app.review.adapter.outbound.orm.report_orm import ReportOrm
from app.review.adapter.outbound.orm.review_option_orm import ReviewOptionOrm
from app.review.adapter.outbound.orm.review_orm import ReviewOrm
from app.review.adapter.outbound.orm.review_selection_orm import ReviewSelectionOrm
from app.review.application.ports.output.review_port import ReviewPort
from app.review.domain.entities.review_entity import (
    NoShowEntity,
    ReportEntity,
    ReviewEntity,
    ReviewOptionEntity,
)

# 소유하지 않는 테이블에서 **읽기만** 한다. 위 docstring 참조.
_match = table("match", column("id"), column("team_id"), column("played_at"))
_application = table(
    "match_application",
    column("match_id"),
    column("user_id"),
    column("team_accepted_at"),
    column("user_accepted_at"),
)
_team_member = table(
    "team_member", column("team_id"), column("user_id"), column("role")
)
_user = table("user", column("id"))


class ReviewPgRepository(ReviewPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_options(self) -> list[ReviewOptionEntity]:
        rows = self._session.execute(
            select(ReviewOptionOrm).order_by(ReviewOptionOrm.sort_order)
        ).scalars()
        return [
            ReviewOptionEntity(
                code=r.code, category=r.category, label=r.label, sort_order=r.sort_order
            )
            for r in rows
        ]

    def option_codes(self) -> set[str]:
        return set(self._session.execute(select(ReviewOptionOrm.code)).scalars())

    def match_played_at(self, match_id: UUID) -> datetime | None:
        stmt = select(_match.c.played_at).where(_match.c.id == match_id)
        return self._session.execute(stmt).scalar_one_or_none()

    def team_role_of(self, match_id: UUID, user_id: UUID) -> str | None:
        stmt = (
            select(_team_member.c.role)
            .select_from(
                _match.join(_team_member, _team_member.c.team_id == _match.c.team_id)
            )
            .where(_match.c.id == match_id, _team_member.c.user_id == user_id)
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def is_confirmed_participant(self, match_id: UUID, user_id: UUID) -> bool:
        # 두 수락 시각이 **다 찬** 행만 확정이다 (부록 D.5).
        stmt = select(_application.c.match_id).where(
            _application.c.match_id == match_id,
            _application.c.user_id == user_id,
            _application.c.team_accepted_at.is_not(None),
            _application.c.user_accepted_at.is_not(None),
        )
        return self._session.execute(stmt).first() is not None

    def save_review(self, review: ReviewEntity) -> bool:
        # 🔴 중복을 파이썬으로 미리 세지 않는다 — 세고 넣는 사이에 다른 요청이
        #    끼어들면 둘 다 통과한다. 유일 제약이 막게 두고 그 실패를 읽는다.
        try:
            self._session.add(
                ReviewOrm(
                    id=review.id,
                    match_id=review.match_id,
                    reviewer_id=review.reviewer_id,
                    reviewee_id=review.reviewee_id,
                    submitted_at=review.submitted_at,
                )
            )
            self._session.flush()
            self._session.execute(
                insert(ReviewSelectionOrm),
                [
                    {"review_id": review.id, "option_code": code}
                    for code in review.selected_codes
                ],
            )
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            return False
        return True

    def save_no_show(self, no_show: NoShowEntity) -> bool:
        try:
            self._session.add(
                NoShowOrm(
                    id=no_show.id,
                    match_id=no_show.match_id,
                    user_id=no_show.user_id,
                    recorded_at=no_show.recorded_at,
                )
            )
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            return False
        return True

    def save_report(self, report: ReportEntity) -> None:
        self._session.add(
            ReportOrm(
                id=report.id,
                reporter_id=report.reporter_id,
                target_user_id=report.target_user_id,
                reason=report.reason,
                created_at=report.created_at,
            )
        )
        self._session.commit()

    def user_exists(self, user_id: UUID) -> bool:
        stmt = select(_user.c.id).where(_user.c.id == user_id)
        return self._session.execute(stmt).first() is not None
