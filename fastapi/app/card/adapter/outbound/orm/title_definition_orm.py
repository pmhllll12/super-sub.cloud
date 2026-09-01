"""`title_definition` 테이블. 부록 D 도메인 ③.

호칭의 **종류**다. 누가 받았는지는 `user_title` 이 담는다.

`sport_code` 는 부록 D.3 대로 `sport` 를 가리키는 외래키다(2026-09-01 연결).
`sport` 는 `user` 컨텍스트에 있지만 **문자열 참조라 임포트하지 않는다** —
컨텍스트 경계 검사(`tests/test_architecture.py`)를 지키는 방식이다.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String
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
    sport_code: Mapped[str] = mapped_column(
        String(20), ForeignKey("sport.code"), nullable=False
    )
