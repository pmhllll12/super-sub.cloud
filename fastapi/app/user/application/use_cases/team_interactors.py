"""팀 인터랙터 넷. 권한 판단은 전부 `domain/rules/team_rules.py` 가 한다.

여기서 하는 일은 **순서**다 — 무엇을 먼저 확인하고 어떤 에러를 낼지.
"""

from __future__ import annotations

from uuid import UUID, uuid4
from datetime import datetime, timezone

from app.core.errors import ApiError
from app.user.application.dtos.team_dto import (
    CancelTeamInvitationCommand,
    CreateTeamCommand,
    CreateTeamInvitationCommand,
    JoinTeamCommand,
    LeaveTeamCommand,
    MyTeamInvitationResult,
    MyTeamInvitationsQuery,
    RespondTeamInvitationCommand,
    TeamInvitationResult,
    TeamInvitationsQuery,
    TeamQuery,
    TeamResult,
    UpdateTeamCommand,
)
from app.user.application.ports.input.team_use_cases import (
    AcceptTeamInvitationUseCase,
    CancelTeamInvitationUseCase,
    CreateTeamInvitationUseCase,
    CreateTeamUseCase,
    JoinTeamUseCase,
    LeaveTeamUseCase,
    ListMyTeamInvitationsUseCase,
    ListTeamInvitationsUseCase,
    ReadTeamUseCase,
    RejectTeamInvitationUseCase,
    UpdateTeamUseCase,
)
from app.user.application.ports.output.team_port import TeamPort
from app.user.application.use_cases.team_assembler import (
    to_my_team_invitation_result,
    to_team_invitation_result,
    to_team_result,
)
from app.user.domain.entities.team_entity import (
    TeamEntity,
    TeamInvitationEntity,
    TeamMemberEntity,
)
from app.user.domain.rules.team_invitation_rules import (
    PENDING,
    can_manage as can_manage_invitation,
    can_respond,
    is_respondable,
)
from app.user.domain.rules.team_rules import (
    can_add_member,
    can_edit_team,
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
        # 🔴 「없는 종목」과 **「지금 안 받는 종목」을 가른다**(`ho` 39번).
        # 행은 남아 있지만 루브릭이 없어 분석이 안 되는 종목이라, 여기서
        # 막지 않으면 팀은 만들어지는데 그 팀 영상은 워커가 전부 거부한다.
        if not self._repository.sport_is_active(command.sport_code):
            raise ApiError(
                422,
                "SPORT_NOT_AVAILABLE",
                "지금은 받지 않는 종목입니다.",
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


class UpdateTeamInteractor(_TeamInteractorBase, UpdateTeamUseCase):
    """팀 이름·지역을 고친다(주장만).

    지금까지 팀은 **만들 때 적은 값이 영영 고정**이었다 — 고칠 경로가
    없어서 이사하거나 오타를 내면 되돌릴 방법이 없었다. 그런데 지역은
    경기 탐색(`GET /matches?region=`)이 거르는 값이라 틀리면 그 팀이
    검색에서 안 걸린다.
    """

    def __call__(self, command: UpdateTeamCommand) -> TeamResult:
        team = self._team_or_404(command.team_id)
        members = self._repository.active_members(team.id)

        if not can_edit_team(_role_of(members, command.actor_id)):
            raise ApiError(403, "FORBIDDEN", "주장만 팀 정보를 고칠 수 있습니다.")

        updated = self._repository.update_team(
            team.id, command.name, command.region
        )
        if updated is None:
            raise ApiError(404, "TEAM_NOT_FOUND", "팀을 찾을 수 없습니다.")
        return self._result(updated)


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


def _pending_invitation_or_404(
    repository: TeamPort, invitation_id: UUID
) -> TeamInvitationEntity:
    invitation = repository.find_team_invitation(invitation_id)
    if invitation is None:
        raise ApiError(404, "TEAM_INVITATION_NOT_FOUND", "초대를 찾을 수 없습니다.")
    if not is_respondable(invitation.status):
        raise ApiError(
            409,
            "TEAM_INVITATION_ALREADY_RESPONDED",
            "이미 답이 난 초대입니다.",
        )
    return invitation


class CreateTeamInvitationInteractor(_TeamInteractorBase, CreateTeamInvitationUseCase):
    def __call__(
        self, command: CreateTeamInvitationCommand
    ) -> TeamInvitationResult:
        team = self._team_or_404(command.team_id)
        members = self._repository.active_members(team.id)

        if not can_manage_invitation(_role_of(members, command.actor_id)):
            raise ApiError(403, "FORBIDDEN", "주장만 초대할 수 있습니다.")

        if any(m.user_id == command.invited_user_id for m in members):
            raise ApiError(409, "ALREADY_MEMBER", "이미 이 팀의 구성원입니다.")

        if not self._repository.user_exists(command.invited_user_id):
            raise ApiError(404, "USER_NOT_FOUND", "사용자를 찾을 수 없습니다.")

        if (
            self._repository.find_pending_invitation(
                team.id, command.invited_user_id
            )
            is not None
        ):
            raise ApiError(
                409,
                "ALREADY_INVITED",
                "이미 이 사람에게 보낸 대기 중인 초대가 있습니다.",
            )

        position_id = position_code = position_label = None
        if command.position_code is not None:
            found = self._repository.find_position(
                team.sport_code, command.position_code
            )
            if found is None:
                # 약칭은 **종목 안에서만** 유일하다 — 농구 `C`(센터)로 축구
                # 팀에 초대하는 것은 오타지 빈 자리가 아니다.
                raise ApiError(
                    422,
                    "UNKNOWN_POSITION",
                    "이 팀 종목에 없는 포지션입니다.",
                )
            position_id, position_label = found
            position_code = command.position_code

        invitation = TeamInvitationEntity(
            id=uuid4(),
            team_id=team.id,
            invited_user_id=command.invited_user_id,
            status=PENDING,
            created_at=datetime.now(timezone.utc),
            position_id=position_id,
            position_code=position_code,
            position_label=position_label,
        )
        self._repository.create_team_invitation(invitation)
        return to_team_invitation_result(invitation)


class ListTeamInvitationsInteractor(_TeamInteractorBase, ListTeamInvitationsUseCase):
    def __call__(self, query: TeamInvitationsQuery) -> list[TeamInvitationResult]:
        """그 팀이 보낸 초대 목록, **주장만** — 누구를 초대했는지는 팀 내부 정보다."""
        team = self._team_or_404(query.team_id)
        members = self._repository.active_members(team.id)
        if not can_manage_invitation(_role_of(members, query.actor_id)):
            raise ApiError(403, "FORBIDDEN", "주장만 볼 수 있습니다.")
        return [
            to_team_invitation_result(i)
            for i in self._repository.list_team_invitations(team.id)
        ]


class ListMyTeamInvitationsInteractor(ListMyTeamInvitationsUseCase):
    def __init__(self, repository: TeamPort) -> None:
        self._repository = repository

    def __call__(
        self, query: MyTeamInvitationsQuery
    ) -> list[MyTeamInvitationResult]:
        return [
            to_my_team_invitation_result(i)
            for i in self._repository.list_my_pending_invitations(query.user_id)
        ]


class AcceptTeamInvitationInteractor(AcceptTeamInvitationUseCase):
    def __init__(self, repository: TeamPort, join_use_case: JoinTeamUseCase) -> None:
        self._repository = repository
        self._join = join_use_case

    def __call__(
        self, command: RespondTeamInvitationCommand
    ) -> TeamInvitationResult:
        invitation = _pending_invitation_or_404(
            self._repository, command.invitation_id
        )
        if not can_respond(invitation.invited_user_id, command.actor_id):
            raise ApiError(403, "FORBIDDEN", "받은 사람만 수락할 수 있습니다.")

        # 🔴 새 가입 로직을 만들지 않는다 — 기존 `JoinTeamUseCase`를 자기-가입
        # (`user_id` 생략)으로 그대로 쓴다. `can_add_member`가 "자기 자신은
        # 아무나" 이미 허용한다(`team_rules.py`). 그 사이 다른 경로로 이미
        # 소속이 됐으면(드문 동시성) `ALREADY_MEMBER`가 나는데, 그래도
        # 목표(소속)는 이미 달성된 것이라 초대는 그대로 수락 처리한다.
        try:
            self._join(
                JoinTeamCommand(actor_id=command.actor_id, team_id=invitation.team_id)
            )
        except ApiError as exc:
            if exc.code != "ALREADY_MEMBER":
                raise

        accepted = self._repository.accept_team_invitation(invitation.id)
        return to_team_invitation_result(accepted)


class RejectTeamInvitationInteractor(RejectTeamInvitationUseCase):
    def __init__(self, repository: TeamPort) -> None:
        self._repository = repository

    def __call__(
        self, command: RespondTeamInvitationCommand
    ) -> TeamInvitationResult:
        invitation = _pending_invitation_or_404(
            self._repository, command.invitation_id
        )
        if not can_respond(invitation.invited_user_id, command.actor_id):
            raise ApiError(403, "FORBIDDEN", "받은 사람만 거절할 수 있습니다.")
        rejected = self._repository.reject_team_invitation(invitation.id)
        return to_team_invitation_result(rejected)


class CancelTeamInvitationInteractor(_TeamInteractorBase, CancelTeamInvitationUseCase):
    def __call__(
        self, command: CancelTeamInvitationCommand
    ) -> TeamInvitationResult:
        invitation = _pending_invitation_or_404(
            self._repository, command.invitation_id
        )
        team = self._team_or_404(command.team_id)
        members = self._repository.active_members(team.id)
        if invitation.team_id != team.id or not can_manage_invitation(
            _role_of(members, command.actor_id)
        ):
            raise ApiError(403, "FORBIDDEN", "그 팀 주장만 무를 수 있습니다.")
        cancelled = self._repository.cancel_team_invitation(invitation.id)
        return to_team_invitation_result(cancelled)
