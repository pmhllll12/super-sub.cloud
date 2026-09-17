"""`team_invitation` 테이블. 부록 D 도메인 ①. `min` 20번.

팀이 개인(용병 검색 결과 등)을 초대해 데려오는 자리다. `team_match_request`
(팀 대 팀, `match` 컨텍스트)와 상태 전이 모양(`status` 문자열 + `responded_at`
시각 하나)만 같다 — 신청은 항상 팀이 먼저 걸고 대상만 답하는 비대칭 구조라
`team_match_request_orm.py`와 같은 판단이다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TeamInvitationOrm(Base):
    __tablename__ = "team_invitation"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    team_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("team.id", ondelete="CASCADE"), nullable=False
    )
    invited_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    # pending · accepted · rejected · cancelled. DB 제약을 안 거는 이유는
    # `team_match_request.status`와 같다 — 단계가 늘 때 마이그레이션이 필요 없게.
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        # 그 팀이 보낸 pending 초대·그 사람이 받은 pending 초대를 자주 찾는다
        # (중복 초대 방지, `GET /teams/{id}/invitations`·`GET /me/invitations`).
        Index("ix_team_invitation_team", "team_id", "status"),
        Index("ix_team_invitation_invited_user", "invited_user_id", "status"),
    )
