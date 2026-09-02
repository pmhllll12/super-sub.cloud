"""Alembic 환경 설정.

🔴 **이 파일의 존재 이유는 아래 import 목록이다.**

`--autogenerate` 는 "코드가 아는 테이블"과 "DB 에 있는 테이블"의 차이를 마이그레이션
으로 만든다. 모델이 `Base.metadata` 에 등록되지 않으면 Alembic 은 그 테이블을
**"DB 에만 있는 것"으로 보고 `DROP TABLE` 을 생성한다.** 인접 저장소에서 실제로
13개 테이블이 삭제 후보가 된 적이 있다.

**새 ORM 을 만들면 아래에 한 줄 추가한다.** 빠뜨리면 조용히 위 상태가 된다 —
그래서 `tests/test_architecture.py` 가 `*_orm.py` 와 이 목록을 대조한다.

등록을 `app/core/database.py` 에서 하지 않는 이유: `app/core/` 는 컨텍스트를
임포트하면 안 된다(같은 테스트가 검사한다). 여기는 `app/` 밖이라 제약이 없다.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import Base, sqlalchemy_url  # noqa: E402

# --- 모델 등록 (여기 없는 테이블은 DROP 대상이 된다) ------------------------
from app.user.adapter.outbound.orm import position_orm  # noqa: E402,F401
from app.user.adapter.outbound.orm import sport_orm  # noqa: E402,F401
from app.user.adapter.outbound.orm import team_member_orm  # noqa: E402,F401
from app.user.adapter.outbound.orm import team_orm  # noqa: E402,F401
from app.user.adapter.outbound.orm import user_credential_orm  # noqa: E402,F401
from app.user.adapter.outbound.orm import user_identity_orm  # noqa: E402,F401
from app.card.adapter.outbound.orm import player_card_orm  # noqa: E402,F401
from app.card.adapter.outbound.orm import title_definition_orm  # noqa: E402,F401
from app.card.adapter.outbound.orm import user_title_orm  # noqa: E402,F401
from app.user.adapter.outbound.orm import user_orm  # noqa: E402,F401
from app.analysis.adapter.outbound.orm import analysis_job_orm  # noqa: E402,F401
from app.analysis.adapter.outbound.orm import analysis_metric_orm  # noqa: E402,F401
from app.analysis.adapter.outbound.orm import analysis_metric_value_orm  # noqa: E402,F401
from app.analysis.adapter.outbound.orm import analysis_report_orm  # noqa: E402,F401
from app.analysis.adapter.outbound.orm import metric_definition_orm  # noqa: E402,F401
from app.analysis.adapter.outbound.orm import video_orm  # noqa: E402,F401
from app.match.adapter.outbound.orm import (  # noqa: E402,F401
    match_application_orm,
)
from app.match.adapter.outbound.orm import match_orm  # noqa: E402,F401
from app.match.adapter.outbound.orm import (  # noqa: E402,F401
    match_position_need_orm,
)
# ---------------------------------------------------------------------------

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# `%` 는 configparser 의 보간 문자다. 비밀번호에 들어 있으면 여기서 죽는다.
config.set_main_option("sqlalchemy.url", sqlalchemy_url().replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
