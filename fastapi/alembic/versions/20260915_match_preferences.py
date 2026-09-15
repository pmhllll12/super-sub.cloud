"""region + 팀/개인 경기 조건(match_preferences) — paik 18·19·20·21번

Revision ID: e7c2a9f4b1d5
Revises: d4a8e5f1c3b7
Create Date: 2026-09-15

부록 D 도메인 ①·④. `paik` 18번(경기 조건을 둘 자리가 없다)·19번(지역 목록도
서버가 줘야 한다)·20번(맞는 상대 후보 목록 — 정상호 회신이 기준)·21번(팀장이
팀원 조건을 볼 수 있어야 한다).

## `region` — 대리키 + `(city, district)` 유일 제약

`position`과 같은 패턴이다. `city`·`district`를 별도 컬럼으로 둔 이유는
`paik` 20번이 "지역을 계층으로 — 시/구를 나눠서" 요구해서다. `www/src/lib/
regions.ts`의 60개 붙박이 값을 그대로 시드한다(19번 확인 기준 — 저장값이
바뀌면 안 된다고 명시돼 있다).

## `team_match_*` / `member_match_*` — 팀 조건과 개인 조건은 절대 안 섞는다

`paik` 18번 「하지 말 것」 — 같은 사람이 팀장이면서 팀원일 수 있어 한 벌로
합치면 안 된다. 지역·요일시각은 여러 개라 jsonb/배열 대신 자식 테이블로
나눈다(제1정규형, `match_position_need`와 같은 판단). 포지션은 개인 조건에만
있다("내가 뛸 자리"는 개인 값이다).

## `판 크기`(3/5/7)는 새 컬럼을 안 둔다

이미 `squad.formation`이 있다(`paik` 9번). 여기에 또 두면 두 번째 진실이
생긴다 — 후보 목록(20번)은 `squad.formation`을 원시 쿼리로 읽어 하드 필터로
쓴다.
"""

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "e7c2a9f4b1d5"
down_revision: Union[str, Sequence[str], None] = "d4a8e5f1c3b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    region = op.create_table(
        "region",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("city", sa.String(30), nullable=False),
        sa.Column("district", sa.String(30), nullable=False),
        sa.Column("label", sa.String(60), nullable=False),
        sa.UniqueConstraint("city", "district", name="uq_region_city_district"),
    )

    op.bulk_insert(
        region,
        [
        {"id": uuid4(), "city": "서울", "district": "강남구", "label": "서울 강남구"},
        {"id": uuid4(), "city": "서울", "district": "강동구", "label": "서울 강동구"},
        {"id": uuid4(), "city": "서울", "district": "강북구", "label": "서울 강북구"},
        {"id": uuid4(), "city": "서울", "district": "강서구", "label": "서울 강서구"},
        {"id": uuid4(), "city": "서울", "district": "관악구", "label": "서울 관악구"},
        {"id": uuid4(), "city": "서울", "district": "광진구", "label": "서울 광진구"},
        {"id": uuid4(), "city": "서울", "district": "구로구", "label": "서울 구로구"},
        {"id": uuid4(), "city": "서울", "district": "금천구", "label": "서울 금천구"},
        {"id": uuid4(), "city": "서울", "district": "노원구", "label": "서울 노원구"},
        {"id": uuid4(), "city": "서울", "district": "도봉구", "label": "서울 도봉구"},
        {"id": uuid4(), "city": "서울", "district": "동대문구", "label": "서울 동대문구"},
        {"id": uuid4(), "city": "서울", "district": "동작구", "label": "서울 동작구"},
        {"id": uuid4(), "city": "서울", "district": "마포구", "label": "서울 마포구"},
        {"id": uuid4(), "city": "서울", "district": "서대문구", "label": "서울 서대문구"},
        {"id": uuid4(), "city": "서울", "district": "서초구", "label": "서울 서초구"},
        {"id": uuid4(), "city": "서울", "district": "성동구", "label": "서울 성동구"},
        {"id": uuid4(), "city": "서울", "district": "성북구", "label": "서울 성북구"},
        {"id": uuid4(), "city": "서울", "district": "송파구", "label": "서울 송파구"},
        {"id": uuid4(), "city": "서울", "district": "양천구", "label": "서울 양천구"},
        {"id": uuid4(), "city": "서울", "district": "영등포구", "label": "서울 영등포구"},
        {"id": uuid4(), "city": "서울", "district": "용산구", "label": "서울 용산구"},
        {"id": uuid4(), "city": "서울", "district": "은평구", "label": "서울 은평구"},
        {"id": uuid4(), "city": "서울", "district": "종로구", "label": "서울 종로구"},
        {"id": uuid4(), "city": "서울", "district": "중구", "label": "서울 중구"},
        {"id": uuid4(), "city": "서울", "district": "중랑구", "label": "서울 중랑구"},
        {"id": uuid4(), "city": "부산", "district": "해운대구", "label": "부산 해운대구"},
        {"id": uuid4(), "city": "부산", "district": "부산진구", "label": "부산 부산진구"},
        {"id": uuid4(), "city": "부산", "district": "동래구", "label": "부산 동래구"},
        {"id": uuid4(), "city": "대구", "district": "수성구", "label": "대구 수성구"},
        {"id": uuid4(), "city": "대구", "district": "달서구", "label": "대구 달서구"},
        {"id": uuid4(), "city": "인천", "district": "남동구", "label": "인천 남동구"},
        {"id": uuid4(), "city": "인천", "district": "연수구", "label": "인천 연수구"},
        {"id": uuid4(), "city": "인천", "district": "부평구", "label": "인천 부평구"},
        {"id": uuid4(), "city": "광주", "district": "서구", "label": "광주 서구"},
        {"id": uuid4(), "city": "광주", "district": "북구", "label": "광주 북구"},
        {"id": uuid4(), "city": "대전", "district": "유성구", "label": "대전 유성구"},
        {"id": uuid4(), "city": "대전", "district": "서구", "label": "대전 서구"},
        {"id": uuid4(), "city": "울산", "district": "남구", "label": "울산 남구"},
        {"id": uuid4(), "city": "경기", "district": "수원시", "label": "경기 수원시"},
        {"id": uuid4(), "city": "경기", "district": "성남시", "label": "경기 성남시"},
        {"id": uuid4(), "city": "경기", "district": "용인시", "label": "경기 용인시"},
        {"id": uuid4(), "city": "경기", "district": "고양시", "label": "경기 고양시"},
        {"id": uuid4(), "city": "경기", "district": "화성시", "label": "경기 화성시"},
        {"id": uuid4(), "city": "경기", "district": "부천시", "label": "경기 부천시"},
        {"id": uuid4(), "city": "경기", "district": "안양시", "label": "경기 안양시"},
        {"id": uuid4(), "city": "경기", "district": "남양주시", "label": "경기 남양주시"},
        {"id": uuid4(), "city": "경기", "district": "평택시", "label": "경기 평택시"},
        {"id": uuid4(), "city": "경기", "district": "시흥시", "label": "경기 시흥시"},
        {"id": uuid4(), "city": "경기", "district": "김포시", "label": "경기 김포시"},
        {"id": uuid4(), "city": "경기", "district": "광명시", "label": "경기 광명시"},
        {"id": uuid4(), "city": "경기", "district": "하남시", "label": "경기 하남시"},
        {"id": uuid4(), "city": "경기", "district": "의정부시", "label": "경기 의정부시"},
        {"id": uuid4(), "city": "강원", "district": "춘천시", "label": "강원 춘천시"},
        {"id": uuid4(), "city": "충북", "district": "청주시", "label": "충북 청주시"},
        {"id": uuid4(), "city": "충남", "district": "천안시", "label": "충남 천안시"},
        {"id": uuid4(), "city": "전북", "district": "전주시", "label": "전북 전주시"},
        {"id": uuid4(), "city": "전남", "district": "순천시", "label": "전남 순천시"},
        {"id": uuid4(), "city": "경북", "district": "포항시", "label": "경북 포항시"},
        {"id": uuid4(), "city": "경남", "district": "창원시", "label": "경남 창원시"},
        {"id": uuid4(), "city": "제주", "district": "제주시", "label": "제주 제주시"},
        ],
    )

    op.create_table(
        "team_match_region",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "team_id",
            sa.Uuid(),
            sa.ForeignKey("team.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "region_id", sa.Uuid(), sa.ForeignKey("region.id"), nullable=False
        ),
        sa.UniqueConstraint("team_id", "region_id", name="uq_team_match_region"),
    )

    op.create_table(
        "team_match_slot",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "team_id",
            sa.Uuid(),
            sa.ForeignKey("team.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("weekday", sa.SmallInteger(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
    )

    op.create_table(
        "member_match_region",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "region_id", sa.Uuid(), sa.ForeignKey("region.id"), nullable=False
        ),
        sa.UniqueConstraint(
            "user_id", "region_id", name="uq_member_match_region"
        ),
    )

    op.create_table(
        "member_match_slot",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("weekday", sa.SmallInteger(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
    )

    op.create_table(
        "member_match_position",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "position_id", sa.Uuid(), sa.ForeignKey("position.id"), nullable=False
        ),
        sa.UniqueConstraint(
            "user_id", "position_id", name="uq_member_match_position"
        ),
    )


def downgrade() -> None:
    op.drop_table("member_match_position")
    op.drop_table("member_match_slot")
    op.drop_table("member_match_region")
    op.drop_table("team_match_slot")
    op.drop_table("team_match_region")
    op.drop_table("region")
