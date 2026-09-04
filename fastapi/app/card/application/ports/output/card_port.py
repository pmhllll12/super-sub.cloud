"""출력 포트. 구현은 `adapter/outbound/` — 지금은 `stub/`, DB 가 붙으면 `pg/`."""

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

    @abstractmethod
    def update_tagline(self, user_id: UUID, tagline: str | None) -> CardEntity | None:
        """카드의 한 줄을 바꾼다. 카드가 없으면 None.

        🔴 **여기서 바꿀 수 있는 것은 이것뿐이다.** `public_slug` 는 이미 공유된
        주소라 바꾸면 남이 가진 링크가 죽고, `og_image_key` 는 슬러그에서
        규칙으로 나온다. 포트에 그 둘을 받는 인자를 두지 않는 것이 그 규칙을
        코드로 지키는 방법이다.

        `None` 을 주면 **지운다** — 안 정한 상태로 돌아간다.
        """
    @abstractmethod
    def create_for_owner(self, user_id: UUID) -> CardEntity:
        """카드를 만들어 돌려준다. **이미 있으면 있는 것을 돌려준다.**

        슬러그 생성이 구현 쪽에 있는 이유: 유일 제약에 걸렸을 때 **다시 뽑아
        재시도할 수 있는 곳이 저장소뿐**이다. 규칙 자체는 도메인에 있다
        (`PublicSlug.generate`).
        """

    @abstractmethod
    def create_for_owner(self, user_id: UUID) -> CardEntity:
        """카드를 만들어 돌려준다. **이미 있으면 있는 것을 돌려준다.**

        슬러그 생성이 구현 쪽에 있는 이유: 유일 제약에 걸렸을 때 **다시 뽑아
        재시도할 수 있는 곳이 저장소뿐**이다. 규칙 자체는 도메인에 있다
        (`PublicSlug.generate`).
        """
