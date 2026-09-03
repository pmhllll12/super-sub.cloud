"""팀 스쿼드와 등재된 카드. 부록 D 도메인 ③ (카드·호칭)."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.card.domain.value_objects.public_slug_vo import PublicSlug


@dataclass(frozen=True)
class SquadMemberEntity:
    """스쿼드에 등재된 카드 1장.

    `nickname` 과 `card_public_slug` 는 표시용으로 읽어 온 값이다 — 저장되는 것은
    `player_card_id` 와 `position_id` 뿐이다(부록 D 의 ERD).

    `position_code` 는 종목 안에서만 유일하므로(야구 `C` 는 포수, 농구 `C` 는 센터)
    **코드만으로는 포지션을 가리킬 수 없다.** 저장은 `position_id` 로 한다.
    """

    id: UUID
    player_card_id: UUID
    card_public_slug: str
    nickname: str
    position_id: UUID
    position_code: str
    position_label: str


@dataclass(frozen=True)
class SquadEntity:
    """한 팀의 스쿼드.

    🔴 **종목이 없다.** `squad -> team -> sport_code` 로 결정된다 — 경기와 같은
    이유다(부록 D.4). 여기에 종목을 들이면 팀 종목과 어긋날 수 있는 두 번째
    진실이 생긴다.

    ⚠️ **스키마는 팀당 여러 개를 허용한다.** 부록 D.7 의 유일 제약이 `public_slug`
    하나뿐이라 `team_id` 에는 제약이 없다. 그런데 `squad` 에 이름 컬럼이 없어
    여러 개를 만들면 서로 구별할 수가 없다. 그래서 **애플리케이션이 팀당 하나로
    다룬다**(생성이 멱등이다). 나중에 이름 컬럼과 함께 열면 스키마 변경 없이
    여러 개를 쓸 수 있다.
    """

    id: UUID
    team_id: UUID
    public_slug: PublicSlug
    members: list[SquadMemberEntity] = field(default_factory=list)
