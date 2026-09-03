"""팀 인터랙터 넷. 권한 판단은 전부 `domain/rules/team_rules.py` 가 한다.

여기서 하는 일은 **순서**다 — 무엇을 먼저 확인하고 어떤 에러를 낼지.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from app.core.errors import ApiError
from app.user.application.dtos.team_dto import (
    CreateTeamCommand,
    JoinTeamCommand,
    LeaveTeamCommand,
    TeamQuery,
    TeamResult,
)
from app.user.application.ports.input.team_use_cases import (
    CreateTeamUseCase,
    JoinTeamUseCase,
    LeaveTeamUseCase,
    ReadTeamUseCase,
)
from app.user.application.ports.output.team_port import TeamPort
from app.user.application.use_cases.team_assembler import to_team_result
from app.user.domain.entities.team_entity import TeamEntity, TeamMemberEntity
from app.user.domain.rules.team_rules import (
    can_add_member,
    can_remove_member,
    is_last_owner,
)
from app.user.domain.value_objects.team_role_vo import TeamRole


def _role_of(members: list[TeamMemberEntity], user_id: UUID) -> TeamRole | None:
    """소속이 아니면 None. 규칙 함수들이 그것을 "권한 없음"으로 읽는다."""
    return next((m.role for m in members if m.user_id == user_id), None)


class _TeamInteractorBase:
    def __init__(self, repository: TeamPort) -> None:
        self._repository = repository

    def _team_or_404(self, team_id: UUID) -> TeamEntity:
        team = self._repository.find_team(team_id)
        if team is None:
            raise ApiError(404, "TEAM_NOT_FOUND", "팀을 찾을 수 없습니다.")
        return team

    def _result(self, team: TeamEntity) -> TeamResult:
        return to_team_result(team, self._repository.active_members(team.id))


class CreateTeamInteractor(_TeamInteractorBase, CreateTeamUseCase):
    def __call__(self, command: CreateTeamCommand) -> TeamResult:
        if not self._repository.sport_exists(command.sport_code):
            raise ApiError(
                422, "UNKNOWN_SPORT", "등록되지 않은 종목 코드입니다."
            )

        team = TeamEntity(
            id=uuid4(),
            name=command.name,
            region=command.region,
            sport_code=command.sport_code,
        )
        self._repository.create_team(team, owner_id=command.actor_id)
        return self._result(team)


class ReadTeamInteractor(_TeamInteractorBase, ReadTeamUseCase):
    def __call__(self, query: TeamQuery) -> TeamResult:
        """소속이 아니어도 볼 수 있다.

        가입하려면 먼저 봐야 하고, 담기는 것은 팀 이름·지역·종목과 구성원의
        닉네임뿐이라 소속으로 막을 이유가 없다. 인증은 필요하다.
        """
        return self._result(self._team_or_404(query.team_id))


class JoinTeamInteractor(_TeamInteractorBase, JoinTeamUseCase):
    def __call__(self, command: JoinTeamCommand) -> TeamResult:
        target_id = command.user_id or command.actor_id
        adding_self = target_id == command.actor_id

        team = self._team_or_404(command.team_id)
        members = self._repository.active_members(team.id)

        if not can_add_member(_role_of(members, command.actor_id), adding_self):
            raise ApiError(403, "FORBIDDEN", "주장만 다른 사람을 넣을 수 있습니다.")

        if any(m.user_id == target_id for m in members):
            raise ApiError(409, "ALREADY_MEMBER", "이미 이 팀의 구성원입니다.")

        # 본인은 토큰으로 존재가 증명된다. 남을 넣을 때만 확인한다.
        if not adding_self and not self._repository.user_exists(target_id):
            raise ApiError(404, "USER_NOT_FOUND", "사용자를 찾을 수 없습니다.")

        self._repository.add_member(team.id, target_id)
        return self._result(team)


class LeaveTeamInteractor(_TeamInteractorBase, LeaveTeamUseCase):
    def __call__(self, command: LeaveTeamCommand) -> None:
        team = self._team_or_404(command.team_id)
        members = self._repository.active_members(team.id)

        if not any(m.user_id == command.user_id for m in members):
            raise ApiError(404, "NOT_A_MEMBER", "이 팀의 구성원이 아닙니다.")

        actor_role = _role_of(members, command.actor_id)
        if not can_remove_member(command.actor_id, command.user_id, actor_role):
            raise ApiError(403, "FORBIDDEN", "주장만 다른 사람을 뺄 수 있습니다.")

        if is_last_owner(members, command.user_id):
            raise ApiError(
                409,
                "LAST_OWNER",
                "마지막 주장은 나갈 수 없습니다. 다른 주장을 먼저 세워야 합니다.",
            )

        self._repository.mark_left(team.id, command.user_id)
