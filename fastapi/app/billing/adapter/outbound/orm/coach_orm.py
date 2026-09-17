"""`coach` 테이블. 부록 D 도메인 ⑥ — 제휴 코치.

🔴 **`user_id`가 없다.** 코치는 플랫폼 사용자가 아니라 외부 제휴자다 —
넣으면 회원 탈퇴·로그인 같은 사용자 컨텍스트의 삭제 연쇄에 코치가 걸린다.

⚠️ 가격·소개 문장·대표 영상 같은 값은 아직 여기 없다. `www/src/lib/market.ts`
의 `Coach` 타입(자리 표시 mock)이 훨씬 풍부하지만, 그 나머지는 화면과
스키마를 맞추는 별도 범위라 미결 항목으로 남아 있다. **`sport_code`만
`paik` 14번(2026-09-16)으로 먼저 들어왔다** — 종목 필터가 화면에서 걸리게
하는 최소 컬럼이다.

`sport_code`는 `video.sport_code`·`position.sport_code`와 같은 판단으로
단일 컬럼이다(다대다 아님) — `www/src/lib/market.ts`의 `Coach.sport`가
이미 단일값으로 모델링돼 있어 코치가 여러 종목을 겸하는 경우를 다룰
근거가 없다(박민호 결정, pending `paik` 14번).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CoachOrm(Base):
    __tablename__ = "coach"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    contact: Mapped[str] = mapped_column(String(200), nullable=False)
    sport_code: Mapped[str] = mapped_column(
        String(20), ForeignKey("sport.code"), nullable=False
    )
