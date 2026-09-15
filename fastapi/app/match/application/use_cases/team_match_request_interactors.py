"""팀 대 팀 경기 신청 인터랙터. `paik` 17번.

권한(주장만)은 `team_match_request_rules.can_manage`가, 상태 전이 가능 여부는
`is_respondable`가 판단한다. 실제 확정 경기 생성·알림·동시 확정 방지는
리포지토리(`accept_team_match_request`)가 한 트랜잭션에서 한다 — 여기서는
호출 전 권한·존재 확인만 한다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.core.errors import ApiError
from app.match.application.dtos.match_dto import (
    CancelTeamMatchRequestCommand,
    CreateTeamMatchRequestCommand,
    RespondTeamMatchRequestCommand,
    TeamMatchRequestResult,
    TeamMatchRequestsQuery,
)
from app.match.application.ports.input.match_use_cases import (
    AcceptTeamMatchRequestUseCase,
    CancelTeamMatchRequestUseCase,
    CreateTeamMatchRequestUseCase,
    ListTeamMatchRequestsUseCase,
    RejectTeamMatchRequestUseCase,
)
from app.match.application.ports.output.match_port import MatchPort
from app.match.application.use_cases.match_assembler import (
    to_team_match_request_result,
)
from app.match.domain.entities.match_entity import TeamMatchRequestEntity
from app.match.domain.rules.match_rules import is_registrable
from app.match.domain.rules.team_match_request_rules import (
    PENDING,
    can_manage,
    is_respondable,
)


def _require_owner(repository: MatchPort, team_id: UUID, actor_id: UUID) -> None:
    if not repository.team_exists(team_id):
        raise ApiError(404, "TEAM_NOT_FOUND", "팀을 찾을 수 없습니다.")
    if not can_manage(repository.team_role_of(team_id, actor_id)):
        raise ApiError(403, "FORBIDDEN", "주장만 할 수 있습니다.")


def _find_pending(
    repository: MatchPort, request_id: UUID
) -> TeamMatchRequestEntity:
    request = repository.find_team_match_request(request_id)
    if request is None:
        raise ApiError(
            404, "TEAM_MATCH_REQUEST_NOT_FOUND", "신청을 찾을 수 없습니다."
        )
    if not is_respondable(request.status):
        raise ApiError(
            409,
            "TEAM_MATCH_REQUEST_ALREADY_RESPONDED",
            "이미 답이 난 신청입니다.",
        )
    return request


class CreateTeamMatchRequestInteractor(CreateTeamMatchRequestUseCase):
    def __init__(self, repository: MatchPort) -> None:
        self._repository = repository

    def __call__(
        self, command: CreateTeamMatchRequestCommand
    ) -> TeamMatchRequestResult:
        if command.requester_team_id == command.target_team_id:
            raise ApiError(
                422, "CANNOT_REQUEST_SELF", "같은 팀에는 걸 수 없습니다."
            )
        _require_owner(
            self._repository, command.requester_team_id, command.actor_id
        )
        if not self._repository.team_exists(command.target_team_id):
            raise ApiError(404, "TEAM_NOT_FOUND", "상대 팀을 찾을 수 없습니다.")
        if not is_registrable(
            command.proposed_played_at, datetime.now(timezone.utc)
        ):
            raise ApiError(422, "PAST_MATCH", "지난 시각으로는 걸 수 없습니다.")

        request = TeamMatchRequestEntity(
            id=uuid4(),
            requester_team_id=command.requester_team_id,
            target_team_id=command.target_team_id,
            proposed_played_at=command.proposed_played_at,
            proposed_place=command.proposed_place,
            status=PENDING,
            created_at=datetime.now(timezone.utc),
        )
        self._repository.create_team_match_request(request)
        return to_team_match_request_result(request)


class ListTeamMatchRequestsInteractor(ListTeamMatchRequestsUseCase):
    def __init__(self, repository: MatchPort) -> None:
        self._repository = repository

    def __call__(
        self, query: TeamMatchRequestsQuery
    ) -> list[TeamMatchRequestResult]:
        """보낸 것 + 받은 것, **주장만** — 상대 전적·일정은 팀 내부 정보다."""
        _require_owner(self._repository, query.team_id, query.actor_id)
        return [
            to_team_match_request_result(r)
            for r in self._repository.list_team_match_requests(query.team_id)
        ]


class AcceptTeamMatchRequestInteractor(AcceptTeamMatchRequestUseCase):
    def __init__(self, repository: MatchPort) -> None:
        self._repository = repository

    def __call__(
        self, command: RespondTeamMatchRequestCommand
    ) -> TeamMatchRequestResult:
        request = _find_pending(self._repository, command.request_id)
        if request.target_team_id != command.team_id or not can_manage(
            self._repository.team_role_of(command.team_id, command.actor_id)
        ):
            raise ApiError(
                403, "FORBIDDEN", "대상 팀 주장만 수락할 수 있습니다."
            )
        accepted = self._repository.accept_team_match_request(request.id)
        return to_team_match_request_result(accepted)


class RejectTeamMatchRequestInteractor(RejectTeamMatchRequestUseCase):
    def __init__(self, repository: MatchPort) -> None:
        self._repository = repository

    def __call__(
        self, command: RespondTeamMatchRequestCommand
    ) -> TeamMatchRequestResult:
        request = _find_pending(self._repository, command.request_id)
        if request.target_team_id != command.team_id or not can_manage(
            self._repository.team_role_of(command.team_id, command.actor_id)
        ):
            raise ApiError(
                403, "FORBIDDEN", "대상 팀 주장만 거절할 수 있습니다."
            )
        rejected = self._repository.reject_team_match_request(request.id)
        return to_team_match_request_result(rejected)


class CancelTeamMatchRequestInteractor(CancelTeamMatchRequestUseCase):
    def __init__(self, repository: MatchPort) -> None:
        self._repository = repository

    def __call__(
        self, command: CancelTeamMatchRequestCommand
    ) -> TeamMatchRequestResult:
        request = _find_pending(self._repository, command.request_id)
        if request.requester_team_id != command.team_id or not can_manage(
            self._repository.team_role_of(command.team_id, command.actor_id)
        ):
            raise ApiError(
                403, "FORBIDDEN", "신청 팀 주장만 무를 수 있습니다."
            )
        cancelled = self._repository.cancel_team_match_request(request.id)
        return to_team_match_request_result(cancelled)
