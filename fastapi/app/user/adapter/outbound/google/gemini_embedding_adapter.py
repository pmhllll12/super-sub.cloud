"""`EmbeddingPort`의 Gemini 구현.

🔴 **2026-09-10에 실제 키로 검증했다 — `text-embedding-004`는 이미 은퇴한
모델이라 404였다(NOT_FOUND, embedContent 미지원).** `client.models.list()`로
`embedContent`를 지원하는 모델을 뽑아 `gemini-embedding-001`로 정정했고,
`output_dimensionality=768` 그대로 768차원 벡터가 돌아오는 것을 확인했다.

모델 id는 배포 전에 다시 한번 https://ai.google.dev/gemini-api/docs/embeddings
로 최신인지 확인할 것 — Gemini 쪽이 모델을 종종 은퇴시킨다(이번이 그 예).
"""

from __future__ import annotations

from google import genai
from google.genai import types

from app.core.errors import ApiError
from app.user.application.ports.output.embedding_port import (
    EmbeddingPort,
    EmbeddingPurpose,
)

MODEL = "gemini-embedding-001"
DIMENSIONS = 768

# Gemini 임베딩 API의 비대칭 task_type. 저장할 프로필 글과 검색어를 다르게
# 인코딩해야 검색 품질이 나온다(공식 문서의 권장 사용법).
_TASK_TYPE: dict[EmbeddingPurpose, str] = {
    "document": "RETRIEVAL_DOCUMENT",
    "query": "RETRIEVAL_QUERY",
}


class GeminiEmbeddingAdapter(EmbeddingPort):
    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key)

    def embed(self, text: str, *, purpose: EmbeddingPurpose) -> list[float]:
        try:
            response = self._client.models.embed_content(
                model=MODEL,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type=_TASK_TYPE[purpose],
                    output_dimensionality=DIMENSIONS,
                ),
            )
        except Exception as exc:  # noqa: BLE001 — 공급자 예외 종류가 다양하다
            raise ApiError(
                502, "EMBEDDING_UPSTREAM_ERROR", "임베딩 서비스와 통신하지 못했습니다."
            ) from exc

        embeddings = response.embeddings or []
        if not embeddings or not embeddings[0].values:
            raise ApiError(
                502, "EMBEDDING_UPSTREAM_ERROR", "임베딩 서비스가 빈 응답을 돌려줬습니다."
            )
        return embeddings[0].values
