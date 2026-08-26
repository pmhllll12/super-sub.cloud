"""저장소 프로바이더.

**이 컨텍스트에서 구현을 고르는 유일한 곳이다.** 스텁은 지웠다 — 파일은
`adapter/outbound/stub/` 에 남겨 두고 테스트에서 `dependency_overrides` 로 끼운다.
계약 테스트는 DB 없이 돌아야 하기 때문이다.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.card.adapter.outbound.pg.card_pg_repository import CardPgRepository
from app.card.application.ports.output.card_port import CardPort
from app.core.database import get_session


def get_card_repository(
    session: Annotated[Session, Depends(get_session)],
) -> CardPort:
    return CardPgRepository(session)


CardRepositoryDep = Annotated[CardPort, Depends(get_card_repository)]
