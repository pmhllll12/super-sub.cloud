"""`user_title` 테이블. 부록 D 도메인 ③.

**부여된 것만 행으로 존재한다.** 미달을 `False` 로 담지 않는다 — 담는 순간
부정 표식이 된다(부록 D.5 설계 원칙). 그 원칙은 이 스키마 모양이 지킨다.

⚠️ 부록 D.3 의 `source_metric_id -> analysis_metric`(호칭 부여 근거)은 넣지 않았다.
`analysis_metric` 테이블이 아직 없고 카드 표시 경로가 쓰지 않는다. 영상·분석 도메인이
들어올 때 컬럼과 외래키를 함께 추가한다 — 그때 D.6 삭제 연쇄도 같이 걸린다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserTitleOrm(Base):
    __tablename__ = "user_title"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    # 삭제 규칙을 일부러 비워 둔다. 부록 D.6 은 **영상 삭제 연쇄**에서 user_title 을
    # 다루지만 계정 탈퇴 시의 처리는 정하지 않았다. 정해지지 않은 것을 여기서
    # 임의로 정하면 나중에 스키마와 문서가 어긋난다.
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user.id"), nullable=False
    )
    title_code: Mapped[str] = mapped_column(
        String(40), ForeignKey("title_definition.code"), nullable=False
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        # 부록 D.7 — 같은 호칭 중복 부여 방지.
        UniqueConstraint("user_id", "title_code", name="uq_user_title_user_code"),
    )
