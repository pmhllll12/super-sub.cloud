"""테스트·로컬 개발용 임베딩 어댑터. 네트워크를 타지 않는다.

`hashlib`로 텍스트를 결정적(deterministic) 벡터로 바꾼다 — 같은 텍스트는
항상 같은 벡터가 되어야 "비슷한 소개글이 비슷한 벡터가 된다"는 성질은
없어도(실제 의미 이해가 없으니 당연하다), 최소한 **같은 값 재현성**은
필요한 테스트(예: 저장 후 재조회)를 통과시킬 수 있다.
"""

from __future__ import annotations

import hashlib

from app.user.application.ports.output.embedding_port import (
    EmbeddingPort,
    EmbeddingPurpose,
)

DIMENSIONS = 768


class StubEmbeddingAdapter(EmbeddingPort):
    def embed(self, text: str, *, purpose: EmbeddingPurpose) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # 32바이트로 768개 float을 채운다 — 바이트를 반복해 순환시키고 [-1, 1]로
        # 정규화한다. 실제 임베딩 모델의 분포를 흉내 내려는 것이 아니라, 순전히
        # "결정적이고 차원이 맞는 벡터"가 필요한 자리를 채우는 것뿐이다.
        return [(digest[i % len(digest)] / 127.5) - 1.0 for i in range(DIMENSIONS)]
