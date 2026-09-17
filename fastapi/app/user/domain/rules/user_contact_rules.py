"""지인 신청 규칙. **HTTP도 DB도 없다.**"""

from __future__ import annotations

from uuid import UUID

from app.user.domain.entities.user_contact_entity import UserContactEntity


def can_request(requester_id: UUID, target_id: UUID) -> bool:
    """자기 자신에게는 신청할 수 없다."""
    return requester_id != target_id


def can_accept(contact: UserContactEntity, actor_id: UUID) -> bool:
    """**대상만** 수락할 수 있고, 아직 대기중이어야 한다.

    신청자가 자기 신청을 스스로 수락하는 것은 뜻이 없다 — 수락은 상대가 하는
    것이다(`match_application`의 `acceptable_side`와 같은 결의 판단이지만,
    여기는 수락할 쪽이 처음부터 하나로 정해져 있어 더 단순하다).
    """
    return actor_id == contact.target_user_id and not contact.is_accepted
