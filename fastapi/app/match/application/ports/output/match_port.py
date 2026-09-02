"""경기 출력 포트.

🔴 **`team`·`team_member`·`position` 은 `user` 컨텍스트의 테이블이다.** 포트에
이 메서드들이 있어도 `match` 가 `user` 를 임포트하는 것은 아니다 — 구현이
`table()`/`column()` 원시 쿼리로 **필요한 컬럼만** 읽는다(카드가 `user.nickname` 을
읽는 것과 같은 방식).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

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
