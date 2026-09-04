"""review trust tables

Revision ID: a3d0764cefa5
Revises: None — 정어진이 병합할 때 채운다 (docs/backend-work-split.md 패킷 B)
Create Date: 2026-09-03

부록 D 도메인 ⑤ 전부(`review` · `review_option` · `review_selection` · `report` ·
`no_show`)다. SFR-008.

## `review_option` 은 대리키를 쓰지 않는다

`position`(도메인 ③)은 같은 코드가 종목 간 겹칠 수 있어(야구 `C` = 포수, 농구
`C` = 센터) 대리키 `id` + `(sport_code, code)` 유일 제약을 썼다. `review_option`은
범위가 나뉘지 않아 그런 충돌이 없다 — ERD가 정한 대로 `code`를 그대로 기본키로
쓴다. `uuid5` 생성도 필요 없다.

## 초기 선택지 8개 — D.8이 "3.4의 피해 상한 설계와 함께 정한다"고 미뤄 둔 것

`review`는 점수를 합산하지 않고 선택형이라(3.4 · D.4), 애초에 나쁜 평가 하나가
줄 수 있는 피해에 상한이 걸려 있다 — 저장되는 것은 "무엇을 골랐다"는 사실뿐이지
누적 점수가 아니다. 그 위에서 **선택지 구성 자체**로 한 번 더 상한을 둔다:

- 매너·실력은 전부 **긍정형**이다 — 구체적인 비난을 담을 수 없다
- 부정 신호는 `caution` 두 개(포지션 불일치 · 재매칭 비선호)뿐이고, 둘 다
  **사실 진술이 아니라 선호 표현**이라 명예훼손성 서술이 들어갈 자리가 없다
- **징계성 사안(불참·괴롭힘 등)은 여기 없다** — `no_show`·`report`로 이미 분리돼
  있고(3.5 · D.5), 평가 선택지에 다시 넣으면 두 경로가 같은 것을 두 번 셈하게
  된다

| category | code | label |
|---|---|---|
| manner | manner_time | 시간을 잘 지켰다 |
| manner | manner_respect | 매너가 좋았다 |
| manner | manner_communication | 소통이 원활했다 |
| skill | skill_above_expected | 실력이 기대 이상이었다 |
| skill | skill_position_fit | 포지션 소화가 좋았다 |
| skill | skill_teamplay | 팀플레이가 좋았다 |
| repeat | repeat_yes | 다시 함께 뛰고 싶다 |
| caution | caution_position_mismatch | 포지션이 안 맞았다 |
| caution | caution_would_not_repeat | 다시 함께 뛰고 싶지 않다 |

카테고리 4개(매너·실력·재매칭 의사·주의)와 그 순서는 화면에 그대로 나갈 구성이라
바뀌면 프런트도 같이 바뀐다 — 확정 전에 박민호 님(PM)·사용자와 다시 맞춘다
(`docs/backend-work-split.md` 패킷 B 참고).

## `review_selection`은 대리키가 없다

`(review_id, option_code)` 복합 기본키 그대로다 — 대리키를 두면 같은 평가에서
같은 선택지를 두 번 담을 수 있게 된다(ERD가 명시적으로 금지).

## FK는 컨텍스트를 임포트하지 않고 테이블명 문자열로만 건다

`match`·`user`는 각각 `analysis`/이전 컨텍스트가 아니라 `match`·`user` 컨텍스트
소관이다. 여기서는 임포트 없이 `"match.id"`/`"user.id"` 문자열로만 참조한다
(`fastapi/CLAUDE.md`).

## 삭제 연쇄는 걸지 않는다

D.6이 정한 연쇄(영상 파생물 · 계정 탈퇴 시 `user_credential`/`user_identity`)에
이 다섯 테이블은 들어있지 않다. `match`의 기존 FK(예: `match.team_id`)도 명시적
`ondelete`가 없으므로 그 관례를 그대로 따른다 — 여기서 새로 정하지 않는다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a3d0764cefa5'
down_revision: Union[str, Sequence[str], None] = "d52e8f1a6b34"  # 정어진이 병합하며 이었다 (2026-09-04)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (category, code, label). 순서가 화면 노출 순서다.
_REVIEW_OPTIONS = [
    ("manner", "manner_time", "시간을 잘 지켰다"),
    ("manner", "manner_respect", "매너가 좋았다"),
    ("manner", "manner_communication", "소통이 원활했다"),
    ("skill", "skill_above_expected", "실력이 기대 이상이었다"),
    ("skill", "skill_position_fit", "포지션 소화가 좋았다"),
    ("skill", "skill_teamplay", "팀플레이가 좋았다"),
    ("repeat", "repeat_yes", "다시 함께 뛰고 싶다"),
    ("caution", "caution_position_mismatch", "포지션이 안 맞았다"),
    ("caution", "caution_would_not_repeat", "다시 함께 뛰고 싶지 않다"),
]


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "review_option",
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("label", sa.String(length=60), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )

    op.create_table(
        "review",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("match_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=False),
        sa.Column("reviewee_id", sa.Uuid(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["match.id"]),
        sa.ForeignKeyConstraint(["reviewer_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["reviewee_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "match_id", "reviewer_id", "reviewee_id", name="uq_review_once_per_match"
        ),
    )

    op.create_table(
        "review_selection",
        sa.Column("review_id", sa.Uuid(), nullable=False),
        sa.Column("option_code", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(["review_id"], ["review.id"]),
        sa.ForeignKeyConstraint(["option_code"], ["review_option.code"]),
        sa.PrimaryKeyConstraint("review_id", "option_code"),
    )

    op.create_table(
        "report",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reporter_id", sa.Uuid(), nullable=False),
        sa.Column("target_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["reporter_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["target_user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "no_show",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("match_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["match.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("match_id", "user_id", name="uq_no_show_once_per_match"),
    )

    review_option = sa.table(
        "review_option",
        sa.column("code", sa.String),
        sa.column("category", sa.String),
        sa.column("label", sa.String),
    )
    op.bulk_insert(
        review_option,
        [
            {"code": code, "category": category, "label": label}
            for category, code, label in _REVIEW_OPTIONS
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("no_show")
    op.drop_table("report")
    op.drop_table("review_selection")
    op.drop_table("review")
    op.drop_table("review_option")
