"""match tables

Revision ID: 3b93fe12219a
Revises: 7b1c4a92e5d0
Create Date: 2026-09-02

부록 D 도메인 ④ 의 앞 둘이다 (`match` · `match_position_need`). 나머지
(`match_application` · `fitness_score` · `recommendation`)는 지원·적합도·추천이라
경기 등록과 별개 단계다.

## `match` 에 종목 컬럼을 두지 않는다

`match -> team -> sport_code` 로 결정된다. 부록 D.4 가 이것을 **"중복이자 모순
가능성"** 으로 명시해 두었다 — 컬럼을 두면 팀 종목과 어긋날 수 있는 두 번째 진실이
생긴다.

## `position` 을 여기서 채운다

08-31 에 `position` 을 만들 때 **빈 테이블로 두고** "참조하는 쪽이 들어올 때 채운다"
고 적어 두었다. `match_position_need` 가 그 참조라 지금이 그때다.

넣는 값은 **종목별 기본 포지션**이고 확정된 목록이 아니다. 스쿼드(`squad_member`)가
들어올 때 세분화가 필요하면 그때 늘린다 — 지금 세분화하면 쓰지도 않는 행이 는다.

  football     GK DF MF FW
  baseball     P C IF OF
  basketball   G F C

🔴 **야구의 `C`(포수)와 농구의 `C`(센터)가 여기서 실제로 겹친다.** `position` 이
코드가 아니라 대리키를 쓰고 `(sport_code, code)` 에 유일 제약을 거는 이유가
이것이다(부록 D.7). 축구의 `FW` 와 농구의 포워드도 같은 사정이다.

id 는 `uuid5` 로 만든다. 같은 코드는 어디서 돌려도 같은 id 라, 환경마다 값이 갈리지
않고 downgrade 뒤 다시 upgrade 해도 참조가 유지된다.
"""
from typing import Sequence, Union
from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '3b93fe12219a'
down_revision: Union[str, Sequence[str], None] = '7b1c4a92e5d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (종목, 약칭, 이름). 종목 안에서만 약칭이 유일하다.
_POSITIONS = [
    ("football", "GK", "골키퍼"),
    ("football", "DF", "수비수"),
    ("football", "MF", "미드필더"),
    ("football", "FW", "공격수"),
    ("baseball", "P", "투수"),
    ("baseball", "C", "포수"),
    ("baseball", "IF", "내야수"),
    ("baseball", "OF", "외야수"),
    ("basketball", "G", "가드"),
    ("basketball", "F", "포워드"),
    ("basketball", "C", "센터"),
]


def _position_id(sport_code: str, code: str):
    """어디서 돌려도 같은 id. 환경마다 값이 갈리면 참조를 옮길 수 없다."""
    return uuid5(NAMESPACE_URL, f"supersub:position:{sport_code}:{code}")


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "match",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("played_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("place", sa.String(length=120), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["team.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "match_position_need",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("match_id", sa.Uuid(), nullable=False),
        sa.Column("position_id", sa.Uuid(), nullable=False),
        sa.Column("head_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["match.id"]),
        sa.ForeignKeyConstraint(["position_id"], ["position.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "match_id", "position_id", name="uq_match_position_need"
        ),
    )

    position = sa.table(
        "position",
        sa.column("id", sa.Uuid),
        sa.column("sport_code", sa.String),
        sa.column("code", sa.String),
        sa.column("label", sa.String),
    )
    op.bulk_insert(
        position,
        [
            {
                "id": _position_id(sport_code, code),
                "sport_code": sport_code,
                "code": code,
                "label": label,
            }
            for sport_code, code, label in _POSITIONS
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("match_position_need")
    op.drop_table("match")
    # 이 마이그레이션이 넣은 행만 지운다. 뒤에 손으로 추가한 포지션은 남긴다.
    op.execute(
        sa.text("delete from position where id in :ids").bindparams(
            sa.bindparam(
                "ids",
                value=tuple(
                    _position_id(sport_code, code)
                    for sport_code, code, _ in _POSITIONS
                ),
                expanding=True,
            )
        )
    )
