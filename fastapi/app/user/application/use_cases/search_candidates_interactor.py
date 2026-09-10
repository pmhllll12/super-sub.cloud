"""용병 후보 검색 인터랙터 — RAG의 "R"(검색) 부분.

생성(응답 문장을 만드는 것)은 이 인터랙터의 몫이 아니다. 여기는 순수하게
"조건에 맞는 사람을 유사도 순으로 돌려주는" 검색이고, 그 결과를 자연어로
엮는 것은 호출 쪽(`www/`의 챗봇)이 한다 — `docs/api-contract.md`의 계약이
데이터 형태까지만 정하고 대화 문구는 정하지 않는 것과 같은 경계다.
"""

from __future__ import annotations

from app.core.errors import ApiError
from app.user.application.dtos.mercenary_dto import (
    CandidateResult,
    SearchCandidatesQuery,
)
from app.user.application.ports.input.search_candidates_use_case import (
    SearchCandidatesUseCase,
)
from app.user.application.ports.output.embedding_port import EmbeddingPort
from app.user.application.ports.output.mercenary_port import MercenaryPort


class SearchCandidatesInteractor(SearchCandidatesUseCase):
    def __init__(self, repository: MercenaryPort, embedder: EmbeddingPort) -> None:
        self._repository = repository
        self._embedder = embedder

    def __call__(self, query: SearchCandidatesQuery) -> list[CandidateResult]:
        text = query.query_text.strip()
        if not text:
            raise ApiError(422, "VALIDATION_ERROR", "query_text가 필요합니다.")

        query_embedding = self._embedder.embed(text, purpose="query")
        candidates = self._repository.search_candidates(
            sport_code=query.sport_code,
            position_code=query.position_code,
            query_embedding=query_embedding,
            limit=query.limit,
        )
        return [
            CandidateResult(
                user_id=c.user_id,
                nickname=c.nickname,
                location=c.location,
                skill_summary=c.skill_summary,
                similarity=c.similarity,
            )
            for c in candidates
        ]
