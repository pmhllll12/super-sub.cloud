"""탈퇴 삭제 규칙 — 내 기록은 지우고, 남에게 남긴 기록은 작성자만 비운다

Revision ID: b3e8d1f07a52
Revises: a7d5e0f34c19
Create Date: 2026-09-17

## 고치는 결함

`DELETE /me` 는 `user` 행을 지우고 나머지를 외래키 `ON DELETE` 에 맡긴다. 그런데
아래 외래키가 규칙 없이(NO ACTION) 걸려 있어서, **경기에 지원했거나 평가·신고·
불참·크레딧·코치 연결·스쿼드 등재가 한 건이라도 있는 사람은 탈퇴가 DB 에서
거부됐다**(`ForeignKeyViolation`, 부록 D 재작성 중 발견 — `7abadaa`). 재현 테스트는
`tests/user/adapter/test_delete_me_db.py::TestDeleteMeWithRecords`.

## 규칙 (2026-09-17 사용자 결정 — 「내 것은 지우고 남의 것은 익명」)

| 외래키 | 규칙 | 이유 |
|---|---|---|
| `match_application.user_id` | CASCADE | 내 지원 |
| `no_show.user_id` | CASCADE | 내 불참 기록 |
| `analysis_credit.user_id` | CASCADE | 내 크레딧 이력 |
| `coach_referral.user_id` | CASCADE | 내 코치 연결 요청 |
| `squad_member.player_card_id` | CASCADE | 내 카드의 등재(카드는 이미 CASCADE) |
| `review.reviewee_id` | CASCADE | 나에 대한 평가 — 내 파생 데이터 |
| `report.target_user_id` | CASCADE | 나에 대한 신고 — 제재할 계정이 없다 |
| `review_selection.review_id` | CASCADE | 평가가 지워질 때 선택 결과가 막지 않게 |
| `review.reviewer_id` | SET NULL (NULL 허용) | 내가 남에게 쓴 평가 — 상대 신뢰 등급의 원자료 |
| `report.reporter_id` | SET NULL (NULL 허용) | 내가 한 신고 — 대상 제재의 근거 |

`reviewer_id`·`reporter_id` 는 쓸 때만 쓰고 다시 읽어 내보내는 경로가 없어 API
응답 모양은 안 바뀐다. `uq_review_once_per_match(match_id, reviewer_id, reviewee_id)`
는 NULL 끼리 같다고 보지 않으므로 익명화된 평가 여럿이 충돌하지 않는다.

🔴 **downgrade 는 NOT NULL 을 되살리므로, 그 사이 탈퇴로 작성자가 비워진 평가·
신고가 있으면 실패한다.** 되돌려야 하면 그 행을 먼저 어떻게 할지 정한다.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "b3e8d1f07a52"
down_revision: Union[str, Sequence[str], None] = "a7d5e0f34c19"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (테이블, 컬럼, 참조 테이블, 새 규칙)
_RULES = [
    ("match_application", "user_id", "user", "CASCADE"),
    ("no_show", "user_id", "user", "CASCADE"),
    ("analysis_credit", "user_id", "user", "CASCADE"),
    ("coach_referral", "user_id", "user", "CASCADE"),
    ("squad_member", "player_card_id", "player_card", "CASCADE"),
    ("review", "reviewee_id", "user", "CASCADE"),
    ("report", "target_user_id", "user", "CASCADE"),
    ("review_selection", "review_id", "review", "CASCADE"),
    ("review", "reviewer_id", "user", "SET NULL"),
    ("report", "reporter_id", "user", "SET NULL"),
]

_NULLABLE = [("review", "reviewer_id"), ("report", "reporter_id")]


def _recreate(with_rules: bool) -> None:
    for table, col, target, rule in _RULES:
        name = f"{table}_{col}_fkey"
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(
            name, table, target, [col], ["id"],
            ondelete=rule if with_rules else None,
        )


def upgrade() -> None:
    for table, col in _NULLABLE:
        op.alter_column(table, col, nullable=True)
    _recreate(with_rules=True)


def downgrade() -> None:
    _recreate(with_rules=False)
    for table, col in _NULLABLE:
        op.alter_column(table, col, nullable=False)
