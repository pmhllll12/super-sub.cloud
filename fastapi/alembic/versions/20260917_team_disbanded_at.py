"""team.disbanded_at — paik 35번 (팀 해체)

Revision ID: f1c83b0d59a4
Revises: e4a9c6d21b70
Create Date: 2026-09-17

마지막 주장이 팀을 버릴 방법이 없었다. `DELETE /teams/{id}/members/{id}` 가
`409 LAST_OWNER` 로 막는데, 그 안내("다른 주장을 먼저 세워야 합니다")가
가리키는 경로 자체가 없었다.

## 🔴 행을 지우지 않고 컬럼으로 표시하는 이유

`team` 을 참조하는 외래키가 **아홉이고 그중 다섯이 NO ACTION** 이다
(`match` 둘 · `squad` · `team_match_request` 둘 · `team_member`). 진짜
`DELETE` 를 하려면 세 컨텍스트(`user`·`card`·`match`)에 걸친 삭제 연쇄를
새로 정해야 하는데, **부록 D.6 은 팀 삭제를 정하지 않았다** —
`squad.team_id` 가 RESTRICT 인 이유가 그것이다.

그리고 이 저장소의 기존 판단이 정반대다: `team_member` 는 "탈퇴 후에도
경기·평가 이력이 남아야 하므로" `left_at` 으로 소프트 삭제한다(부록 D.6).
팀도 같다 — 지난 경기·평가가 팀 이름을 가리킨다.

## 무엇이 막히고 무엇이 남나

`sport.active`(`ho` 39번)와 **같은 판단**이다. 해체된 팀은 **새로 만드는
자리만** 막는다(가입·초대·팀 수정). 읽기와 이력은 그대로다.

해체 자체는 앱이 한다 — `disbanded_at` 을 찍고, 남은 구성원을 전부
`left_at` 으로 내보내고(그래야 `GET /me` 의 `teams` 에서 사라진다),
대기 중이던 초대·경기 신청을 `cancelled` 로 닫는다.

**앞으로 있을 경기가 있으면 해체를 막는다**(409). 상대 팀에는 약속이라
조용히 사라지면 안 되고, 경기 탐색이 다가오는 경기만 보므로 이 규칙 하나로
「없는 팀의 경기가 탐색에 뜬다」가 구조적으로 안 생긴다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f1c83b0d59a4"
down_revision: Union[str, Sequence[str], None] = "e4a9c6d21b70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "team",
        sa.Column("disbanded_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("team", "disbanded_at")
