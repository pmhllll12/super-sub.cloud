"""경기 유스케이스가 주고받는 DTO. **원시 타입만** 담는다."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class PositionNeedInput:
    position_code: str
    head_count: int


@dataclass(frozen=True)
class CreateMatchCommand:
    actor_id: UUID
    team_id: UUID
    played_at: datetime
    place: str
    needs: list[PositionNeedInput]


@dataclass(frozen=True)
class UpdateMatchCommand:
    """경기를 고친다. **`None` 은 "안 바꾼다"는 뜻이다.**

    셋 다 `null` 이 뜻을 갖지 않는 값이라(시각·장소·필요 포지션은 비울 수 없다)
    "안 보냄"과 "null 로 지움"을 가를 필요가 없다.

    `needs` 를 보내면 **통째로 갈아 끼운다.** 부분 갱신은 "어느 포지션을 빼라"를
    표현할 방법이 없어 뜻이 애매해진다.
    """

    actor_id: UUID
    match_id: UUID
    played_at: datetime | None = None
    place: str | None = None
    needs: list[PositionNeedInput] | None = None


@dataclass(frozen=True)
class CancelMatchCommand:
    actor_id: UUID
    match_id: UUID


@dataclass(frozen=True)
class TeamMatchesQuery:
    team_id: UUID


@dataclass(frozen=True)
class MatchQuery:
    match_id: UUID


@dataclass(frozen=True)
class MatchSearchQuery:
    """경기 탐색. **팀 id 를 몰라도 찾을 수 있는 유일한 경로다.**

    `sport_code` 와 `region` 은 비울 수 있고, 비우면 그 축으로 좁히지 않는다.
    """

    sport_code: str | None
    region: str | None
    page: int
    size: int


@dataclass(frozen=True)
class MatchListingResult:
    """탐색 목록 한 줄. 팀 값이 **평평하게** 실린다.

    중첩 객체로 두지 않은 것은 `ApplicationResult.nickname` · 스쿼드의
    `position_label` 과 같은 판단이다 — 표시용으로 조인해 온 값은 평평하게 둔다.
    """

    id: UUID
    team_id: UUID
    team_name: str
    region: str
    sport_code: str
    played_at: datetime
    place: str
    needs: list[PositionNeedResult] = field(default_factory=list)


@dataclass(frozen=True)
class MatchSearchResult:
    """`GET /admin/users` 와 같은 페이지 형식이다 — 형식이 갈리면 클라이언트가
    페이지 처리를 두 벌 짜야 한다."""

    items: list[MatchListingResult]
    total: int
    page: int
    size: int


@dataclass(frozen=True)
class PositionNeedResult:
    position_code: str
    position_label: str
    head_count: int


@dataclass(frozen=True)
class MatchResult:
    id: UUID
    team_id: UUID
    played_at: datetime
    place: str
    needs: list[PositionNeedResult] = field(default_factory=list)
@dataclass(frozen=True)
class ApplyCommand:
    actor_id: UUID
    match_id: UUID
    # None 이면 본인이 지원한다. 값이 있으면 주장이 그 사람에게 제안한다.
    user_id: UUID | None = None


@dataclass(frozen=True)
class AcceptApplicationCommand:
    actor_id: UUID
    match_id: UUID
    application_id: UUID


@dataclass(frozen=True)
class RemoveApplicationCommand:
    """무르기(당사자)와 거절(주장)이 같은 명령이다 — 둘 다 행을 지운다."""

    actor_id: UUID
    match_id: UUID
    application_id: UUID


@dataclass(frozen=True)
class ApplicationsQuery:
    actor_id: UUID
    match_id: UUID


@dataclass(frozen=True)
class ApplicationResult:
    id: UUID
    match_id: UUID
    user_id: UUID
    nickname: str
    team_accepted_at: datetime | None
    user_accepted_at: datetime | None
    confirmed: bool
