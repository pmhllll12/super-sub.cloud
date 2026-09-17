"""용병 매칭 저장소 프로바이더.

스텁은 `adapter/outbound/stub/`에 남겨 두고 테스트에서 `dependency_overrides`로
끼운다(`user_repository_provider.py`와 같은 관례).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.user.adapter.outbound.pg.mercenary_pg_repository import MercenaryPgRepository
from app.user.application.ports.output.mercenary_port import MercenaryPort


def get_mercenary_repository(
    session: Annotated[Session, Depends(get_session)],
) -> MercenaryPort:
    return MercenaryPgRepository(session)


MercenaryRepositoryDep = Annotated[MercenaryPort, Depends(get_mercenary_repository)]
