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
from app.match.domain.entities.match_entity import (
    MatchEntity,
    MatchListingEntity,
    PositionNeedEntity,
)


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
    def update_match(
        self,
        match_id: UUID,
        *,
        played_at: datetime | None,
        place: str | None,
        needs: list[PositionNeedEntity] | None,
    ) -> None:
        """경기를 고친다. `None` 인 항목은 건드리지 않는다.

        `needs` 를 주면 **기존 행을 지우고 새로 넣는다** — 부분 갱신은 "어느
        포지션을 빼라"를 표현할 수 없어서다. 지우기와 넣기는 **같은 트랜잭션**에서
        일어난다. 갈리면 필요 포지션이 사라진 경기가 남는다.
        """

    @abstractmethod
    def count_applications(self, match_id: UUID) -> int:
        """그 경기의 지원·제안 건수.

        취소 전에 본다. **DB 의 외래키가 이미 막고 있지만**(`match_application` 의
        삭제 규칙이 RESTRICT 다) 그대로 두면 500 이 나므로, 여기서 세어 뜻이 있는
        에러로 돌려준다.
        """

    @abstractmethod
    def delete_match(self, match_id: UUID) -> None:
        """경기를 지운다. 필요 포지션도 함께 지운다.

        🔴 **취소를 행 삭제로 표현한다.** 부록 D 의 `match` 에는 상태 컬럼이 없고
        D.8 도 취소를 다루지 않는다 — **ERD 에 없는 컬럼은 늘리지 않는다.**
        대신 스키마가 이미 말하고 있는 것을 따른다: 지원이 붙은 경기는 외래키가
        막는다.
        """

    @abstractmethod
    def list_upcoming_matches(
        self, team_id: UUID, now: datetime
    ) -> list[MatchEntity]:
        """그 팀의 **다가오는** 경기. 이른 것이 앞에 온다.

        지난 경기를 빼는 것은 목록이 **모집 글**이기 때문이다. 지난 경기도
        `find_match` 로는 여전히 읽힌다 — 기록이 사라지는 것이 아니다.
        """

    @abstractmethod
    def sport_exists(self, sport_code: str) -> bool:
        """종목 코드가 실재하는가.

        탐색에서 오타 난 코드를 **빈 결과가 아니라 에러**로 돌려주기 위해 쓴다 —
        빈 배열로 답하면 "그런 종목이 없다"와 "그 종목 경기가 없다"가 같아 보인다.
        """

    @abstractmethod
    def search_upcoming(
        self,
        *,
        sport_code: str | None,
        region: str | None,
        now: datetime,
        offset: int,
        limit: int,
    ) -> tuple[list[MatchListingEntity], int]:
        """**다가오는** 경기를 종목·지역으로 좁혀 찾는다. `(목록, 전체 건수)`.

        이른 것이 앞에 온다 — 목록은 모집 글이고 임박한 것이 급하다.

        지난 경기를 빼는 이유는 `list_upcoming_matches` 와 같다. **여기서는 더
        중요하다** — 팀 목록은 그 팀 사람이 보지만 이 목록은 지원할 곳을 찾는
        사람이 본다.
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

    @abstractmethod
    def delete_application(self, application_id: UUID) -> None:
        """지원 건을 지운다 — 무르기와 거절이 같은 동작이다.

        🔴 **이것이 `delete_match` 의 409 를 푸는 유일한 길이다**(미결 `jin` 16번).
        `match_application.match_id` 가 RESTRICT 라 행이 남아 있으면 경기를
        못 지운다. 거절을 컬럼으로 담으면 행이 남아 그대로 막힌다.
        """
