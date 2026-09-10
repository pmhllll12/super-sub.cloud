"""용병 후보 검색 유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.user.application.ports.input.search_candidates_use_case import (
    SearchCandidatesUseCase,
)
from app.user.application.use_cases.search_candidates_interactor import (
    SearchCandidatesInteractor,
)
from app.user.dependencies.embedding_provider import EmbeddingDep
from app.user.dependencies.mercenary_repository_provider import MercenaryRepositoryDep


def get_search_candidates_use_case(
    repository: MercenaryRepositoryDep, embedder: EmbeddingDep
) -> SearchCandidatesUseCase:
    # 검색은 이 요청 자체가 임베딩을 계산해야만 성립하므로(수정과 달리 "안 쓰는
    # 경로"가 없다) 여기서는 즉시 만들어도 된다.
    return SearchCandidatesInteractor(repository, embedder)


SearchCandidatesUseCaseDep = Annotated[
    SearchCandidatesUseCase, Depends(get_search_candidates_use_case)
]
