"""메모리 저장소. 계약 테스트가 DB 없이 돌기 위한 것이다."""

from __future__ import annotations

from uuid import UUID

from app.billing.application.ports.output.billing_port import BillingPort
from app.billing.domain.entities.billing_entity import (
    CoachEntity,
    CoachReferralEntity,
    CreditEntryEntity,
)

_CREDITS: dict[UUID, list[CreditEntryEntity]] = {}
_COACHES: dict[UUID, CoachEntity] = {}
_REFERRALS: list[CoachReferralEntity] = []
_USERS: set[UUID] = set()


def reset_billing() -> None:
    _CREDITS.clear()
    _COACHES.clear()
    _REFERRALS.clear()
    _USERS.clear()


def register_user(user_id: UUID) -> None:
    _USERS.add(user_id)


def register_coach(coach: CoachEntity) -> None:
    _COACHES[coach.id] = coach


def referrals_of(user_id: UUID) -> list[CoachReferralEntity]:
    return [r for r in _REFERRALS if r.user_id == user_id]


class StubBillingRepository(BillingPort):
    def credit_history(self, user_id: UUID) -> list[CreditEntryEntity]:
        return list(_CREDITS.get(user_id, []))

    def add_credit_entry(self, entry: CreditEntryEntity) -> None:
        _CREDITS.setdefault(entry.user_id, []).append(entry)
        _USERS.add(entry.user_id)

    def list_coaches(self, offset: int, limit: int) -> tuple[list[CoachEntity], int]:
        coaches = sorted(_COACHES.values(), key=lambda c: c.name)
        return coaches[offset : offset + limit], len(coaches)

    def get_coach(self, coach_id: UUID) -> CoachEntity | None:
        return _COACHES.get(coach_id)

    def save_referral(self, referral: CoachReferralEntity) -> None:
        _REFERRALS.append(referral)

    def user_exists(self, user_id: UUID) -> bool:
        return user_id in _USERS
