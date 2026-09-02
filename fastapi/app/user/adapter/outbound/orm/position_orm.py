"""`position` 테이블. 부록 D 도메인 ①.

종목별 포지션이다. `squad_member` · `match_position_need` 가 참조한다(부록 D.3).

🔴 **여기는 `sport` 와 설계가 반대다.** `sport` 는 코드가 곧 식별자인데 포지션은
**대리키를 두고 `(sport_code, code)` 에 유일 제약**을 건다(부록 D.7). 포지션 약칭이
종목 간 겹치기 때문이다 — 축구의 `FW` 와 농구의 `FW` 는 **다른 것**이라 하나로
합쳐지면 안 된다.

> 지표(`metric_definition`)는 정반대다. `trunk_forward_lean_deg_at_impact` 같은
> 물리량은 종목이 달라도 **같은 것**이라 나뉘면 비교가 불가능해진다. 그쪽은 코드가
> 전역 식별자여야 한다 — 계약 문서 3-1절의 미결 항목이다.

⚠️ **지금은 빈 테이블이다.** 참조하는 두 테이블(`squad_member`·`match_position_need`)
이 아직 없고 포지션 목록도 정해지지 않았다. 스쿼드·매칭 도메인이 들어올 때 채운다.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PositionOrm(Base):
    __tablename__ = "position"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    sport_code: Mapped[str] = mapped_column(
        String(20), ForeignKey("sport.code"), nullable=False
    )
    # 약칭(FW · GK 등). 종목 안에서만 유일하다.
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str] = mapped_column(String(40), nullable=False)

    __table_args__ = (
        # 부록 D.7 — 포지션 약칭이 종목 간 겹칠 수 있다.
        UniqueConstraint("sport_code", "code", name="uq_position_sport_code"),
    )
