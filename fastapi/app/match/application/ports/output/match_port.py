"""경기 출력 포트.

🔴 **`team`·`team_member`·`position` 은 `user` 컨텍스트의 테이블이다.** 포트에
이 메서드들이 있어도 `match` 가 `user` 를 임포트하는 것은 아니다 — 구현이
`table()`/`column()` 원시 쿼리로 **필요한 컬럼만** 읽는다(카드가 `user.nickname` 을
읽는 것과 같은 방식).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.match.domain.entities.application_entity import ApplicationEntity
from app.match.domain.entities.match_entity import MatchEntity, PositionNeedEntity


class MatchPort(ABC):
    @abstractmethod
    def team_exists(self, team_id: UUID) -> bool: ...

    @abstractmethod
    def team_role_of(self, team_id: UUID, user_id: UUID) -> str | None:
        """지금 소속의 역할. 소속이 아니면 None (`left_at` 이 찬 행은 제외한다)."""

    @abstractmethod
    def find_positions(
        self, team_id: UUID, codes: list[str]
    ) -> dict[str, PositionNeedEntity]:
        """팀 **종목의** 포지션만 찾는다. 없는 코드는 결과에 담기지 않는다.

        약칭은 종목 안에서만 유일하므로(야구 `C` 는 포수, 농구 `C` 는 센터)
        팀을 거치지 않고 코드만으로 찾으면 **다른 종목의 포지션이 걸린다.**
        `head_count` 는 여기서 채우지 않는다 — 요청이 정한다.
        """

    @abstractmethod
    def create_match(self, match: MatchEntity) -> None:
        """경기와 필요 포지션을 **같은 트랜잭션에서** 만든다."""

    @abstractmethod
    def find_match(self, match_id: UUID) -> MatchEntity | None: ...

    @abstractmethod
    def list_upcoming_matches(
        self, team_id: UUID, now: datetime
    ) -> list[MatchEntity]:
        """그 팀의 **다가오는** 경기. 이른 것이 앞에 온다.

        지난 경기를 빼는 것은 목록이 **모집 글**이기 때문이다. 지난 경기도
        `find_match` 로는 여전히 읽힌다 — 기록이 사라지는 것이 아니다.
        """

    @abstractmethod
    def user_exists(self, user_id: UUID) -> bool: ...

    @abstractmethod
    def find_application(
        self, match_id: UUID, user_id: UUID
    ) -> ApplicationEntity | None:
        """경기당 1인 1건이라 이 둘이면 유일하다(부록 D.7)."""

    @abstractmethod
    def find_application_by_id(
        self, application_id: UUID
    ) -> ApplicationEntity | None: ...

    @abstractmethod
    def list_applications(self, match_id: UUID) -> list[ApplicationEntity]: ...

    @abstractmethod
    def create_application(
        self, match_id: UUID, user_id: UUID, side: str
    ) -> ApplicationEntity:
        """지원(`side="user"`)이나 제안(`side="team"`)을 만든다.

        **시작한 쪽의 시각만 채운다.** 나머지 한쪽은 상대가 수락할 때 찬다 —
        그 둘이 다 차야 확정이다(부록 D.5).
        """

    @abstractmethod
    def accept_application(self, application_id: UUID, side: str) -> ApplicationEntity:
        """비어 있던 쪽 시각을 채운다."""
