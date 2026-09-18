"""카드·호칭 규칙.

**부록 D.5 의 설계 원칙이 사는 곳이다.** 스키마로 막아 놨어도 응답에서 되살아나면
무의미하므로 여기서 한 번 더 막고 테스트로 고정한다.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from app.card.domain.entities.card_entity import CardEntity, PublicCardEntity
from app.card.domain.entities.title_entity import TitleEntity

# 카드에 실려서는 안 되는 이름들. 3.5 — "카드에 수치 능력치를 노출하지 않는다".
# player_card 에 그런 컬럼이 애초에 없으므로 조회 경로로도 새면 안 된다.
FORBIDDEN_CARD_FIELDS = frozenset(
    {
        "score", "rating", "stat", "stats", "level", "rank", "ranking",
        "grade", "point", "points", "ability", "abilities", "overall", "tier",
    }
)


def og_image_key_for(card_id: UUID) -> str:
    """공유 미리보기 이미지의 저장 키.

    ⚠️ **아직 그 위치에 파일이 없다.** 이미지 생성도, 파일을 어디에 둘지도 정해지지
    않았다(SFR-001 의 저장 위치 결정과 같은 갈래다). 지금은 **키를 정하는 규칙만**
    두고 값을 채운다 — 컬럼이 NOT NULL 이라 비워 둘 수 없고, 나중에 생성기가
    붙을 때 이 규칙이 그대로 경로가 된다.

    지금 이 값을 그리는 클라이언트는 없다(`www` 의 카드 화면은 고정 장식 이미지를
    쓴다). 그리기 시작하면 **생성기가 먼저 있어야 한다.**
    """
    return f"cards/{card_id}.png"


def og_image_key_for(card_id: UUID) -> str:
    """공유 미리보기 이미지의 저장 키.

    ⚠️ **아직 그 위치에 파일이 없다.** 이미지 생성도, 파일을 어디에 둘지도 정해지지
    않았다(SFR-001 의 저장 위치 결정과 같은 갈래다). 지금은 **키를 정하는 규칙만**
    두고 값을 채운다 — 컬럼이 NOT NULL 이라 비워 둘 수 없고, 나중에 생성기가 붙을
    때 이 규칙이 그대로 경로가 된다.

    지금 이 값을 그리는 클라이언트는 없다(`www` 의 카드 화면은 고정 장식 이미지를
    쓴다). 그리기 시작하면 **생성기가 먼저 있어야 한다.**
    """
    return f"cards/{card_id}.png"


# 카드 사진으로 받는 확장자 (2026-09-18, 사용자 요청).
#
# 🔴 **화이트리스트다.** 클라이언트가 고른 확장자를 그대로 키에 붙이므로,
# 열어 두면 `.html` 을 우리 버킷에 올려 같은 도메인에서 열 수 있다. 사전 서명
# PUT 은 내용을 검사하지 않는다 — 막는 곳은 여기뿐이다.
PHOTO_EXTENSIONS = frozenset({"jpg", "jpeg", "png", "webp"})

# 확장자 ↔ 콘텐츠 타입. 사전 서명은 `ContentType` 을 **서명에 넣으므로**
# 올릴 때와 정확히 같아야 한다 — 다르면 S3 가 403 을 준다.
PHOTO_CONTENT_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}

# 받는 쪽 — **이 목록에 없으면 안 받는다.**
# ⚠️ `image/svg+xml` 은 **일부러 없다**: SVG 는 스크립트를 담을 수 있고, 우리
#    버킷에서 내려가면 같은 출처처럼 다뤄질 여지가 있다.
_EXTENSION_BY_CONTENT_TYPE = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


def extension_for_content_type(content_type: str) -> str | None:
    """콘텐츠 타입 → 확장자. **모르는 것이면 `None`.**

    🔴 **화이트리스트로 뒤집어 읽는다** — 클라이언트가 확장자를 고르게 두면
    타입과 어긋난 키가 생긴다(`image/jpeg` 라며 `.html` 로). 타입 하나만 받고
    확장자는 우리가 정한다.
    """
    return _EXTENSION_BY_CONTENT_TYPE.get(content_type.split(";")[0].strip().lower())


def build_photo_key(user_id: UUID, card_id: UUID, extension: str) -> str:
    """카드 사진의 저장 키.

    `cards/photos/<user_id>/<card_id>-<8자>.<확장자>`

    🔴 **`<user_id>/` 접두사가 접근 통제다.** 사전 서명 PUT 은 키만 알면
    만들어지므로, 저장할 때 이 접두사를 대조해 **남이 올린 객체를 자기 카드
    사진으로 등록하는 것**을 막는다(`owns_photo_key`). 영상의
    `build_storage_key`·`owns_key` 와 같은 짜임이다.

    🔴 **`<8자>` 무작위가 있어야 한다.** 없으면 같은 카드의 두 번째 사진이
    첫 번째를 **조용히 덮고**, 옛 사진은 되돌릴 수 없다. 사전 서명 URL 을
    받아 놓고 안 올린 경우도 있어서 키는 매번 새로 짓는 편이 안전하다.

    ⚠️ 확장자는 **화이트리스트**다(`PHOTO_EXTENSIONS`) — 위 주석 참고.
    """
    ext = extension.lower().lstrip(".")
    if ext not in PHOTO_EXTENSIONS:
        raise ValueError(f"카드 사진으로 받지 않는 확장자다: {extension}")
    return f"cards/photos/{user_id}/{card_id}-{uuid4().hex[:8]}.{ext}"


def owns_photo_key(storage_key: str, user_id: UUID) -> bool:
    """그 키가 **이 사람 자리**에 있는가.

    🔴 **이것이 없으면 남의 사진 키를 자기 카드에 붙일 수 있다.** 키는 비밀이
    아니고(응답에 실려 나간다) 사전 서명도 키만 있으면 만들어지므로, 저장
    시점에 접두사를 대조하는 것이 유일한 방어선이다.

    🔴 **`..` 가 든 키를 막는다.** 접두사만 보면
    `cards/photos/<나>/../../남의것` 이 통과한다 — S3 키는 경로가 아니라 문자열
    이라 그대로 저장되지만, 나중에 이 값을 경로처럼 쓰는 코드가 생기면 새어
    나간다. 규칙이 싼 자리에서 막아 둔다.
    """
    if ".." in storage_key:
        return False
    return storage_key.startswith(f"cards/photos/{user_id}/")


def to_public(card: CardEntity) -> PublicCardEntity:
    """공개용으로 깎는다.

    내부 카드 id 를 떨어뜨리는 것이 요점이다. 공유 링크는 슬러그로만 접근하며
    (SFR-009) 카드 id 를 알아야 할 이유가 없다.
    """
    return PublicCardEntity(
        public_slug=card.public_slug,
        og_image_key=card.og_image_key,
        owner=card.owner,
        titles=list(card.titles),
        # 공유 링크에도 나간다 — 카드에 크게 박히는 값이라 없으면 남이 보는
        # 카드만 밋밋해진다.
        tagline=card.tagline,
        # 꾸미기도 같은 이유로 나간다 — 안 실으면 남이 보는 카드만 안 꾸며진다.
        style=card.style,
    )


# 카드에 한 줄로 들어가는 길이. ORM 도 같은 값이다 —
# **여기가 규칙이고 저쪽은 저장 한계다.**
MAX_TAGLINE = 20


def normalize_tagline(raw: str | None) -> str | None:
    """사람이 쓴 한 줄을 저장할 모양으로 만든다.

    - 앞뒤 공백을 턴다
    - **빈 문자열은 `None` 으로** 본다. "지웠다"와 "빈칸을 넣었다"를 나눌 이유가
      없고, 나누면 화면이 빈 줄을 그리게 된다

    🔴 **길이는 자르지 않고 거부한다.** 조용히 자르면 사람이 쓴 것과 보이는 것이
    달라지고, 그것을 알아차리는 시점은 카드를 공유한 뒤다.
    """
    if raw is None:
        return None
    cleaned = raw.strip()
    if not cleaned:
        return None
    if len(cleaned) > MAX_TAGLINE:
        raise ValueError(f"{MAX_TAGLINE}자를 넘을 수 없다")
    return cleaned


# 사람이 직접 적는 호칭(`paik` 36번). 길이는 `tagline` 과 같은 20자다 —
# 추천 판의 한 줄에 들어가야 해서 그 정도면 충분하다. 개수 상한은 지금
# 화면이 칩 둘을 그린다는 데서 왔다(셋까지 여유를 뒀다).
MAX_CUSTOM_TITLE = 20
MAX_CUSTOM_TITLES = 3


def normalize_custom_titles(raw: list[str] | None) -> list[str]:
    """사람이 적은 호칭들을 저장할 모양으로 만든다(`paik` 36번).

    - 앞뒤 공백을 턴다
    - **빈 문자열은 버린다** — `normalize_tagline` 과 같은 판단(빈 줄을
      그리게 하지 않는다)
    - **같은 글은 하나만 남긴다**(먼저 쓴 순서를 지킨다) — 같은 칩이 둘
      그려질 이유가 없다
    - `None` 은 **전부 지운다**는 뜻이라 빈 목록이 된다

    🔴 **길이도 개수도 자르지 않고 거부한다.** 조용히 자르면 사람이 쓴 것과
    보이는 것이 달라지고, 그것을 알아차리는 시점은 카드를 공유한 뒤다
    (`normalize_tagline` 과 같은 이유).
    """
    if raw is None:
        return []

    cleaned: list[str] = []
    for item in raw:
        text = item.strip()
        if not text:
            continue
        if len(text) > MAX_CUSTOM_TITLE:
            raise ValueError(f"{MAX_CUSTOM_TITLE}자를 넘을 수 없다")
        if text not in cleaned:
            cleaned.append(text)

    if len(cleaned) > MAX_CUSTOM_TITLES:
        raise ValueError(f"{MAX_CUSTOM_TITLES}개를 넘을 수 없다")
    return cleaned


def visible_titles(granted: list[TitleEntity]) -> list[TitleEntity]:
    """카드에 표시할 호칭.

    **부여된 것만 들어온다.** "못 받았다"를 값으로 만들지 않는다(3.5).

    최근에 받은 것을 앞에 둔다. 카드가 좁아서 다 못 보여줄 수 있다.
    """
    return sorted(granted, key=lambda t: t.granted_at, reverse=True)
