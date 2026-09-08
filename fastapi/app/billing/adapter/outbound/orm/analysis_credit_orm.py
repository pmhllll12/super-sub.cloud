"""`analysis_credit` 테이블. 부록 D 도메인 ⑥ — 분석 크레딧 증감 이력.

🔴 **잔량 컬럼이 없다.** 지급은 양수, 차감은 음수 한 행이고 잔량은
`SUM(delta)`로 구한다 — 부록 D.4 가 `analysis_credit.balance`를 파생값이라
명시적으로 제거한 자리다. 컬럼을 두면 이력과 갈릴 수 있고, 갈리면 어느 쪽이
맞는지 알 수 없다.

⚠️ **분석 경로(`POST /videos`)와 여기서 잇지 않는다.** 그 연결은 컨텍스트
경계를 넘으므로 정어진이 붙인다(패킷 A 문서 「하지 말 것」).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AnalysisCreditOrm(Base):
    __tablename__ = "analysis_credit"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    # `user` 는 다른 컨텍스트의 테이블이라 **문자열로 참조**한다.
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("user.id"), nullable=False)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    # 값 목록(signup_bonus · analysis · refund …)은 아직 정하지 않았다 — 자유
    # 텍스트로 둔다(패킷 A 문서 「정해야 할 것」).
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
