"""임베딩 구현을 고르는 곳. 지금은 Gemini 하나다."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.core.config import settings
from app.core.errors import ApiError
from app.user.adapter.outbound.google.gemini_embedding_adapter import (
    GeminiEmbeddingAdapter,
)
from app.user.application.ports.output.embedding_port import EmbeddingPort


@lru_cache
def _adapter() -> GeminiEmbeddingAdapter:
    # `google_client_ids`·`worker_token`과 같은 fail-closed 관례 — 조용한
    # 기본값을 두면 키를 안 넣은 배포가 "임베딩이 전부 실패"가 아니라 "임베딩이
    # 조용히 이상한 값"이 되어 알아채기 더 어렵다.
    if not settings.gemini_api_key:
        raise ApiError(
            503, "EMBEDDING_NOT_CONFIGURED", "GEMINI_API_KEY가 설정되어 있지 않습니다."
        )
    return GeminiEmbeddingAdapter(api_key=settings.gemini_api_key)


def get_embedding_adapter() -> EmbeddingPort:
    return _adapter()


EmbeddingDep = Annotated[EmbeddingPort, Depends(get_embedding_adapter)]
