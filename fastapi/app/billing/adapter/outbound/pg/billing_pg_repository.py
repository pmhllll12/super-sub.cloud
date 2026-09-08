"""`BillingPort` 의 PostgreSQL 구현.

🔴 **`user` 를 임포트하지 않는다.** 다른 컨텍스트의 테이블이라 모듈을 가져오지
않고 **필요한 컬럼만** `table()`/`column()` 으로 읽는다(`review` 가 하는
방식과 같다).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import column, func, select, table
from sqlalchemy.orm import Session

from app.billing.adapter.outbound.orm.analysis_credit_orm import AnalysisCreditOrm
from app.billing.adapter.outbound.orm.coach_orm import CoachOrm
from app.billing.adapter.outbound.orm.coach_referral_orm import CoachReferralOrm
from app.billing.application.ports.output.billing_port import BillingPort
from app.billing.domain.entities.billing_entity import (
    CoachEntity,
    CoachReferralEntity,
    CreditEntryEntity,
)

# 소유하지 않는 테이블에서 **읽기만** 한다. 위 docstring 참조.
_user = table("user", column("id"))


class BillingPgRepository(BillingPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def credit_history(self, user_id: UUID) -> list[CreditEntryEntity]:
        rows = self._session.execute(
            select(AnalysisCreditOrm)
            .where(AnalysisCreditOrm.user_id == user_id)
            .order_by(AnalysisCreditOrm.created_at)
        ).scalars()
        return [
            CreditEntryEntity(
                id=r.id,
                user_id=r.user_id,
                delta=r.delta,
                reason=r.reason,
                created_at=r.created_at,
            )
            for r in rows
        ]

    def add_credit_entry(self, entry: CreditEntryEntity) -> None:
        self._session.add(
            AnalysisCreditOrm(
                id=entry.id,
                user_id=entry.user_id,
                delta=entry.delta,
                reason=entry.reason,
                created_at=entry.created_at,
            )
        )
        self._session.commit()

    def list_coaches(self, offset: int, limit: int) -> tuple[list[CoachEntity], int]:
        total = self._session.execute(
            select(func.count()).select_from(CoachOrm)
        ).scalar_one()
        rows = self._session.execute(
            select(CoachOrm).order_by(CoachOrm.name).offset(offset).limit(limit)
        ).scalars()
        coaches = [
            CoachEntity(id=r.id, name=r.name, contact=r.contact) for r in rows
        ]
        return coaches, total

    def get_coach(self, coach_id: UUID) -> CoachEntity | None:
        row = self._session.get(CoachOrm, coach_id)
        if row is None:
            return None
        return CoachEntity(id=row.id, name=row.name, contact=row.contact)

    def save_referral(self, referral: CoachReferralEntity) -> None:
        self._session.add(
            CoachReferralOrm(
                id=referral.id,
                user_id=referral.user_id,
                coach_id=referral.coach_id,
                fee=referral.fee,
                created_at=referral.created_at,
            )
        )
        self._session.commit()

    def user_exists(self, user_id: UUID) -> bool:
        stmt = select(_user.c.id).where(_user.c.id == user_id)
        return self._session.execute(stmt).first() is not None
