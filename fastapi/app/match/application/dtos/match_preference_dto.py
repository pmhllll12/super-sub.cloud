"""경기 조건(`paik` 18번)·후보(`paik` 20번)·팀원 조건 열람(`paik` 21번) DTO."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from uuid import UUID


@dataclass(frozen=True)
class SlotInput:
    weekday: int
    start_time: time
    end_time: time


@dataclass(frozen=True)
class SetTeamPreferenceCommand:
    actor_id: UUID
    team_id: UUID
    region_ids: list[UUID] = field(default_factory=list)
    slots: list[SlotInput] = field(default_factory=list)


@dataclass(frozen=True)
class GetTeamPreferenceQuery:
    team_id: UUID


@dataclass(frozen=True)
class TeamPreferenceResult:
    team_id: UUID
    region_ids: list[UUID]
    slots: list[SlotInput]


@dataclass(frozen=True)
class SetMemberPreferenceCommand:
    user_id: UUID
    region_ids: list[UUID] = field(default_factory=list)
    slots: list[SlotInput] = field(default_factory=list)
    position_ids: list[UUID] = field(default_factory=list)


@dataclass(frozen=True)
class GetMemberPreferenceQuery:
    user_id: UUID


@dataclass(frozen=True)
class MemberPreferenceResult:
    user_id: UUID
    region_ids: list[UUID]
    slots: list[SlotInput]
    position_ids: list[UUID]


@dataclass(frozen=True)
class ListMemberPreferencesQuery:
    """`paik` 21번 — 팀장만."""

    actor_id: UUID
    team_id: UUID


@dataclass(frozen=True)
class MemberPreferenceSummaryResult:
    user_id: UUID
    nickname: str
    region_ids: list[UUID]
    slots: list[SlotInput]
    position_ids: list[UUID]


@dataclass(frozen=True)
class ListMatchCandidatesQuery:
    """`paik` 20번 — "맞는 상대" 후보 목록."""

    actor_id: UUID
    team_id: UUID


@dataclass(frozen=True)
class MatchReasonResult:
    kind: str
    detail: str


@dataclass(frozen=True)
class MatchCandidateResult:
    team_id: UUID
    team_name: str
    region_label: str
    formation: str
    # 🔴 사실값만 — 유사도 점수는 안 준다(`paik` 20번 정상호 회신).
    # 순서는 이미 정렬돼 있다. reasons가 빈 리스트면 소프트 근거가 0개라는
    # 뜻이다 — 화면이 그걸로 구획을 나눌 수 있다.
    reasons: list[MatchReasonResult]


@dataclass(frozen=True)
class ListSquadCandidatesQuery:
    """`paik` 27번 — 빈 자리 추천 후보. `grade`가 `None`이면(또는 `"any"`)
    등급으로 좁히지 않고 실력 축 거리로 정렬만 한다 — `grade`를 직접
    골랐을 때만 그 칸으로 하드 필터한다(정상호 회신)."""

    actor_id: UUID
    team_id: UUID
    position_code: str
    grade: str | None = None


@dataclass(frozen=True)
class SquadCandidateResult:
    """🔴 사실값만 — 실력 축 거리는 정렬에만 쓰고 안 내려준다(20번과 같은
    원칙). `provisional`은 `grade`와 항상 함께 온다(26번 — 등급 문자만
    떼면 검수 전인지 알 방법이 없어진다)."""

    user_id: UUID
    nickname: str
    card_public_slug: str | None
    grade: str | None
    provisional: bool | None
    # 추천 판 카드의 불릿 한두 줄(`paik` 33번). 등급과 같은 리포트에서 왔다.
    notes: list[str] | None = None
