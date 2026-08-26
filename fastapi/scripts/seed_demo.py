"""데모 계정을 DB 에 넣는다. **개발·프리뷰 전용이다.**

왜 필요한가: `/docs` 와 계약 문서가 `demo@super-sub.example / supersub2026` 으로
성공 경로를 눌러보라고 안내한다. 저장소가 스텁에서 PostgreSQL 로 바뀌면서 그 계정이
DB 에 없으면 **백성검 쪽 확인이 그대로 막힌다.**

여러 번 돌려도 안전하다(이미 있으면 건너뛴다).

    .venv/bin/python scripts/seed_demo.py

⚠️ 운영 DB 에는 돌리지 않는다. 비밀번호가 공개된 계정이다.
"""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timezone  # noqa: E402

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

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


def _at(y: int, mo: int, d: int, h: int = 0, mi: int = 0) -> datetime:
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


def main() -> int:
    if settings.app_env not in {"local", "dev"}:
        print(f"APP_ENV={settings.app_env} — 개발 환경에서만 돌린다.", file=sys.stderr)
        return 1

    engine = engine_or_none()
    if engine is None:
        print("DATABASE_URL 이 없다.", file=sys.stderr)
        return 1

    with Session(engine) as session:
        exists = session.execute(
            select(UserOrm.id).where(UserOrm.email == DEMO_EMAIL)
        ).first()
        if exists:
            print(f"이미 있다: {DEMO_EMAIL}")
            return 0

        session.add(
            UserOrm(
                id=DEMO_USER_ID,
                email=DEMO_EMAIL,
                nickname="홍길동",
                created_at=_at(2026, 7, 13, 10, 30),
            )
        )
        session.add(TeamOrm(id=ACTIVE_TEAM_ID, name="번개FC", region="서울 강남", sport_code="futsal"))
        session.add(TeamOrm(id=LEFT_TEAM_ID, name="옛날FC", region="서울 마포", sport_code="futsal"))
        # user·team 을 먼저 내보내야 아래 외래키가 성립한다.
        session.flush()

        session.add(
            UserCredentialOrm(
                id=uuid4(),
                user_id=DEMO_USER_ID,
                password_hash=hash_password(DEMO_PASSWORD),
                updated_at=datetime.now(timezone.utc),
            )
        )
        # 나간 팀을 하나 넣어 둔다. 이게 있어야 "탈퇴한 팀은 안 보인다" 를
        # 실제 데이터로 눌러볼 수 있다.
        session.add(
            TeamMemberOrm(
                id=uuid4(), team_id=ACTIVE_TEAM_ID, user_id=DEMO_USER_ID,
                role="member", joined_at=_at(2026, 7, 1), left_at=None,
            )
        )
        session.add(
            TeamMemberOrm(
                id=uuid4(), team_id=LEFT_TEAM_ID, user_id=DEMO_USER_ID,
                role="member", joined_at=_at(2026, 3, 1), left_at=_at(2026, 6, 30),
            )
        )
        session.commit()

    print(f"넣었다: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
