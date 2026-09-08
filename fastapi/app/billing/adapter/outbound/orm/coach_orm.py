"""`coach` 테이블. 부록 D 도메인 ⑥ — 제휴 코치.

🔴 **`user_id`가 없다.** 코치는 플랫폼 사용자가 아니라 외부 제휴자다 —
넣으면 회원 탈퇴·로그인 같은 사용자 컨텍스트의 삭제 연쇄에 코치가 걸린다.

⚠️ 종목·가격·소개 문장·대표 영상 같은 값은 여기 없다. `www/src/lib/market.ts`
의 `Coach` 타입(자리 표시 mock)이 훨씬 풍부하지만, 부록 D 의 `coach`는 `id`·
`name`·`contact` 셋뿐이다 — 화면과 스키마를 맞추는 것은 이번 범위 밖이고
미결 항목으로 남겨 뒀다.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CoachOrm(Base):
    __tablename__ = "coach"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    contact: Mapped[str] = mapped_column(String(200), nullable=False)
