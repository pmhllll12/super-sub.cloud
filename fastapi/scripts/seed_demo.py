"""데모 계정과 카드를 DB 에 넣는다. **개발·프리뷰 전용이다.**

왜 필요한가: `/docs` 와 계약 문서가 `demo@super-sub.example` / 슬러그
`hong-gildong-4f2a` 로 성공 경로를 눌러보라고 안내한다. 저장소가 스텁에서
PostgreSQL 로 바뀌면서 그 데이터가 DB 에 없으면 **백성검 쪽 확인이 그대로 막힌다.**

**항목별로 멱등하다.** 통째로 건너뛰지 않고 없는 것만 채운다 — 사용자는 이미 있고
카드만 없는 상태(도메인이 하나씩 붙는 동안 실제로 생긴다)에서도 쓸 수 있어야 한다.

    .venv/bin/python scripts/seed_demo.py

⚠️ 운영 DB 에는 돌리지 않는다. 비밀번호가 공개된 계정이다.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timezone  # noqa: E402
from uuid import UUID, uuid4  # noqa: E402

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.card.adapter.outbound.orm.player_card_orm import PlayerCardOrm  # noqa: E402
from app.card.adapter.outbound.orm.title_definition_orm import (  # noqa: E402
    TitleDefinitionOrm,
)
from app.card.adapter.outbound.orm.user_title_orm import UserTitleOrm  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.database import engine_or_none  # noqa: E402
from app.core.password import hash_password  # noqa: E402
from app.user.adapter.outbound.orm.team_member_orm import TeamMemberOrm  # noqa: E402
from app.user.adapter.outbound.orm.team_orm import TeamOrm  # noqa: E402
from app.user.adapter.outbound.orm.user_credential_orm import (  # noqa: E402
    UserCredentialOrm,
)
from app.user.adapter.outbound.orm.user_orm import UserOrm  # noqa: E402

# 스텁이 쓰던 값과 같게 맞춘다. 그래야 스텁으로 확인하던 화면이 그대로 동작한다.
DEMO_EMAIL = "demo@super-sub.example"
DEMO_PASSWORD = "supersub2026"
DEMO_USER_ID = UUID("3f1c9d2e-0a44-4b7c-9e11-2b5d8c6a1f30")
ACTIVE_TEAM_ID = UUID("9a2e5f31-6d70-4c18-b3a9-4e82d7c05a16")
LEFT_TEAM_ID = UUID("c4d17b02-8e35-4a91-b6f2-0d38e5a7c914")
DEMO_CARD_ID = UUID("7b4d1a08-5c39-4e62-8f77-91ac3e0d4b25")
DEMO_SLUG = "hong-gildong-4f2a"

TITLES = [
    # (code, label, category, granted_at)
    # 일부러 오래된 것을 먼저 둔다 — visible_titles 가 최신순으로 뒤집는지
    # 실제 데이터로 눌러볼 수 있어야 한다.
    ("weekend_regular", "주말 개근", "활동", (2026, 8, 1, 9, 0)),
    ("sharp_shooter", "슈팅이 매서운", "강점", (2026, 8, 20, 12, 0)),
]


def _at(y: int, mo: int, d: int, h: int = 0, mi: int = 0) -> datetime:
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


def _missing(session: Session, model, pk) -> bool:
    return session.get(model, pk) is None


def seed_user(session: Session) -> list[str]:
    done = []
    if _missing(session, UserOrm, DEMO_USER_ID):
        session.add(
            UserOrm(
                id=DEMO_USER_ID,
                email=DEMO_EMAIL,
                nickname="홍길동",
                created_at=_at(2026, 7, 13, 10, 30),
            )
        )
        session.flush()   # 아래 외래키가 성립하려면 먼저 나가야 한다
        done.append("user")

    has_credential = session.execute(
        select(UserCredentialOrm.id).where(UserCredentialOrm.user_id == DEMO_USER_ID)
    ).first()
    if not has_credential:
        session.add(
            UserCredentialOrm(
                id=uuid4(),
                user_id=DEMO_USER_ID,
                password_hash=hash_password(DEMO_PASSWORD),
                updated_at=datetime.now(timezone.utc),
            )
        )
        done.append("credential")
    return done


def seed_teams(session: Session) -> list[str]:
    done = []
    for team_id, name, region in [
        (ACTIVE_TEAM_ID, "번개FC", "서울 강남"),
        (LEFT_TEAM_ID, "옛날FC", "서울 마포"),
    ]:
        if _missing(session, TeamOrm, team_id):
            session.add(
                TeamOrm(id=team_id, name=name, region=region, sport_code="futsal")
            )
            done.append(f"team:{name}")
    session.flush()

    # 나간 팀을 하나 넣어 둔다. 이게 있어야 "탈퇴한 팀은 안 보인다"를 눌러볼 수 있다.
    for team_id, joined, left in [
        (ACTIVE_TEAM_ID, _at(2026, 7, 1), None),
        (LEFT_TEAM_ID, _at(2026, 3, 1), _at(2026, 6, 30)),
    ]:
        exists = session.execute(
            select(TeamMemberOrm.id).where(
                TeamMemberOrm.team_id == team_id,
                TeamMemberOrm.user_id == DEMO_USER_ID,
            )
        ).first()
        if not exists:
            session.add(
                TeamMemberOrm(
                    id=uuid4(),
                    team_id=team_id,
                    user_id=DEMO_USER_ID,
                    role="member",
                    joined_at=joined,
                    left_at=left,
                )
            )
            done.append("membership")
    return done


def seed_card(session: Session) -> list[str]:
    done = []
    for code, label, category, _ in TITLES:
        if _missing(session, TitleDefinitionOrm, code):
            session.add(
                TitleDefinitionOrm(
                    code=code, label=label, category=category, sport_code="futsal"
                )
            )
            done.append(f"title_definition:{code}")
    session.flush()

    if _missing(session, PlayerCardOrm, DEMO_CARD_ID):
        session.add(
            PlayerCardOrm(
                id=DEMO_CARD_ID,
                user_id=DEMO_USER_ID,
                public_slug=DEMO_SLUG,
                og_image_key=f"cards/{DEMO_CARD_ID}.png",
            )
        )
        done.append("player_card")

    for code, _, _, when in TITLES:
        exists = session.execute(
            select(UserTitleOrm.id).where(
                UserTitleOrm.user_id == DEMO_USER_ID,
                UserTitleOrm.title_code == code,
            )
        ).first()
        if not exists:
            session.add(
                UserTitleOrm(
                    id=uuid4(),
                    user_id=DEMO_USER_ID,
                    title_code=code,
                    granted_at=_at(*when),
                )
            )
            done.append(f"user_title:{code}")
    return done


def main() -> int:
    if settings.app_env not in {"local", "dev"}:
        print(f"APP_ENV={settings.app_env} — 개발 환경에서만 돌린다.", file=sys.stderr)
        return 1

    engine = engine_or_none()
    if engine is None:
        print("DATABASE_URL 이 없다.", file=sys.stderr)
        return 1

    with Session(engine) as session:
        done = seed_user(session) + seed_teams(session) + seed_card(session)
        session.commit()

    if done:
        print("넣은 것: " + ", ".join(done))
    else:
        print("이미 다 있다.")
    print(f"로그인: {DEMO_EMAIL} / {DEMO_PASSWORD}   공개 카드 슬러그: {DEMO_SLUG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
