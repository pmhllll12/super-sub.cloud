"""저장소 프로바이더.

**이 컨텍스트에서 구현을 고르는 유일한 곳이다.**
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.card.adapter.outbound.stub.card_stub_repository import (
    StubCardRepository,
)
from app.card.application.ports.output.card_port import CardPort


def get_card_repository() -> CardPort:
    return StubCardRepository()


CardRepositoryDep = Annotated[CardPort, Depends(get_card_repository)]
