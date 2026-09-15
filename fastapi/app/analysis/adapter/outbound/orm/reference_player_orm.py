"""`reference_player` 테이블. 부록 D 도메인 ②. `paik` 29번.

「선수와 비교하기」가 쓰는 고정 데모 선수 목록이다. 지금은 둘뿐이지만
`sport`·`position`·`region`과 같은 이유로 참조 테이블로 둔다 — 나중에 늘어날
때 코드 재배포 없이 행만 추가하면 된다.

🔴 **영상 파일은 안 갖는다.** `id`는 `www/src/components/analysis/
AnalysisStage.tsx`의 `COMPARE` 상수 id(`rovelli`·`castanheira`)와 그대로
맞춘다 — 화면과 서버가 같은 사람을 같은 값으로 가리켜야 나중에 이어붙이기
쉽다.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ReferencePlayerOrm(Base):
    __tablename__ = "reference_player"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    # 버킷 상대 S3 키. 예: `reports/pro/pexels-15436954/report.json`.
    report_key: Mapped[str] = mapped_column(String(1024), nullable=False)
