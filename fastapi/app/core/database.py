"""DB 엔진·세션과 모든 ORM 이 상속하는 `Base`.

**동기(sync) 로 간다.** 라우터·인터랙터가 전부 `def` 이고, 지금 규모에서 async 로
바꾸면 얻는 것 없이 테스트 70여 건을 전부 건드려야 한다.

🔴 **`Base` 는 프로젝트에 하나뿐이어야 한다.** Alembic 의 `--autogenerate` 는
"코드가 아는 테이블"과 "DB 에 있는 테이블"을 비교해 차이를 마이그레이션으로 만든다.
`Base` 가 둘로 갈리면 한쪽 metadata 만 넘어가고, 나머지 테이블은 **"DB 에만 있는 것"
으로 보여 `DROP TABLE` 이 생성된다.**

모델을 metadata 에 등록하는 일은 `alembic/env.py` 가 맡는다. 여기서 하지 않는 이유는
`app/core/` 가 컨텍스트를 임포트하면 안 되기 때문이다 — `tests/test_architecture.py`
가 그 방향을 검사한다. 대신 **모든 `*_orm.py` 가 `env.py` 에 등록됐는지**를
`tests/test_architecture.py` 가 따로 확인한다.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """모든 ORM 모델이 상속한다. **이 하나뿐이어야 한다.**"""


def sqlalchemy_url() -> str:
    """`postgresql://` 을 SQLAlchemy 가 쓸 드라이버 URL 로 바꾼다.

    드라이버를 안 적으면 SQLAlchemy 는 psycopg2 를 찾는다. 우리가 설치한 것은
    psycopg3 이라 `+psycopg` 를 명시해야 한다 — 안 하면 기동 시점에
    `ModuleNotFoundError: psycopg2` 로 죽는다.
    """
    url = settings.dsn
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


# `db_configured` 가 False 면 접속 대상이 없다는 뜻이라 엔진을 만들지 않는다.
# 스텁만으로 도는 지금 상태에서도 앱이 뜨게 하기 위함이다.
#: 🔴 **커넥션 풀을 명시한다** (2026-09-25, `paik`).
#:
#: SQLAlchemy 의 기본값은 `pool_size=5` · `max_overflow=10` · `pool_timeout=30`
#: 이다. 그 **30초**가 실제로 사용자에게 보였다 — 앱 홈에서 영상 줄이 통째로
#: 안 나와서 재 봤더니 `GET /videos/public` 이 **정확히 30.00초** 무응답이었고
#: (`/regions` 는 같은 순간 0.4초에 답했다), 같은 경로가 0.4초 ~ 30초로
#: 널뛰었다. 풀이 빈 채로 기다리다 그대로 시간이 다 간 것이다.
#:
#: 🔴 **빨리 실패하는 쪽이 낫다.** 30초를 기다리면 클라이언트는 「서버가
#: 죽었나」로 읽고, 그 사이 요청은 워커를 쥐고 있어 **줄이 더 길어진다.**
#: 5초면 오류로 돌아가고 사람이 다시 시킬 수 있다.
#:
#: ⚠️ **최댓값이 곧 Postgres 커넥션 수다** — `pool_size + max_overflow` 가
#: 프로세스마다 열릴 수 있는 상한이라, 워커를 늘리면 여기를 같이 본다.
_POOL_SIZE = 10
_MAX_OVERFLOW = 20
_POOL_TIMEOUT_SECONDS = 5

_engine = (
    create_engine(
        sqlalchemy_url(),
        pool_pre_ping=True,
        pool_size=_POOL_SIZE,
        max_overflow=_MAX_OVERFLOW,
        pool_timeout=_POOL_TIMEOUT_SECONDS,
        #: 오래 쉰 커넥션은 방화벽·프록시가 조용히 끊는다 — 30분마다 새로 연다.
        pool_recycle=1800,
        future=True,
    )
    if settings.db_configured
    else None
)
_SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI 의존성. 요청당 세션 하나.

    커밋은 호출하는 쪽(리포지토리)이 한다. 여기서는 **닫는 것만** 책임진다.
    """
    if _engine is None:
        from app.core.errors import ApiError

        raise ApiError(
            503, "DB_NOT_CONFIGURED", "데이터베이스 접속 정보가 설정되지 않았습니다."
        )
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


def engine_or_none():
    """부트스트랩·헬스체크용. 엔진이 없으면 None."""
    return _engine
