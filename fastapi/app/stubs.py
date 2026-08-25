"""스텁 데이터.

DB가 아직 없다. 정어진이 09.01에 화면을 붙일 수 있도록 **고정 응답**으로 먼저 연다.
실제 조회가 붙으면 이 파일은 통째로 사라진다.

에러 경로도 눌러볼 수 있어야 하므로 성공 조건을 좁게 잡았다 — 아래 계정·슬러그만
성공하고 나머지는 계약대로 실패한다.
"""

from datetime import datetime, timezone
from uuid import UUID

from app.schemas import (
    CardOwner,
    CardResponse,
    MeResponse,
    PublicCardResponse,
    TeamMembership,
    TitleResponse,
)


def _at(y: int, mo: int, d: int, h: int = 0, mi: int = 0) -> datetime:
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


# --- 스텁이 성공으로 받아주는 값 ---------------------------------------------

DEMO_EMAIL = "demo@super-sub.example"
DEMO_PASSWORD = "supersub2026"
DEMO_SLUG = "hong-gildong-4f2a"

# 로그인이 내주는 토큰. 이 값이 아닌 Bearer 토큰은 401 로 떨어진다.
STUB_ACCESS_TOKEN = "stub-access-token-do-not-use-in-production"
TOKEN_EXPIRES_IN = 7 * 24 * 60 * 60  # 7일 (계약 문서 0장)

_USER_ID = UUID("3f1c9d2e-0a44-4b7c-9e11-2b5d8c6a1f30")
_CARD_ID = UUID("7b4d1a08-5c39-4e62-8f77-91ac3e0d4b25")
_TEAM_ID = UUID("9a2e5f31-6d70-4c18-b3a9-4e82d7c05a16")


_TITLES = [
    TitleResponse(
        code="sharp_shooter",
        label="슈팅이 매서운",
        category="강점",
        granted_at=_at(2026, 8, 20, 12, 0),
    ),
    TitleResponse(
        code="weekend_regular",
        label="주말 개근",
        category="활동",
        granted_at=_at(2026, 8, 1, 9, 0),
    ),
]

_OWNER = CardOwner(id=_USER_ID, nickname="홍길동")


def me() -> MeResponse:
    return MeResponse(
        id=_USER_ID,
        email=DEMO_EMAIL,
        nickname="홍길동",
        created_at=_at(2026, 7, 13, 10, 30),
        teams=[
            TeamMembership(
                team_id=_TEAM_ID,
                name="번개FC",
                region="서울 강남",
                sport_code="futsal",
                role="member",
                joined_at=_at(2026, 7, 1),
            )
        ],
    )


def my_card() -> CardResponse:
    return CardResponse(
        id=_CARD_ID,
        public_slug=DEMO_SLUG,
        og_image_key=f"cards/{_CARD_ID}.png",
        user=_OWNER,
        titles=_TITLES,
    )


def public_card() -> PublicCardResponse:
    return PublicCardResponse(
        public_slug=DEMO_SLUG,
        og_image_key=f"cards/{_CARD_ID}.png",
        user=_OWNER,
        titles=_TITLES,
    )
