"""카드 주인 값 객체."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class CardOwner:
    """카드에 표시할 주인 정보.

    `user` 엔티티를 그대로 들고 오지 않는다. 카드에 필요한 것은 id 와 닉네임뿐이고,
    이메일·가입일까지 끌고 오면 공개 카드로 새어 나갈 여지가 생긴다.
    """

    id: UUID
    nickname: str
