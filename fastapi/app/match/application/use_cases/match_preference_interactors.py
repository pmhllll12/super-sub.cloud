"""경기 조건·후보 인터랙터. `paik` 18·20·21번."""

from __future__ import annotations

from app.core.errors import ApiError
from app.match.application.dtos.match_preference_dto import (
    GetMemberPreferenceQuery,
    GetTeamPreferenceQuery,
    ListMatchCandidatesQuery,
    ListMemberPreferencesQuery,
    MatchCandidateResult,
    MemberPreferenceResult,
    MemberPreferenceSummaryResult,
    SetMemberPreferenceCommand,
    SetTeamPreferenceCommand,
    TeamPreferenceResult,
)
from app.match.application.ports.input.match_preference_use_cases import (
    GetMemberPreferenceUseCase,
    GetTeamPreferenceUseCase,
    ListMatchCandidatesUseCase,
    ListMemberPreferencesUseCase,
    SetMemberPreferenceUseCase,
    SetTeamPreferenceUseCase,
)
from app.match.application.ports.output.match_preference_port import (
    MatchPreferencePort,
)
from app.match.application.use_cases.match_preference_assembler import (
    to_candidate_result,
    to_member_preference_result,
    to_member_preference_summary_result,
    to_slot_entities,
    to_team_preference_result,
)
from app.match.domain.rules.match_preference_rules import (
    OWNER_ROLE,
    is_valid_slot,
)


def _require_valid_slots(slots) -> None:
    for s in slots:
        if not is_valid_slot(s.weekday, s.start_time, s.end_time):
            raise ApiError(
                422,
                "INVALID_TIME_SLOT",
                "요일은 0~6, 시작 시각은 끝 시각보다 앞이어야 합니다.",
            )


class SetTeamPreferenceInteractor(SetTeamPreferenceUseCase):
    def __init__(self, repository: MatchPreferencePort) -> None:
        self._repository = repository

    def __call__(self, command: SetTeamPreferenceCommand) -> TeamPreferenceResult:
        if not self._repository.team_exists(command.team_id):
            raise ApiError(404, "TEAM_NOT_FOUND", "팀을 찾을 수 없습니다.")
        role = self._repository.team_role(command.team_id, command.actor_id)
        if role != OWNER_ROLE:
            raise ApiError(
                403, "FORBIDDEN", "팀 조건은 팀장만 정할 수 있습니다."
            )
        _require_valid_slots(command.slots)
        if command.region_ids and not self._repository.region_ids_exist(
            command.region_ids
        ):
            raise ApiError(422, "UNKNOWN_REGION", "존재하지 않는 지역입니다.")

        pref = self._repository.set_team_preference(
            command.team_id, command.region_ids, to_slot_entities(command.slots)
        )
        return to_team_preference_result(pref)


class GetTeamPreferenceInteractor(GetTeamPreferenceUseCase):
    def __init__(self, repository: MatchPreferencePort) -> None:
        self._repository = repository

    def __call__(self, query: GetTeamPreferenceQuery) -> TeamPreferenceResult:
        if not self._repository.team_exists(query.team_id):
            raise ApiError(404, "TEAM_NOT_FOUND", "팀을 찾을 수 없습니다.")
        return to_team_preference_result(
            self._repository.get_team_preference(query.team_id)
        )


class SetMemberPreferenceInteractor(SetMemberPreferenceUseCase):
    def __init__(self, repository: MatchPreferencePort) -> None:
        self._repository = repository

    def __call__(
        self, command: SetMemberPreferenceCommand
    ) -> MemberPreferenceResult:
        _require_valid_slots(command.slots)
        if command.region_ids and not self._repository.region_ids_exist(
            command.region_ids
        ):
            raise ApiError(422, "UNKNOWN_REGION", "존재하지 않는 지역입니다.")
        if command.position_ids and not self._repository.position_ids_exist(
            command.position_ids
        ):
            raise ApiError(422, "UNKNOWN_POSITION", "존재하지 않는 포지션입니다.")

        pref = self._repository.set_member_preference(
            command.user_id,
            command.region_ids,
            to_slot_entities(command.slots),
            command.position_ids,
        )
        return to_member_preference_result(pref)


class GetMemberPreferenceInteractor(GetMemberPreferenceUseCase):
    def __init__(self, repository: MatchPreferencePort) -> None:
        self._repository = repository

    def __call__(self, query: GetMemberPreferenceQuery) -> MemberPreferenceResult:
        return to_member_preference_result(
            self._repository.get_member_preference(query.user_id)
        )


class ListMemberPreferencesInteractor(ListMemberPreferencesUseCase):
    """`paik` 21번 — 팀장이 팀원들 조건을 본다. **남의 팀은 절대 안 된다.**"""

    def __init__(self, repository: MatchPreferencePort) -> None:
        self._repository = repository

    def __call__(
        self, query: ListMemberPreferencesQuery
    ) -> list[MemberPreferenceSummaryResult]:
        if not self._repository.team_exists(query.team_id):
            raise ApiError(404, "TEAM_NOT_FOUND", "팀을 찾을 수 없습니다.")
        role = self._repository.team_role(query.team_id, query.actor_id)
        if role != OWNER_ROLE:
            raise ApiError(
                403, "FORBIDDEN", "팀원 조건은 팀장만 볼 수 있습니다."
            )
        return [
            to_member_preference_summary_result(m)
            for m in self._repository.list_member_preferences_for_team(
                query.team_id
            )
        ]


class ListMatchCandidatesInteractor(ListMatchCandidatesUseCase):
    """`paik` 20번 — "맞는 상대" 후보. 정렬·근거는 여기(순수 로직)가 낸다,
    저장소는 원자료만 준다 — 규칙을 테스트하기 쉽게 하려는 것이다.
    """

    def __init__(self, repository: MatchPreferencePort) -> None:
        self._repository = repository

    def __call__(
        self, query: ListMatchCandidatesQuery
    ) -> list[MatchCandidateResult]:
        if not self._repository.team_exists(query.team_id):
            raise ApiError(404, "TEAM_NOT_FOUND", "팀을 찾을 수 없습니다.")
        role = self._repository.team_role(query.team_id, query.actor_id)
        if role is None:
            raise ApiError(
                403, "FORBIDDEN", "그 팀 소속만 후보를 볼 수 있습니다."
            )

        formation = self._repository.team_formation(query.team_id)
        if formation is None:
            return []

        our_pref = self._repository.get_team_preference(query.team_id)
        our_regions = self._repository.resolve_regions(our_pref.region_ids)
        facts = self._repository.list_candidate_facts(query.team_id, formation)
        return to_candidate_result(our_pref.slots, our_regions, facts)
