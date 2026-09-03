"""팀 출력 포트. 구현은 `adapter/outbound/pg/` (계약 테스트는 스텁을 끼운다)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.user.domain.entities.team_entity import TeamEntity, TeamMemberEntity


class TeamPort(ABC):
    @abstractmethod
    def sport_exists(self, sport_code: str) -> bool:
        """`sport` 에 있는 코드인가.

        `team.sport_code` 에는 **외래키가 없다**(부록 D.3 의 외래키 표에 없어서
        늘리지 않았다). 그래서 DB 가 막아 주지 않는 것을 입력 검증으로 거른다 —
        오타로 들어온 종목은 나중에 매칭에서 조용히 아무와도 안 걸린다.
        """

    @abstractmethod
    def find_team(self, team_id: UUID) -> TeamEntity | None: ...

    @abstractmethod
    def active_members(self, team_id: UUID) -> list[TeamMemberEntity]:
        """지금 소속된 구성원. **나간 사람(`left_at`)은 담지 않는다.**"""

    @abstractmethod
    def create_team(self, team: TeamEntity, owner_id: UUID) -> None:
        """팀과 `owner` 소속 1건을 **같은 트랜잭션에서** 만든다.

        나눠 쓰면 팀만 생기고 주장이 없는 상태가 남을 수 있다.
        """

    @abstractmethod
    def add_member(self, team_id: UUID, user_id: UUID) -> None:
        """`member` 로 넣는다. 재가입이면 새 행이다(부록 D.7 유일 제약이 셋 묶음)."""

    @abstractmethod
    def mark_left(self, team_id: UUID, user_id: UUID) -> None:
        """`left_at` 을 채운다. **행을 지우지 않는다** — 경기·평가 이력이 참조한다."""

    @abstractmethod
    def user_exists(self, user_id: UUID) -> bool: ...
