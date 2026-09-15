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
