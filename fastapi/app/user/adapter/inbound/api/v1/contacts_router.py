"""지인 신청·수락·목록 라우터. 계약 문서 3-12절. 미결 `jin` 35번.

**상호 관계다.** 신청은 한쪽이 하지만 수락되면 양쪽 다 서로를 지인 목록에서
본다 — `user_contact_entity.py` 참고.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from app.core.deps import CurrentUserId
from app.user.adapter.inbound.api.schemas.user_contact_schema import (
    ContactListResponse,
    ContactResponse,
    RequestContactSchema,
)
from app.user.application.dtos.user_contact_dto import (
    AcceptContactCommand,
    ContactResult,
    ListContactRequestsQuery,
    ListContactsQuery,
    RequestContactCommand,
)
from app.user.dependencies.accept_contact_provider import AcceptContactUseCaseDep
from app.user.dependencies.list_contacts_provider import (
    ListContactRequestsUseCaseDep,
    ListContactsUseCaseDep,
)
from app.user.dependencies.request_contact_provider import RequestContactUseCaseDep

contacts_router = APIRouter(tags=["contacts"])


@contacts_router.post(
    "/me/contacts", response_model=ContactResponse, status_code=status.HTTP_201_CREATED
)
def request_contact(
    body: RequestContactSchema,
    user_id: CurrentUserId,
    use_case: RequestContactUseCaseDep,
) -> ContactResult:
    """지인 신청을 보낸다.

    | | |
    |---|---|
    | 422 `CANNOT_REQUEST_SELF` | 자기 자신에게 신청 |
    | 404 `USER_NOT_FOUND` | 대상이 없다 |
    | 409 `ALREADY_REQUESTED` | 이미 신청했거나(방향 무관) 이미 지인이다 |
    """
    return use_case(
        RequestContactCommand(
            requester_id=user_id, target_id=body.target_user_id, note=body.note
        )
    )


@contacts_router.post(
    "/me/contacts/{contact_id}/accept", response_model=ContactResponse
)
def accept_contact(
    contact_id: UUID, user_id: CurrentUserId, use_case: AcceptContactUseCaseDep
) -> ContactResult:
    """내가 대상인 대기중 신청을 수락한다.

    | | |
    |---|---|
    | 404 `CONTACT_NOT_FOUND` | 신청이 없다 |
    | 403 `FORBIDDEN` | 내가 대상이 아니다 |
    | 409 `ALREADY_ACCEPTED` | 이미 수락됐다 |
    """
    return use_case(AcceptContactCommand(actor_id=user_id, contact_id=contact_id))


@contacts_router.get("/me/contacts", response_model=ContactListResponse)
def list_contacts(user_id: CurrentUserId, use_case: ListContactsUseCaseDep):
    """수락된 지인 목록. 내가 신청자든 대상이든 상대방이 평평하게 실린다."""
    return use_case(ListContactsQuery(user_id=user_id))


@contacts_router.get("/me/contacts/requests", response_model=list[ContactResponse])
def list_contact_requests(
    user_id: CurrentUserId, use_case: ListContactRequestsUseCaseDep
):
    """나에게 온, 아직 수락하지 않은 신청 목록."""
    return use_case(ListContactRequestsQuery(user_id=user_id))
