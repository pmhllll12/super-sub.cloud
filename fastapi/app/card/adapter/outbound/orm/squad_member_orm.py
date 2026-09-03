"""`squad_member` 테이블. 부록 D 도메인 ③.

스쿼드 1개에 등재된 카드 1장이다. **사람이 아니라 카드를 담는다** — 스쿼드는
카드 묶음이고(부록 D 의 용도 설명), 카드가 곧 그 사람의 공개된 얼굴이다.

`position_id` 로 저장하는 이유는 약칭이 **종목 안에서만 유일**하기 때문이다
(야구 `C` 는 포수, 농구 `C` 는 센터). 코드로 저장하면 종목을 함께 들고 다녀야 한다 —
`match_position_need` 와 같은 판단이다.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SquadMemberOrm(Base):
    __tablename__ = "squad_member"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    # 스쿼드가 사라지면 등재도 함께 사라진다 — 등재는 스쿼드 안에서만 뜻이 있다.
    squad_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("squad.id", ondelete="CASCADE"), nullable=False
    )
    # 🔴 카드 삭제 규칙은 비워 둔다(기본 RESTRICT). 부록 D.6 의 삭제 연쇄가
    #    `player_card` 까지는 다루지만 스쿼드 등재를 어떻게 할지는 정하지 않았다.
    #    **탈퇴한 사람의 등재를 지울지 익명으로 남길지**가 정해지면 그때 건다.
    player_card_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("player_card.id"), nullable=False
    )
    # `position` 은 `user` 컨텍스트에 있지만 문자열 참조라 임포트하지 않는다.
    position_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("position.id"), nullable=False
    )

    __table_args__ = (
        # 부록 D.7 — 스쿼드당 카드 1회 등재.
        UniqueConstraint("squad_id", "player_card_id", name="uq_squad_member"),
    )
