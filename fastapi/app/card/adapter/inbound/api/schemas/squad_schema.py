"""스쿼드 HTTP 모델. 계약 문서 3-7절."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SquadMemberResponse(BaseModel):
    """등재된 카드 1장.

    `card_public_slug` 로 그 사람의 공개 카드(`/cards/{slug}`)로 갈 수 있다 —
    **내부 id 를 밖에 내보내지 않는 것**이 카드와 같은 원칙이다.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    player_card_id: UUID
    card_public_slug: str
    nickname: str
    position_code: str
    position_label: str


class SquadResponse(BaseModel):
    """**종목이 없다.** 주최 팀이 결정한다(부록 D.4) — `GET /teams/{team_id}` 를 본다."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    public_slug: str
    members: list[SquadMemberResponse]


class EnlistCardSchema(BaseModel):
    """카드를 등재한다.

    `position_code` 가 이 팀 종목에 있는지는 서버가 확인한다(422 `UNKNOWN_POSITION`).
    약칭은 종목 안에서만 유일하다 — 야구 `C` 는 포수, 농구 `C` 는 센터다.
    """

    player_card_id: UUID
    position_code: str = Field(min_length=1, max_length=20)
