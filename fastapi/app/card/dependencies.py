"""이 컨텍스트의 의존성 주입.

**저장소 구현을 고르는 곳은 여기다.** DB 가 붙으면 `StubCardRepository` 를
`PgCardRepository` 로 바꾸면 되고 유스케이스·라우터는 고치지 않는다.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.card.adapter.outbound.stub_repository import StubCardRepository
from app.card.application.ports import CardRepository
from app.card.application.use_cases import MyCardUseCase, PublicCardUseCase


def get_repository() -> CardRepository:
    return StubCardRepository()


_Repo = Annotated[CardRepository, Depends(get_repository)]


def get_my_card_use_case(repo: _Repo) -> MyCardUseCase:
    return MyCardUseCase(repo)


def get_public_card_use_case(repo: _Repo) -> PublicCardUseCase:
    return PublicCardUseCase(repo)


MyCard = Annotated[MyCardUseCase, Depends(get_my_card_use_case)]
PublicCardQuery = Annotated[PublicCardUseCase, Depends(get_public_card_use_case)]
