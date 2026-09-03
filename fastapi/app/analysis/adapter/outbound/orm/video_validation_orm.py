"""`video_validation` 테이블. 부록 D 도메인 ② — SFR-001.

클립 1개의 규격 검사 결과다. 컬럼은 부록 D 의 ERD 가 정한 그대로이고 여기서
늘리지 않았다 — 해상도·프레임레이트 같은 **잰 값은 담지 않는다.** 남는 것은
판정과 사유뿐이고, 사유 문장이 그 값을 품는다("해상도가 상한을 넘습니다:
3840x2160").

🔴 **통과한 것도 행을 남긴다.** 반려만 기록하면 "아직 검사 안 한 영상"과
"통과한 영상"이 DB 에서 같아 보인다. 유일 제약이 `video_id` 하나인 것도 같은
뜻이다 — 영상당 판정은 하나다(부록 D.7).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class VideoValidationOrm(Base):
    __tablename__ = "video_validation"
    __table_args__ = (UniqueConstraint("video_id", name="uq_video_validation"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    # 영상이 지워지면 판정도 함께 지운다 — SEC-006 의 삭제 연쇄가
    # `user -> video` 에서 시작해 여기까지 내려온다.
    video_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("video.id", ondelete="CASCADE"), nullable=False
    )

    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # 통과하면 비어 있다. 길이를 제한하지 않는 이유는 사유가 사람이 읽는 문장이고
    # 항목이 늘면 길어지기 때문이다(ERD 도 text 다).
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
