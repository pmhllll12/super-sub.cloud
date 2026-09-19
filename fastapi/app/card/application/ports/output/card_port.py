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
    def update_style(self, user_id: UUID, style: dict | None) -> CardEntity | None:
        """카드 꾸미기를 통째로 바꾼다. 카드가 없으면 None.

        `update_tagline` 과 같은 자리다 — 여기서 바꿀 수 있는 것은 이것뿐이고,
        `None` 을 주면 지운다(꾸미기 전으로 되돌린다). 형식 검증은 이미
        `CardStyleSchema` 가 끝냈으므로 여기서는 통째로 갈아 끼운다 — 부분
        병합을 하지 않는다. 화면이 늘 전체 값을 들고 있다가 저장하기 때문에
        병합할 이유가 없고, 병합하면 화면과 서버 중 **누가 합치는지** 자리가
        하나 더 생긴다.
        """

    @abstractmethod
    def replace_custom_titles(
        self, user_id: UUID, labels: list[str]
    ) -> CardEntity | None:
        """사람이 직접 적은 호칭을 **통째로** 갈아 끼운다(`paik` 36번).

        `update_style` 과 같은 판단이다 — 부분 병합을 하지 않는다. 화면이 늘
        전체 목록을 들고 있다가 저장하므로 합칠 이유가 없고, 병합하면 화면과
        서버 중 **누가 합치는지** 자리가 하나 더 생긴다. 빈 목록이면 전부
        지운다. 카드가 없으면 `None`.

        🔴 **`user_title`(부여된 호칭)은 안 건드린다** — 다른 테이블이고 다른
        뜻이다. 읽을 때만 카드의 `titles` 에 함께 실린다.
        """

    @abstractmethod
    def delete_by_owner(self, user_id: UUID) -> bool:
        """내 카드를 지운다. 지웠으면 True, 원래 없었으면 False(2026-09-19, `paik`).

        🔴 **되돌릴 수 없다.** 슬러그가 사라지므로 이미 공유한 링크가 죽고, 스쿼드
        판의 자리(`squad_member`)도 외래키 CASCADE 로 같이 빠진다. 부여된 호칭
        (`user_title`)과 직접 적은 호칭(`user_custom_title`)은 **사람**(`user`)에
        붙어 있어 남는다 — 다시 만든 카드에 그대로 실린다.
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
