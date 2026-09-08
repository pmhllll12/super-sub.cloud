"""billing tables

Revision ID: 98f9cbdc74f4
Revises: None — 정어진이 병합할 때 채운다 (docs/backend-work-split.md 패킷 A)
Create Date: 2026-09-08

부록 D 도메인 ⑥ 전부(`analysis_credit` · `coach` · `coach_referral`)다.

## `analysis_credit` 은 잔량 컬럼을 두지 않는다

부록 D.4 가 `analysis_credit.balance`를 파생값이라 제거한 자리다 — 잔량은
조회 시 `SUM(delta)`로 구한다. 지급은 양수, 차감은 음수 한 행이다.

## `coach` 에는 `user_id`가 없다

코치는 플랫폼 사용자가 아니라 외부 제휴자다 — 넣으면 회원 탈퇴 같은 사용자
컨텍스트의 삭제 연쇄에 코치가 걸린다(패킷 A 문서 「하지 말 것」).

## `coach_referral.fee`는 `Numeric(12, 2)`

ERD가 "수수료"라고만 적어 뒀고 정확한 정밀도를 정하지 않았다. 원화는 소수점이
없지만 수수료율(%) 계산 등에서 소수가 나올 수 있어 여유를 뒀다 — 통화 단위가
확정되면 다시 좁힐 수 있다.

## 유일 제약을 두지 않는다

`coach_referral`은 같은 사용자가 같은 코치에게 여러 번 연결을 요청할 수
있다(상담을 여러 번 받는 흐름이 자연스럽다) — `report`(신고)와 같은 판단이다.

## FK는 컨텍스트를 임포트하지 않고 테이블명 문자열로만 건다

`user`는 이 컨텍스트 소관이 아니다. 여기서는 임포트 없이 `"user.id"` 문자열로만
참조한다(`fastapi/CLAUDE.md`).

## 삭제 연쇄는 걸지 않는다

D.6이 정한 연쇄에 이 세 테이블은 들어있지 않다. 기존 관례(`ondelete` 명시 없음)를
그대로 따른다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '98f9cbdc74f4'
down_revision: Union[str, Sequence[str], None] = None  # 🔴 정어진이 채운다
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "coach",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("contact", sa.String(200), nullable=False),
    )
    op.create_table(
        "analysis_credit",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=False
        ),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "coach_referral",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=False
        ),
        sa.Column(
            "coach_id", sa.Uuid(), sa.ForeignKey("coach.id"), nullable=False
        ),
        sa.Column("fee", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("coach_referral")
    op.drop_table("analysis_credit")
    op.drop_table("coach")
