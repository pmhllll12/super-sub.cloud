"""`region` 테이블. 부록 D 도메인 ①.

`match` 컨텍스트의 팀·개인 경기 조건(`paik` 18번)이 참조하는 지역 참조 데이터다.
`position`과 같은 이유로 **대리키 + 유일 제약** 패턴을 쓴다 — `sport`처럼 코드
자체를 자연키로 쓰지 않는다. `paik` 20번이 "지역을 계층으로 — 시/구를 나눠서"
달라고 요구해서 `city`·`district`를 **별도 컬럼**으로 둔다. 하나의 문자열
("서울 강남구")로 합치면 계층 비교가 문자열 파싱이 되어 깨지기 쉽다.

`team.region`(자유 문자열, 팀의 "연고지" 표시용)과는 다른 테이블이다 — 그건
정체성이고 이건 "어디서 경기하고 싶은가"라는 선호값이다. 서로 안 건드린다.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RegionOrm(Base):
    __tablename__ = "region"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    city: Mapped[str] = mapped_column(String(30), nullable=False)
    district: Mapped[str] = mapped_column(String(30), nullable=False)
    # 사람이 읽는 전체 표시("서울 강남구"). city+district에서 파생되지만,
    # 표기 관례(띄어쓰기·약칭)가 지역마다 달라 코드로 조립하지 않고 값으로 둔다.
    label: Mapped[str] = mapped_column(String(60), nullable=False)

    __table_args__ = (
        UniqueConstraint("city", "district", name="uq_region_city_district"),
    )
