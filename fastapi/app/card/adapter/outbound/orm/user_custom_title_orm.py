"""`user_custom_title` 테이블. 부록 D 도메인 ③. `paik` 36번.

**사람이 직접 적는 호칭**이다. `user_title`(분석·활동이 부여하는 것)과 **다른
테이블인 이유**: 저쪽은 `title_definition` 의 코드만 받는데(정의 테이블 참조),
이건 자유 문자열이다. 같은 테이블에 섞으면 `title_code` 를 nullable 로 풀어야
하고, 그 순간 "부여된 것만 행으로 존재한다"는 `user_title` 의 뜻이 흐려진다.

🔴 **`title_definition` 에 행을 늘리는 방식은 쓰지 않는다**(`paik` 36번의
「하지 말 것」) — 사람마다 다른 문장이라 정의 테이블이 사용자 수만큼 불어난다.

개수 상한(3개)은 **앱이 막는다**(`card_rules.normalize_custom_titles`).
DB 제약으로 걸지 않은 이유는 `title_definition.category` 와 같다 — 상한이
바뀔 때 마이그레이션이 필요해진다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserCustomTitleOrm(Base):
    __tablename__ = "user_custom_title"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    # 카드 한 줄과 같은 20자. **자르지 않고 거부한다**(`normalize_tagline` 과
    # 같은 판단) — 조용히 자르면 쓴 것과 보이는 것이 달라진다.
    label: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        # 카드를 그릴 때마다 그 사람 것을 통째로 읽는다.
        Index("ix_user_custom_title_user", "user_id"),
    )
