"""스쿼드 출력 포트.

🔴 **`team`·`team_member`·`position` 은 `user` 컨텍스트의 테이블이다.** 포트에 이
메서드들이 있어도 `card` 가 `user` 를 임포트하는 것은 아니다 — 구현이
`table()`/`column()` 원시 쿼리로 **필요한 컬럼만** 읽는다(카드가 `user.nickname` 을
읽는 것과 같은 방식).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.card.domain.entities.squad_entity import SquadEntity, SquadMemberEntity


class SquadPort(ABC):
    @abstractmethod
    def team_exists(self, team_id: UUID) -> bool: ...

    @abstractmethod
    def team_role_of(self, team_id: UUID, user_id: UUID) -> str | None:
        """지금 소속의 역할. 소속이 아니면 None (`left_at` 이 찬 행은 제외한다)."""

    @abstractmethod
    def find_by_team(self, team_id: UUID) -> SquadEntity | None: ...

    @abstractmethod
    def find_by_slug(self, public_slug: str) -> SquadEntity | None: ...

    @abstractmethod
    def create_for_team(self, team_id: UUID) -> tuple[SquadEntity, bool]:
        """스쿼드를 만들어 돌려준다. **이미 있으면 있는 것을 돌려준다.**

        두 번째 값이 "새로 만들었나"다. 슬러그 생성이 구현 쪽에 있는 이유는
        카드와 같다 — 유일 제약에 걸렸을 때 **다시 뽑아 재시도할 수 있는 곳이
        저장소뿐**이다. 규칙 자체는 도메인에 있다(`PublicSlug.generate`).
        """

    @abstractmethod
    def find_position(self, team_id: UUID, code: str) -> tuple[UUID, str] | None:
        """팀 **종목의** 포지션을 찾아 `(id, label)` 을 돌려준다. 없으면 None.

        약칭은 종목 안에서만 유일하므로(야구 `C` 는 포수, 농구 `C` 는 센터)
        팀을 거치지 않고 코드만으로 찾으면 **다른 종목의 포지션이 걸린다.**
        """

    @abstractmethod
    def card_owner(self, player_card_id: UUID) -> UUID | None:
        """그 카드 주인의 `user_id`. 카드가 없으면 None.

        등재하려는 카드가 **팀원의 것인지** 확인하는 데 쓴다.
        """

    @abstractmethod
    def enlist(
        self,
        squad_id: UUID,
        player_card_id: UUID,
        position_id: UUID,
        grid_col: int | None = None,
        grid_row: int | None = None,
    ) -> SquadMemberEntity:
        """카드를 등재한다. 같은 카드를 두 번 넣으면 유일 제약이 막는다(부록 D.7).

        `grid_col`·`grid_row` 는 등재하면서 판에 바로 올릴 때의 칸이다 — 인터랙터가
        both-or-neither 를 보장해 넘긴다.
        """

    @abstractmethod
    def update_member(
        self,
        member_id: UUID,
        position_id: UUID,
        grid_col: int | None,
        grid_row: int | None,
    ) -> SquadMemberEntity:
        """등재 하나의 포지션·판 배치를 바꾼다 (미결 `paik` 9번).

        `member_id` 가 이 팀 스쿼드의 것인지는 **인터랙터가 먼저 확인한다** — 여기는
        받은 값을 그대로 쓴다. 표시용 값(닉네임·슬러그)까지 채운 엔티티를 돌려준다.
        """

    @abstractmethod
    def set_formation(self, squad_id: UUID, formation: str) -> None:
        """판 크기를 저장한다 (미결 `paik` 9번). 값 규칙은 검사하지 않는다."""

    @abstractmethod
    def find_member(self, member_id: UUID) -> tuple[UUID, UUID] | None:
        """`(squad_id, player_card_id)`. 없으면 None.

        제외·이동할 때 **그 등재가 이 팀의 스쿼드 것인지** 확인하는 데 쓴다 — 확인
        없이 손대면 남의 스쿼드를 건드릴 수 있다.
        """

    @abstractmethod
    def discharge(self, member_id: UUID) -> None:
        """등재를 지운다. **카드는 지우지 않는다** — 스쿼드에서 빠질 뿐이다."""
