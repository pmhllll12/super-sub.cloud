"""평가·신뢰 출력 포트.

🔴 **`match` 와 `user` 는 다른 컨텍스트의 테이블이다.** 포트에 `match_played_at`
같은 것이 있어도 `review` 가 저쪽을 임포트하는 것은 아니다 — 구현이
`table()`/`column()` 원시 쿼리로 필요한 컬럼만 읽는다(`match` 가 `team` 을 읽는
방식과 같다).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.review.domain.entities.review_entity import (
    NoShowEntity,
    ReportEntity,
    ReviewEntity,
    ReviewOptionEntity,
)


class ReviewPort(ABC):
    @abstractmethod
    def list_options(self) -> list[ReviewOptionEntity]:
        """선택지 전부. **`sort_order` 순으로** 준다 — 화면 노출 순서다."""

    @abstractmethod
    def option_codes(self) -> set[str]:
        """있는 선택지 코드. 없는 코드를 담은 평가를 거르는 데 쓴다."""

    @abstractmethod
    def match_played_at(self, match_id: UUID) -> datetime | None:
        """경기 시각. 없는 경기면 None. **남의 테이블을 원시 쿼리로 읽는다.**"""

    @abstractmethod
    def team_role_of(self, match_id: UUID, user_id: UUID) -> str | None:
        """그 경기 주최 팀에서의 역할. 소속이 아니면 None."""

    @abstractmethod
    def is_confirmed_participant(self, match_id: UUID, user_id: UUID) -> bool:
        """그 경기에 **확정된** 사람인가.

        `match_application` 의 **두 수락 시각이 다 찬 행**이 확정이다(부록 D.5 —
        "매칭 확정은 사람이 한다"). 상태 컬럼이 없으므로 시각 둘로 읽는다.
        """

    @abstractmethod
    def save_review(self, review: ReviewEntity) -> bool:
        """평가와 선택 결과를 **한 트랜잭션에서** 만든다.

        이미 있으면(유일 제약 위반) `False`. 🔴 **파이썬으로 미리 세어 보고
        넣지 않는다** — 그 사이에 다른 요청이 끼어들면 둘 다 통과한다.
        """

    @abstractmethod
    def save_no_show(self, no_show: NoShowEntity) -> bool:
        """이미 있으면 `False`. 위와 같은 이유로 DB 제약에 맡긴다."""

    @abstractmethod
    def save_report(self, report: ReportEntity) -> None:
        """신고는 중복을 막지 않는다 — 같은 사람을 여러 번 신고할 수 있다."""

    @abstractmethod
    def user_exists(self, user_id: UUID) -> bool: ...
