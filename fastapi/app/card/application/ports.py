"""출력 포트. 구현은 `adapter/outbound/`."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.card.domain.entities import Card
from app.card.domain.value_objects import PublicSlug


class CardRepository(Protocol):
    def find_by_owner(self, user_id: UUID) -> Card | None: ...

    def find_by_slug(self, slug: PublicSlug) -> Card | None: ...
