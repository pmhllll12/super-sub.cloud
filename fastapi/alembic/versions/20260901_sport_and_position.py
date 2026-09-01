"""sport and position

Revision ID: 7b1c4a92e5d0
Revises: 02ae7ff7d9da
Create Date: 2026-09-01

부록 D 도메인 ① 의 나머지 둘이다. `sport_code` 가 그동안 **문자열**이라 오타가
그대로 새 종목이 됐다 — 이제 외래키가 막는다.

## 종목 행은 `agent/rubrics/` 를 따른다

루브릭이 있는 종목만 분석할 수 있으므로 목록의 실물은 그쪽이다(축구·야구·농구).
그 전에 쓰던 `futsal` 은 08-28 팀 병합에서 축소되며 사라졌고, 남아 있던 데모 데이터
(`team` 2행 · `title_definition` 2행)를 `football` 로 옮긴다.

⚠️ 부록 D 본문은 아직 "풋살·야구 2행"이라고 적고 있다. 남의 문서라 고치지 않았다.

## 외래키를 **일부러 안 건 곳** 둘

| 대상 | 왜 |
|---|---|
| `metric_definition.sport_code` | 계약 문서 3-1절이 **미결**이다. A 안(`sport_code` 제거)이 채택되면 컬럼 자체가 사라지므로 지금 걸면 되돌려야 한다 |
| `team.sport_code` | **부록 D.3 의 외래키 표에 없다.** 문서에 없는 제약을 임의로 늘리지 않는다 (데이터는 일관성을 위해 함께 옮긴다) |

`position` 은 지금 **빈 테이블**이다 — 참조하는 `squad_member`·`match_position_need`
가 아직 없고 포지션 목록도 정해지지 않았다. 스키마만 준비한다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7b1c4a92e5d0'
down_revision: Union[str, Sequence[str], None] = '02ae7ff7d9da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# `agent/rubrics/` 의 파일명이 곧 종목 코드다.
_SPORTS = [
    ("football", "축구"),
    ("baseball", "야구"),
    ("basketball", "농구"),
]

# 축소 이전 표기 → 지금 표기. 데모 데이터만 해당한다.
_RETIRED = "futsal"
_REPLACEMENT = "football"


def upgrade() -> None:
    sport = op.create_table(
        "sport",
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("label", sa.String(length=40), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )
    # 외래키를 걸기 **전에** 채운다. 비어 있으면 아래 갱신이 갈 곳이 없다.
    op.bulk_insert(
        sport, [{"code": code, "label": label} for code, label in _SPORTS]
    )

    op.create_table(
        "position",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sport_code", sa.String(length=20), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("label", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(["sport_code"], ["sport.code"]),
        sa.PrimaryKeyConstraint("id"),
        # 부록 D.7 — 포지션 약칭이 종목 간 겹칠 수 있다.
        sa.UniqueConstraint("sport_code", "code", name="uq_position_sport_code"),
    )

    # 남아 있는 옛 표기를 옮긴다. 외래키를 걸기 전이어야 통과한다.
    op.execute(
        sa.text("update team set sport_code = :new where sport_code = :old").bindparams(
            new=_REPLACEMENT, old=_RETIRED
        )
    )
    op.execute(
        sa.text(
            "update title_definition set sport_code = :new where sport_code = :old"
        ).bindparams(new=_REPLACEMENT, old=_RETIRED)
    )

    # 부록 D.3 이 지정한 외래키. `metric_definition`·`team` 은 위 docstring 참고.
    op.create_foreign_key(
        "fk_video_sport_code", "video", "sport", ["sport_code"], ["code"]
    )
    op.create_foreign_key(
        "fk_title_definition_sport_code",
        "title_definition",
        "sport",
        ["sport_code"],
        ["code"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_title_definition_sport_code", "title_definition", type_="foreignkey"
    )
    op.drop_constraint("fk_video_sport_code", "video", type_="foreignkey")

    # 🔴 **옮긴 데이터는 되돌리지 않는다.** `football` 을 전부 `futsal` 로 바꾸면
    #    원래부터 `football` 이던 행까지 함께 망가진다 — 어느 것이 이 마이그레이션이
    #    옮긴 행인지 구별할 방법이 없다. 스키마만 되돌리고 데이터는 그대로 둔다.
    op.drop_table("position")
    op.drop_table("sport")
