"""엔티티 → 지인 관련 결과 조립. `me_assembler.py`와 같은 이유로 한 곳에 둔다."""

from __future__ import annotations

from app.user.application.dtos.user_contact_dto import (
    ContactListResult,
    ContactResult,
    ContactSummaryResult,
)
from app.user.domain.entities.user_contact_entity import (
    UserContactEntity,
    UserContactSummary,
)


def to_contact_result(contact: UserContactEntity) -> ContactResult:
    return ContactResult(
        id=contact.id,
        requester_user_id=contact.requester_user_id,
        target_user_id=contact.target_user_id,
        note=contact.note,
        accepted_at=contact.accepted_at,
        created_at=contact.created_at,
    )


def to_contact_list_result(
    summaries: list[UserContactSummary],
) -> ContactListResult:
    return ContactListResult(
        items=[
            ContactSummaryResult(
                contact_id=s.contact_id,
                user_id=s.user_id,
                nickname=s.nickname,
                note=s.note,
                accepted_at=s.accepted_at,
            )
            for s in summaries
        ]
    )
