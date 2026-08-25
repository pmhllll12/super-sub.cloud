"""공유 슬러그 값 객체."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PublicSlug:
    """공유 링크에 쓰는 슬러그 (SFR-009).

    `player_card.public_slug` 에 유일 제약이 있다(부록 D.7). **카드 id 대신 이것으로만
    공개 조회를 받는다** — 내부 식별자를 밖에 내보내지 않기 위해서다.
    """

    value: str

    def __str__(self) -> str:
        return self.value
