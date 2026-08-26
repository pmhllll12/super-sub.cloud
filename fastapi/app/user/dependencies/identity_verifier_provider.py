"""외부 신원 확인 구현을 고르는 곳.

지금은 구글 하나다. 카카오가 붙으면 여기서 갈라진다.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.core.config import settings
from app.user.adapter.outbound.google.google_identity_verifier import (
    GoogleIdentityVerifier,
)
from app.user.application.ports.output.identity_provider_port import (
    IdentityProviderPort,
)


@lru_cache
def _verifier() -> GoogleIdentityVerifier:
    # 캐시하는 이유는 JWKS 클라이언트가 구글의 공개키를 들고 있기 때문이다.
    # 요청마다 새로 만들면 매번 구글에 키를 받으러 간다.
    return GoogleIdentityVerifier(audiences=settings.google_audiences)


def get_identity_verifier() -> IdentityProviderPort:
    return _verifier()


IdentityVerifierDep = Annotated[IdentityProviderPort, Depends(get_identity_verifier)]
