"""`report` 테이블. 부록 D 도메인 ⑤ — 신고 접수.

🔴 **`review` 와 이어지지 않는다.** 제재는 평가 점수가 아니라 **별도 기록**이다
(3.5). 외래키를 걸면 두 경로가 같은 것을 두 번 세게 되고, 평가를 안 한 사람은
신고도 못 하게 된다.

`reason` 은 자유 텍스트다. 정해진 목록으로 할지는 패킷 B 문서가 「정해야 할 것」에
두었는데, 마이그레이션이 `Text` 로 낸 것을 그대로 따른다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ReportOrm(Base):
    __tablename__ = "report"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    reporter_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user.id"), nullable=False
    )
    target_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
