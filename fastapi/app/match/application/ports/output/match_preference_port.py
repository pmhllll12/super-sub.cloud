"""경기 조건·후보 출력 포트. `paik` 18·20·21번."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.match.domain.entities.match_preference_entity import (
    CandidateFactsEntity,
    MemberPreferenceEntity,
    MemberPreferenceSummaryEntity,
    RegionFactEntity,
    SlotEntity,
    TeamPreferenceEntity,
)


class MatchPreferencePort(ABC):
    @abstractmethod
    def team_exists(self, team_id: UUID) -> bool: ...

    @abstractmethod
    def team_role(self, team_id: UUID, user_id: UUID) -> str | None:
        """그 팀에서 `user_id`의 역할. 소속이 아니면 `None`."""

    @abstractmethod
    def region_ids_exist(self, region_ids: list[UUID]) -> bool:
        """전부 실재하는 지역 id인가."""

    @abstractmethod
    def position_ids_exist(self, position_ids: list[UUID]) -> bool:
        """전부 실재하는 포지션 id인가."""

    @abstractmethod
    def set_team_preference(
        self, team_id: UUID, region_ids: list[UUID], slots: list[SlotEntity]
    ) -> TeamPreferenceEntity:
        """통째로 교체한다(PUT 의미론) — 기존 것은 지우고 다시 넣는다."""

    @abstractmethod
    def get_team_preference(self, team_id: UUID) -> TeamPreferenceEntity:
        """없으면 빈 조건(region_ids=[]·slots=[])을 돌려준다."""

    @abstractmethod
    def set_member_preference(
        self,
        user_id: UUID,
        region_ids: list[UUID],
        slots: list[SlotEntity],
        position_ids: list[UUID],
    ) -> MemberPreferenceEntity: ...

    @abstractmethod
    def get_member_preference(self, user_id: UUID) -> MemberPreferenceEntity:
        """없으면 빈 조건을 돌려준다."""

    @abstractmethod
    def list_member_preferences_for_team(
        self, team_id: UUID
    ) -> list[MemberPreferenceSummaryEntity]:
        """`paik` 21번 — 그 팀의 **현재 소속**(`left_at IS NULL`) 전원."""

    @abstractmethod
    def list_candidate_facts(
        self, team_id: UUID, formation: str | None
    ) -> list[CandidateFactsEntity]:
        """하드 필터를 통과한 후보들의 원자료 — 소프트 점수는 인터랙터가 낸다.

        하드 필터(`paik` 20번): 자기 팀 제외·`formation`이 같음(`None`이면
        우리 팀도 스쿼드가 없다는 뜻이라 빈 목록)·상대 스쿼드 로스터가 `formation`
        인원만큼 찼음·경기 조건(지역·시간)을 하나라도 등록한 팀만.
        """

    @abstractmethod
    def team_formation(self, team_id: UUID) -> str | None:
        """`squad.formation` — 스쿼드가 없으면 `None`(`paik` 9번 참고)."""

    @abstractmethod
    def resolve_regions(self, region_ids: list[UUID]) -> list[RegionFactEntity]:
        """id 목록을 (city, district)로 푼다 — 계층 비교(`paik` 20번)에 쓴다."""
