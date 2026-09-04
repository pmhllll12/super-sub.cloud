"""지원·제안 인터랙터. 판단은 전부 `domain/rules/application_rules.py` 가 한다."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.core.errors import ApiError
from app.match.application.dtos.match_dto import (
    AcceptApplicationCommand,
    ApplicationResult,
    ApplicationsQuery,
    ApplyCommand,
    RemoveApplicationCommand,
)
from app.match.application.ports.input.match_use_cases import (
    AcceptApplicationUseCase,
    ApplyToMatchUseCase,
    ListApplicationsUseCase,
    RemoveApplicationUseCase,
)
from app.match.application.ports.output.match_port import MatchPort
from app.match.application.use_cases.match_assembler import to_application_result
from app.match.domain.entities.match_entity import MatchEntity
from app.match.domain.rules.application_rules import (
    SIDE_TEAM,
    SIDE_USER,
    acceptable_side,
    can_apply,
    can_offer,
    can_remove,
    has_stake,
)
from app.match.domain.rules.match_rules import OWNER_ROLE, is_registrable


class _ApplicationBase:
    def __init__(self, repository: MatchPort) -> None:
        self._repository = repository

    def _match_or_404(self, match_id: UUID) -> MatchEntity:
        match = self._repository.find_match(match_id)
        if match is None:
            raise ApiError(404, "MATCH_NOT_FOUND", "경기를 찾을 수 없습니다.")
        return match

    def _role(self, team_id: UUID, user_id: UUID) -> str | None:
        return self._repository.team_role_of(team_id, user_id)


class ApplyToMatchInteractor(_ApplicationBase, ApplyToMatchUseCase):
    def __call__(self, command: ApplyCommand) -> ApplicationResult:
        match = self._match_or_404(command.match_id)

        # 지난 경기에는 지원할 수 없다. 등록과 같은 규칙을 쓴다.
        if not is_registrable(match.played_at, datetime.now(timezone.utc)):
            raise ApiError(422, "PAST_MATCH", "이미 지난 경기입니다.")

        target_id = command.user_id or command.actor_id
        offering = target_id != command.actor_id
        actor_role = self._role(match.team_id, command.actor_id)

        if offering:
            if not can_offer(actor_role):
                raise ApiError(403, "FORBIDDEN", "주장만 제안할 수 있습니다.")
            if not self._repository.user_exists(target_id):
                raise ApiError(404, "USER_NOT_FOUND", "사용자를 찾을 수 없습니다.")
        elif not can_apply(actor_role):
            raise ApiError(
                409, "TEAM_MEMBER_CANNOT_APPLY", "이 팀 소속은 지원할 수 없습니다."
            )

        # 제안 대상이 그 팀 소속이어도 같은 이유로 뜻이 없다.
        if offering and self._role(match.team_id, target_id) is not None:
            raise ApiError(
                409, "TEAM_MEMBER_CANNOT_APPLY", "이 팀 소속에게는 제안할 수 없습니다."
            )

        if self._repository.find_application(match.id, target_id) is not None:
            raise ApiError(409, "ALREADY_APPLIED", "이미 지원·제안된 건이 있습니다.")

        side = SIDE_TEAM if offering else SIDE_USER
        return to_application_result(
            self._repository.create_application(match.id, target_id, side)
        )


class AcceptApplicationInteractor(_ApplicationBase, AcceptApplicationUseCase):
    def __call__(self, command: AcceptApplicationCommand) -> ApplicationResult:
        match = self._match_or_404(command.match_id)
        application = self._repository.find_application_by_id(command.application_id)
        if application is None or application.match_id != match.id:
            raise ApiError(404, "APPLICATION_NOT_FOUND", "지원 건을 찾을 수 없습니다.")

        is_owner = self._role(match.team_id, command.actor_id) == OWNER_ROLE
        side = acceptable_side(application, command.actor_id, is_owner)
        if side is None:
            # 🔴 "권한 없음"과 "이미 수락함"을 가른다. 같은 에러로 내면 남의 지원
            # 건이 있는지 없는지가 응답으로 새어 나간다.
            if has_stake(application, command.actor_id, is_owner):
                raise ApiError(409, "ALREADY_ACCEPTED", "이미 수락한 건입니다.")
            raise ApiError(403, "FORBIDDEN", "이 지원 건을 수락할 수 없습니다.")

        return to_application_result(
            self._repository.accept_application(application.id, side)
        )


class RemoveApplicationInteractor(_ApplicationBase, RemoveApplicationUseCase):
    def __call__(self, command: RemoveApplicationCommand) -> None:
        match = self._match_or_404(command.match_id)
        application = self._repository.find_application_by_id(command.application_id)
        if application is None or application.match_id != match.id:
            raise ApiError(404, "APPLICATION_NOT_FOUND", "지원 건을 찾을 수 없습니다.")

        # 🔴 지난 경기의 지원은 지우지 않는다. 확정된 행(두 시각이 다 찬 것)이
        #    "누가 그 경기에 뛰었나"의 유일한 근거라, 지우면 평가(SFR-008)가
        #    대상을 잃는다. 취소도 같은 이유로 지난 경기를 막는다.
        if not is_registrable(match.played_at, datetime.now(timezone.utc)):
            raise ApiError(
                422, "PAST_MATCH", "지난 경기의 지원은 무를 수 없습니다."
            )

        is_owner = self._role(match.team_id, command.actor_id) == OWNER_ROLE
        if not can_remove(application, command.actor_id, is_owner):
            raise ApiError(403, "FORBIDDEN", "이 지원 건을 없앨 수 없습니다.")

        self._repository.delete_application(application.id)


class ListApplicationsInteractor(_ApplicationBase, ListApplicationsUseCase):
    def __call__(self, query: ApplicationsQuery) -> list[ApplicationResult]:
        match = self._match_or_404(query.match_id)
        applications = self._repository.list_applications(match.id)

        if self._role(match.team_id, query.actor_id) != OWNER_ROLE:
            # 주장이 아니면 **자기 건만** 본다. 지원자 명단은 팀의 정보다.
            applications = [
                a for a in applications if a.user_id == query.actor_id
            ]
        return [to_application_result(a) for a in applications]
