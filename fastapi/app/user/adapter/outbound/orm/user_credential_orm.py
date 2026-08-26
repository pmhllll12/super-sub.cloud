"""`user_credential` 테이블. 부록 D 도메인 ①.

비밀번호 해시를 `user` 에 두지 않고 분리한 이유는 두 가지다(계약 문서 0장).

1. 소셜 로그인을 붙일 때 `user_identity` 를 나란히 두면 되고 `user` 는 그대로다.
2. `user` 는 거의 모든 테이블이 조인하는 허브라, 해시가 그 위에 있으면 무심코
   조회될 여지가 생긴다. 분리해 두면 자격증명 조회 경로가 로그인 하나로 좁혀진다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserCredentialOrm(Base):
    __tablename__ = "user_credential"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    # 부록 D.6 — 자격증명은 계정에 완전히 종속되며 단독으로 남을 이유가 없다.
    # 부록 D.7 — 사용자당 자격증명 1건.
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    # bcrypt 해시는 60자지만 알고리즘이 바뀔 수 있어 길이를 고정하지 않는다.
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
