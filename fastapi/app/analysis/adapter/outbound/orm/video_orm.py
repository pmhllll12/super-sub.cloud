"""`video` 테이블. 부록 D 도메인 ② — SFR-001.

업로드된 클립 1개다. **파일 자체는 여기에 없다.** 객체 저장소의 키만 들고 있다
(PER-002 — 업로드·재생이 앱 서버를 경유하지 않는다).

⚠️ **저장소가 아직 정해지지 않았다**(5장 ASM-003). `storage_key` 는 어느 저장소를
쓰든 바뀌지 않는 부분이라 지금 확정할 수 있고, 버킷·리전 같은 접속 정보는 설정으로
빠진다. 저장소가 정해져도 이 컬럼은 그대로다.

`sport_code` 는 부록 D.3 대로 `sport` 를 가리키는 외래키다(2026-09-01 연결).
그전에는 문자열이라 오타가 그대로 새 종목이 됐다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class VideoOrm(Base):
    __tablename__ = "video"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    # 업로더(부록 D.3). SEC-006 의 삭제 연쇄가 여기서 시작한다.
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    # `sport` 는 `user` 컨텍스트에 있지만 **문자열 참조라 임포트하지 않는다** —
    # 컨텍스트 경계 검사(`tests/test_architecture.py`)를 지키는 방식이다.
    sport_code: Mapped[str] = mapped_column(
        String(20), ForeignKey("sport.code"), nullable=False
    )

    # 객체 저장소 키. 원본은 앱 서버를 지나지 않는다(PER-002).
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)

    # 던지는 팔·차는 발. **자동 판별이 팔 종목에서 신뢰할 수 없어**(5장 CON-007)
    # 업로드할 때 사람이 지정할 수 있게 열어 둔다. 비어 있으면 자동 판별을 쓴다.
    side: Mapped[str | None] = mapped_column(String(5), nullable=True)

    # 공개 여부(미결 `paik` 5번). 🔴 기본은 비공개 — 이미 올라간 클립이 남에게
    # 보이면 안 된다. 홈의 영상 모음은 `is_public` 인 클립만 훑는다.
    is_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )

    # 홈 영상 모음이 큰 글자로 얹는 값(미결 `paik` 5번). 안 정한 클립은 NULL —
    # "안 정했다"와 "지웠다"를 구별할 필요가 없다.
    title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(String(280), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
