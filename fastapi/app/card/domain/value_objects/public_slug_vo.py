"""공유 슬러그 값 객체."""

from __future__ import annotations

import secrets
from dataclasses import dataclass

# 무작위 바이트 수. token_urlsafe 는 base64 라 16글자가 나온다.
# 96비트면 추측·전수 시도가 성립하지 않는다 — 공개 조회는 인증이 없으므로
# (SFR-009) 슬러그 자체가 유일한 접근 통제다.
_ENTROPY_BYTES = 12


@dataclass(frozen=True)
class PublicSlug:
    """공유 링크에 쓰는 슬러그 (SFR-009).

    `player_card.public_slug` 에 유일 제약이 있다(부록 D.7). **카드 id 대신 이것으로만
    공개 조회를 받는다** — 내부 식별자를 밖에 내보내지 않기 위해서다.
    """

    value: str

    @classmethod
    def generate(cls) -> "PublicSlug":
        """새 슬러그를 만든다 (SEC-005).

        🔴 **닉네임에서 유도하지 않는다.** 유도하면 남의 카드 주소를 이름만 알고
        맞힐 수 있고, 닉네임을 바꿔도 옛 주소가 뜻을 남긴다. `secrets` 를 쓰는 것도
        같은 이유다 — `random` 은 예측 가능한 의사난수라 이 자리에 쓰면 안 된다.

        스텁의 데모 슬러그(`hong-gildong-4f2a`)는 사람이 읽기 좋으라고 손으로 적은
        고정값이고 **생성 규칙이 아니다.**
        """
        return cls(secrets.token_urlsafe(_ENTROPY_BYTES))

    def __str__(self) -> str:
        return self.value
