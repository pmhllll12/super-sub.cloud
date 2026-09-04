"""팀 HTTP 모델. 계약 문서 3-3절."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.shared import Rfc3339


class CreateTeamSchema(BaseModel):
    """`sport_code` 값이 실제로 있는지는 서버가 확인한다(422 `UNKNOWN_SPORT`).

    여기서 고정 목록으로 막지 않는 이유: 종목이 늘 때 **앱 배포 없이 행만 넣으면**
    되게 하기 위해서다.
    """

    name: str = Field(min_length=1, max_length=60)
    region: str = Field(min_length=1, max_length=60)
    sport_code: str = Field(min_length=1, max_length=20)


class AddMemberSchema(BaseModel):
    """`user_id` 를 비우면 **본인이 가입**하는 것이다. 채우면 주장이 남을 넣는다."""

    user_id: UUID | None = None


class TeamMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    nickname: str
    role: str
    joined_at: Rfc3339
    # 그 사람의 선수 카드. **카드를 안 만든 구성원은 둘 다 `null`** 이고, 그래도
    # 목록에는 남는다 — 팀에는 있는 사람이다.
    #
    # 스쿼드 등재(`POST /teams/{id}/squad/members`)는 `player_card_id` 를 받고,
    # 카드로 가는 링크는 `card_public_slug` 를 쓴다. 화면이 둘 다 필요해서
    # 함께 싣는다(미결 `paik` 2번).
    player_card_id: UUID | None = None
    card_public_slug: str | None = None


class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    region: str
    sport_code: str
    members: list[TeamMemberResponse]
