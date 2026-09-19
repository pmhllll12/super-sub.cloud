"""지인 신청·검색 인터랙터. 판단은 `domain/rules/user_contact_rules.py`가 한다."""

from __future__ import annotations

from app.core.errors import ApiError
from app.user.application.dtos.user_contact_dto import (
    SEARCH_LIMIT,
    AcceptContactCommand,
    ContactListResult,
    ContactResult,
    ListContactRequestsQuery,
    ListContactsQuery,
    RequestContactCommand,
    SearchUsersQuery,
    UserSearchResult,
)
from app.user.application.ports.input.user_contact_use_cases import (
    AcceptContactUseCase,
    ListContactRequestsUseCase,
    ListContactsUseCase,
    RequestContactUseCase,
    SearchUsersUseCase,
)
from app.user.application.ports.output.user_port import UserPort
from app.user.application.use_cases.user_contact_assembler import (
    to_contact_list_result,
    to_contact_result,
)
from app.user.domain.rules.user_contact_rules import can_accept, can_request


class SearchUsersInteractor(SearchUsersUseCase):
    def __init__(self, repository: UserPort) -> None:
        self._repository = repository

    def __call__(self, query: SearchUsersQuery) -> list[UserSearchResult]:
        users = self._repository.search_by_nickname(
            q=query.q, exclude_user_id=query.actor_id, limit=SEARCH_LIMIT
        )
        # 🔴 **한 번에 읽는다**(미결 `paik` 39번) — 사람마다 따로 읽으면
        #    검색 한 번에 스무 번 쿼리가 나간다. 카드가 없으면 `None` 이다.
        slugs = self._repository.card_slugs([u.id for u in users])
        return [
            UserSearchResult(
                id=u.id,
                nickname=str(u.nickname),
                card_public_slug=slugs.get(u.id),
            )
            for u in users
        ]


class RequestContactInteractor(RequestContactUseCase):
    def __init__(self, repository: UserPort) -> None:
        self._repository = repository

    def __call__(self, command: RequestContactCommand) -> ContactResult:
        if not can_request(command.requester_id, command.target_id):
            raise ApiError(
                422, "CANNOT_REQUEST_SELF", "자기 자신에게는 신청할 수 없습니다."
            )
        if self._repository.get(command.target_id) is None:
            raise ApiError(404, "USER_NOT_FOUND", "사용자를 찾을 수 없습니다.")
        if self._repository.find_contact(command.requester_id, command.target_id):
            raise ApiError(
                409, "ALREADY_REQUESTED", "이미 신청했거나 지인인 사이입니다."
            )

        note = command.note.strip() if command.note else None
        contact = self._repository.create_contact_request(
            command.requester_id, command.target_id, note
        )
        return to_contact_result(contact)


class AcceptContactInteractor(AcceptContactUseCase):
    def __init__(self, repository: UserPort) -> None:
        self._repository = repository

    def __call__(self, command: AcceptContactCommand) -> ContactResult:
        contact = self._repository.find_contact_by_id(command.contact_id)
        if contact is None:
            raise ApiError(404, "CONTACT_NOT_FOUND", "신청을 찾을 수 없습니다.")

        if not can_accept(contact, command.actor_id):
            if contact.is_accepted:
                raise ApiError(409, "ALREADY_ACCEPTED", "이미 수락한 신청입니다.")
            raise ApiError(403, "FORBIDDEN", "이 신청을 수락할 수 없습니다.")

        accepted = self._repository.accept_contact_request(contact.id)
        return to_contact_result(accepted)


class ListContactsInteractor(ListContactsUseCase):
    def __init__(self, repository: UserPort) -> None:
        self._repository = repository

    def __call__(self, query: ListContactsQuery) -> ContactListResult:
        summaries = self._repository.list_accepted_contacts(query.user_id)
        return to_contact_list_result(summaries)


class ListContactRequestsInteractor(ListContactRequestsUseCase):
    def __init__(self, repository: UserPort) -> None:
        self._repository = repository

    def __call__(self, query: ListContactRequestsQuery) -> list[ContactResult]:
        requests = self._repository.list_incoming_contact_requests(query.user_id)
        return [to_contact_result(r) for r in requests]
