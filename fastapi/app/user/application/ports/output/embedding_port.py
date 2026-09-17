"""출력 포트 — 텍스트를 임베딩 벡터로 바꾼다.

LLM 키가 사는 곳을 넓히는 결정이라 별도 포트로 뺐다 — `www/`의 챗봇(미결
`min` 7번)과 달리 이건 대화가 아니라 저장·검색용 벡터 계산이라 서버(`fastapi`)가
직접 부른다. 실제 공급자(Gemini 등)는 어댑터의 사정이다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

# "document" = 저장할 프로필 텍스트, "query" = 검색어. 비대칭 임베딩 모델은
# 둘을 다르게 인코딩해야 검색 품질이 나온다(Gemini 임베딩 API의 task_type).
EmbeddingPurpose = Literal["document", "query"]


class EmbeddingPort(ABC):
    @abstractmethod
    def embed(self, text: str, *, purpose: EmbeddingPurpose) -> list[float]:
        """`text`를 고정 차원 벡터로 바꾼다.

        빈 문자열이 오면 어댑터가 무엇을 하든 유스케이스는 신경 쓰지 않는다 —
        빈 텍스트를 임베딩할지 말지는 호출 쪽(인터랙터)이 미리 걸러야 한다.
        """
