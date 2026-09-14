"""player_card 에 「카드 꾸미기」(style)를 담는다

Revision ID: c4f1a6e29b73
Revises: 8a765b42e48e
Create Date: 2026-09-11

미결 `paik` 3번의 나머지. `tagline`(2026-09-04)으로 별명 한 줄만 풀었는데,
`www/`는 그새 바탕 · 로고 · 글자 색 · 글자 자리 · 붓자국까지 꾸밀 수 있는
편집기(`CardEditor.tsx`)를 만들어 두고 **이 브라우저에만**(`localStorage`)
담고 있었다 — 다른 기기에서 안 보이고 공개 카드 링크에도 안 실렸다.

## 무엇을 넣나

`player_card.style` `json` NULL — `bg`·`logo`·`text_color`·`text_x`·`text_y`·
`brush`·`brush_color`·`brush_scale`·`brush_x`·`brush_y`(`CardStyleSchema`).
`analysis_job.subject_box`·`focus`(미결 `paik` 6·8번)와 같은 판단 — 값의
구체적 형태는 화면이 정하고 서버는 형식만 검증한다.

## 사진은 왜 없나

`og_image_key`가 이미 "규칙만 있고 그 자리에 파일이 없다"인 상태다(카드
공유 미리보기 이미지). 올린 사진(`style.photo`, data URL)을 어디에 둘지도
아직 안 정해졌다 — S3 사전 서명 업로드가 필요한 별개의 작업이라 이번엔
같이 얹지 않는다. `www/`는 그동안 photo·photoScale·photoX·photoY·mode 를
계속 브라우저에만 담아 둔다(변경 없음).

## `text`(가운데 큰 글자)는 왜 여기 없나

**이미 있는 `tagline`이 같은 것이다.** `www/`가 04-09 이후 이 필드를 몰라
`style.text`를 새로 만들었는데, 기본값(`THREE LUNGS`)까지 `tagline`의 예시와
같다 — 같은 개념이 두 갈래로 갈라진 것이다. 새 컬럼을 안 만들고 `tagline`
쪽으로 합친다(`client-contract-changes.md` 35번에 프론트가 할 일을 적었다).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4f1a6e29b73'
down_revision: Union[str, Sequence[str], None] = '8a765b42e48e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("player_card", sa.Column("style", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("player_card", "style")
