"""`team_match_request` 테이블. 부록 D 도메인 ④. `paik` 17번.

팀 대 팀 경기 신청. `match_application`(개인 지원)과 달리 상태를 **양측
시각 쌍이 아니라 단일 `status` 문자열**로 둔다 — `analysis_job.status`와
같은 판단이다. `match_application`이 시각 쌍을 쓰는 이유(어느 쪽이 먼저
시작했는지가 뜻을 가짐)가 여기는 없다: 신청은 항상 신청 팀이 먼저 걸고,
대상 팀만 답한다 — 비대칭이라 시각 하나(`responded_at`)로 충분하다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TeamMatchRequestOrm(Base):
    __tablename__ = "team_match_request"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    requester_team_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("team.id"), nullable=False
    )
    target_team_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("team.id"), nullable=False
    )
    proposed_played_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    proposed_place: Mapped[str] = mapped_column(String(120), nullable=False)
    # pending · accepted · rejected · cancelled. DB 제약을 안 거는 이유는
    # `analysis_job.status`와 같다 — 단계가 늘 때 마이그레이션이 필요 없게.
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # 수락되면 채워지는 확정 경기. `match`가 지워져도(과거 경기 정리 등) 신청
    # 이력은 남아야 하므로 SET NULL.
    match_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("match.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        # 그 팀이 보낸/받은 pending 신청을 자주 찾는다(`list_team_match_requests`·
        # 동시 확정 방지 정리) — 마이그레이션이 만든 인덱스와 이름을 맞춘다.
        Index(
            "ix_team_match_request_requester", "requester_team_id", "status"
        ),
        Index("ix_team_match_request_target", "target_team_id", "status"),
    )
