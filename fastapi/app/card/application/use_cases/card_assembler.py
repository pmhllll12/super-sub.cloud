"""엔티티 → DTO 변환.

두 인터랙터가 같은 변환을 쓰므로 한곳에 모았다. **여기까지가 도메인의 마지막
지점이다** — 이 함수들이 돌려준 뒤로는 값 객체가 나가지 않는다.
"""

from __future__ import annotations

from app.card.application.dtos.card_dto import (
    CardOwnerResult,
    MyCardResult,
    PublicCardResult,
    TitleResult,
)
from app.card.domain.entities.card_entity import CardEntity, PublicCardEntity
from app.card.domain.entities.title_entity import TitleEntity
from app.card.domain.value_objects.card_owner_vo import CardOwner


def _titles(titles: list[TitleEntity]) -> list[TitleResult]:
    return [
        TitleResult(
            code=t.code,
            label=t.label,
            # 🔴 `str(None)` 이 `"None"` 이 되지 않게 가른다 — 사람이 직접
            # 적은 호칭은 분류가 없다(`paik` 36번).
            category=str(t.category) if t.category is not None else None,
            granted_at=t.granted_at,
        )
        for t in titles
    ]


def _owner(owner: CardOwner) -> CardOwnerResult:
    return CardOwnerResult(id=owner.id, nickname=owner.nickname)


def to_my_card_result(card: CardEntity, photo_url: str | None = None) -> MyCardResult:
    """🔴 `photo_url` 은 **엔티티에 없다** — 저장소가 그때그때 서명해 주는
    값이라 도메인이 알 수 없다. 인터랙터가 받아서 여기로 넘긴다."""
    return MyCardResult(
        id=card.id,
        public_slug=str(card.public_slug),
        og_image_key=card.og_image_key,
        user=_owner(card.owner),
        titles=_titles(card.titles),
        tagline=card.tagline,
        style=card.style,
        photo_url=photo_url,
    )


def to_public_card_result(
    card: PublicCardEntity, photo_url: str | None = None
) -> PublicCardResult:
    return PublicCardResult(
        public_slug=str(card.public_slug),
        og_image_key=card.og_image_key,
        user=_owner(card.owner),
        titles=_titles(card.titles),
        tagline=card.tagline,
        style=card.style,
        photo_url=photo_url,
    )


def photo_url_of(style: dict | None, storage) -> str | None:
    """`style["photo_key"]` 로 사전 서명 GET 주소를 만든다.

    🔴 **`None` 인 경우가 셋이고 전부 정상이다** — 사진을 안 올렸다 ·
    저장소가 설정 안 됐다(로컬) · `style` 자체가 없다. 화면은 그때 기본
    장식 그림을 그린다.

    🔴 **키 존재를 확인하지 않는다.** 서명만 만드는 것이 영상과 같은 방식이고
    (`create_download_url` 주석), 확인하려면 카드를 읽을 때마다 S3 를 한 번
    더 두드려야 한다 — 스쿼드 판은 카드를 한 번에 5~7장 읽는다.
    """
    if storage is None or not style:
        return None
    key = style.get("photo_key")
    if not key:
        return None
    url, _ttl = storage.create_download_url(key)
    return url
