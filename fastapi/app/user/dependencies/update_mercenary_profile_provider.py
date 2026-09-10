"""내 용병 프로필 수정 유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.user.application.ports.input.update_mercenary_profile_use_case import (
    UpdateMercenaryProfileUseCase,
)
from app.user.application.use_cases.update_mercenary_profile_interactor import (
    UpdateMercenaryProfileInteractor,
)
from app.user.dependencies.embedding_provider import get_embedding_adapter
from app.user.dependencies.mercenary_repository_provider import MercenaryRepositoryDep


def get_update_mercenary_profile_use_case(
    repository: MercenaryRepositoryDep,
) -> UpdateMercenaryProfileUseCase:
    # `get_embedding_adapter`를 **부르지 않고 그대로 넘긴다** — `Depends()`로
    # 받으면 FastAPI가 이 프로바이더가 불릴 때 즉시 실행해, `skill_summary`를
    # 안 건드리는 요청까지 `GEMINI_API_KEY` 미설정 503에 걸린다.
    return UpdateMercenaryProfileInteractor(repository, get_embedding_adapter)


UpdateMercenaryProfileUseCaseDep = Annotated[
    UpdateMercenaryProfileUseCase, Depends(get_update_mercenary_profile_use_case)
]
