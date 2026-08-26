"""`player_card` 테이블. 부록 D 도메인 ③.

🔴 **능력치 컬럼이 없다.** 수치는 `analysis_metric_value` 에만 있고 리포트 경로로만
나간다(부록 D.5 — 수치 비노출). **여기에 점수 컬럼을 추가하는 순간 그 원칙이 깨진다.**
`tests/card/domain/test_card_rules.py` 가 엔티티 쪽에서 같은 것을 막는다.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PlayerCardOrm(Base):
    __tablename__ = "player_card"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user.id"), nullable=False
    )
    # 공개 조회는 이것으로만 받는다. 내부 id 를 밖에 내보내지 않기 위해서다(SFR-009).
    public_slug: Mapped[str] = mapped_column(String(80), nullable=False)
    og_image_key: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (
        # 부록 D.7 — 사용자당 카드 1건, 슬러그 중복 방지.
        UniqueConstraint("user_id", name="uq_player_card_user"),
        UniqueConstraint("public_slug", name="uq_player_card_slug"),
    )
