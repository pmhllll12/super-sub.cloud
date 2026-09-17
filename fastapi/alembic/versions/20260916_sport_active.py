"""sport.active — ho 39번

Revision ID: c5a81d0e6b73
Revises: b3e7c92f5a14
Create Date: 2026-09-16

부록 D 도메인 ①. 에이전트가 **축구 단일 종목으로 정리**되면서(`ho` 39번)
야구·농구 루브릭이 사라졌다. 그런데 `sport` 행을 지울 수는 없다 — 이미 그
종목으로 올라간 영상이 참조하고 있다(2026-09-16 실측: `video` 에 야구 165건).
지우면 그 행들이 참조를 잃는다.

## 지우는 대신 내린다

`active=false` 는 **"지금 새로 받지 않는다"**는 뜻이지 "없다"가 아니다.

| | |
|---|---|
| 막는 것 | 팀 만들기(`POST /teams`) · 영상 등록(`POST /videos`) — 새 행이 생기는 자리 |
| 안 막는 것 | `GET /positions` · 경기 목록 · 코치 목록의 종목 거르기 — **과거 데이터를 계속 볼 수 있어야 한다** |

화면 쪽은 백성검이 이미 2026-09-14에 축구 하나로 좁혔다(`www/src/lib/sports.ts`).
이 마이그레이션은 **API 로 직접 오는 경로**(다른 클라이언트·`flutter` 목업)를
막는다 — 지금은 등록이 통과한 뒤 워커에서 「루브릭 없음」으로 거부돼서,
사용자에게는 고를 수 있어 보이는데 나중에 실패한다.

## 되살릴 때

🔴 **이름표만 되살리지 않는다**(`ho` 39번의 「하지 말 것」). 루브릭이
`agent/rubrics/` 에 실제로 있어야 `active=true` 로 올린다 — 안 그러면
멈추는 이유가 「지원하지 않는 종목」이 아니라 설정 실수처럼 읽힌다.

`metric_definition` 의 `grade.baseball.*`·`grade.basketball.*` 시드 행은
**그대로 둔다** — 참조가 걸려 있을 수 있고, 안 불리면 그냥 안 쓰인다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c5a81d0e6b73"
down_revision: Union[str, Sequence[str], None] = "b3e7c92f5a14"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sport",
        sa.Column(
            "active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
    )
    # 루브릭이 남아 있는 것은 축구뿐이다(`agent/rubrics/` — football_instep_shot ·
    # football_inside_pass). 나머지는 내린다.
    op.execute(
        "UPDATE sport SET active = false WHERE code NOT IN ('football')"
    )


def downgrade() -> None:
    op.drop_column("sport", "active")
