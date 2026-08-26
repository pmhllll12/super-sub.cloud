"""`title_definition` 테이블. 부록 D 도메인 ③.

호칭의 **종류**다. 누가 받았는지는 `user_title` 이 담는다.

⚠️ 부록 D.3 에 `sport_code -> sport` 외래키가 있으나 `sport` 테이블이 아직 없어서
컬럼만 둔다. 그 도메인이 들어올 때 마이그레이션으로 제약을 건다 —
`team.sport_code` 와 같은 상태다.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TitleDefinitionOrm(Base):
    __tablename__ = "title_definition"

    # 코드가 곧 식별자다. `user_title.title_code` 가 이걸 참조한다.
    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    label: Mapped[str] = mapped_column(String(40), nullable=False)
    # 강점·활동·용병 셋. 값 객체 `TitleCategory` 가 열거형으로 고정한다 —
    # DB 에 CHECK 를 걸지 않은 이유는 분류가 늘어날 때 마이그레이션이 필요해지기
    # 때문이고, 애플리케이션이 이미 막고 있다.
    category: Mapped[str] = mapped_column(String(10), nullable=False)
    sport_code: Mapped[str] = mapped_column(String(20), nullable=False)
