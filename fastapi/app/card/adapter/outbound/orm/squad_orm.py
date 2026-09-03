"""`squad` 테이블. 부록 D 도메인 ③.

한 팀의 카드 묶음이다. **팀의 얼굴**이라, 개인의 얼굴인 `player_card` 와 같은
모양을 갖는다 — 주인을 가리키는 외래키 하나와 공유용 슬러그 하나.

🔴 **종목이 없다.** `squad -> team -> sport_code` 로 결정된다(부록 D.4). 여기에
종목을 들이면 팀 종목과 어긋날 수 있는 두 번째 진실이 생긴다.

⚠️ **`team_id` 에 유일 제약을 걸지 않았다.** 부록 D.7 이 이 테이블에 정한 유일
제약은 `public_slug` 하나뿐이고, **ERD 에 없는 제약은 늘리지 않는다.** 다만
`squad` 에는 이름 컬럼이 없어 한 팀에 여러 개를 만들면 서로 구별할 수가 없다.
그래서 **애플리케이션이 팀당 하나로 다룬다**(생성이 멱등이다). 나중에 이름
컬럼과 함께 열면 스키마를 바꾸지 않고 여러 개를 쓸 수 있다.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SquadOrm(Base):
    __tablename__ = "squad"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    # `team` 은 `user` 컨텍스트에 있지만 **문자열 참조라 임포트하지 않는다** —
    # 컨텍스트 경계 검사(`tests/test_architecture.py`)를 지키는 방식이다.
    #
    # 삭제 규칙을 비워 둔다(기본 RESTRICT). 부록 D.6 은 팀 해체 시의 처리를
    # 정하지 않았고, 정해지지 않은 것을 여기서 임의로 정하면 나중에 스키마와
    # 문서가 어긋난다 — `user_title` 에서와 같은 판단이다.
    team_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("team.id"), nullable=False
    )

    # 공유 링크의 유일한 접근 통제다(SEC-005). 카드와 같은 96비트 난수를 쓴다.
    public_slug: Mapped[str] = mapped_column(String(40), nullable=False)

    __table_args__ = (
        # 부록 D.7 — 슬러그 중복 방지.
        UniqueConstraint("public_slug", name="uq_squad_public_slug"),
    )
