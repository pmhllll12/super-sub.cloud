"""출력 포트. 구현은 `adapter/outbound/repositories/`."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.card.domain.entities.card_entity import CardEntity
from app.card.domain.value_objects.public_slug_vo import PublicSlug


class CardPort(ABC):
    @abstractmethod
    def find_by_owner(self, user_id: UUID) -> CardEntity | None:
        """사용자 id 로 카드를 찾는다. **`user` 컨텍스트를 임포트하지 않는다** —
        id 를 인자로 받기 때문이다."""

    @abstractmethod
    def find_by_slug(self, slug: PublicSlug) -> CardEntity | None: ...
