"""`user_identity` 테이블. 부록 D 도메인 ①.

외부 제공자(구글 등) 계정과 우리 사용자의 연결이다.

🔴 **이메일로 사람을 식별하지 않는다.** 제공자가 준 고유 ID(`subject`, 구글의 `sub`)
로 식별한다. 이메일은 사용자가 바꿀 수 있고, 조직 계정은 회수 후 다른 사람에게
재발급되기도 한다. 이메일을 키로 쓰면 **그 순간 남의 계정이 넘어간다.**

`provider` 를 값으로 둔 이유는 카카오·애플을 붙일 때 테이블을 늘리지 않기 위해서다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# 지금 지원하는 제공자. 값을 늘릴 때 여기부터 본다.
PROVIDER_GOOGLE = "google"


class UserIdentityOrm(Base):
    __tablename__ = "user_identity"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    # 부록 D.6 — user 가 지워지면 연결도 함께 지운다. 남으면 같은 외부 계정으로
    # 다시 가입할 때 **사라진 사용자를 가리키게 된다.**
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    # 구글의 sub 는 21자 숫자 문자열이지만 제공자마다 다르고 길이 보장도 없다.
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        # 부록 D.7 — 한 외부 계정이 두 사용자에 붙는 것을 막는다.
        UniqueConstraint("provider", "subject", name="uq_user_identity_provider_subject"),
        # 부록 D.7 — 한 사용자가 같은 제공자를 두 번 연결하지 못하게 한다.
        UniqueConstraint("user_id", "provider", name="uq_user_identity_user_provider"),
    )
