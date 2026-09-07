"""`review` 테이블. 부록 D 도메인 ⑤ — 경기 후 상호 평가 (SFR-008).

🔴 **총점·별점 컬럼이 없다.** 평가는 선택형이라(3.4) 고른 것을 `review_selection`
에 **행으로** 담는다. 점수를 여기 두면 선택형이 아니게 되고, 나쁜 평가 하나가 줄
수 있는 피해에 상한이 없어진다.

🔴 **평가자 신뢰도도 테이블로 두지 않는다**(D.4). `review` 와 `review_selection`
을 집계하면 나오는 파생값이라 저장하면 제3정규형에 어긋난다. 가중치는 언제든 다시
계산할 수 있고, **소급 생성이 불가능한 것은 원자료뿐**이다.

⚠️ `reviewer_id` 와 `reviewee_id` 가 같은 행을 막는 제약이 없다 — 부록 D 에도
명시가 없어 스키마로 정하지 않았다(미결 `min` 2번 회신의 (3)번).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ReviewOrm(Base):
    __tablename__ = "review"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    # `match` · `user` 는 다른 컨텍스트의 테이블이라 **문자열로 참조**한다.
    match_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("match.id"), nullable=False
    )
    reviewer_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user.id"), nullable=False
    )
    reviewee_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user.id"), nullable=False
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        # 부록 D.7 — 경기당 1회 평가. **파이썬이 아니라 DB 가 막는다.**
        UniqueConstraint(
            "match_id", "reviewer_id", "reviewee_id", name="uq_review_once_per_match"
        ),
    )
