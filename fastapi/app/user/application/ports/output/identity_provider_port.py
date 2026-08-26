"""출력 포트 — 외부 제공자의 신원 확인.

유스케이스는 **구글을 모른다.** 토큰 문자열을 넘기면 확인된 신원이 돌아온다는
사실만 안다. 그래서 카카오·애플을 붙일 때 유스케이스가 바뀌지 않고, 테스트에서는
네트워크 없이 가짜를 끼울 수 있다.

구현은 `adapter/outbound/google/`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.user.domain.value_objects.external_identity_vo import ExternalIdentity


class IdentityProviderPort(ABC):
    @abstractmethod
    def verify(self, id_token: str) -> ExternalIdentity:
        """ID 토큰을 검증하고 신원을 돌려준다.

        검증에 실패하면 401 로 떨어진다. **왜 실패했는지는 나누지 않는다** —
        서명·만료·발급자·대상 중 무엇이 틀렸든 클라이언트가 할 일은 하나다.
        """
