"""경기 HTTP 모델. 계약 문서 3-4절."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.shared import Rfc3339


class PositionNeedSchema(BaseModel):
    position_code: str = Field(min_length=1, max_length=20)
    # 0명을 모집한다는 말은 뜻이 없다. 상한은 종목 규모를 넉넉히 넘긴 값이다.
    head_count: int = Field(ge=1, le=99)


class CreateMatchSchema(BaseModel):
    """`played_at` 은 타임존이 있는 시각이다(`2026-09-10T19:00:00+09:00`).

    포지션 코드가 이 팀 종목에 있는지는 서버가 확인한다(422 `UNKNOWN_POSITION`).
    """

    played_at: datetime
    place: str = Field(min_length=1, max_length=120)
    needs: list[PositionNeedSchema] = Field(min_length=1)


class UpdateMatchSchema(BaseModel):
    """경기를 고친다. **보낸 것만 바뀐다.**

    셋 다 `null` 이 뜻을 갖지 않는 값이라(시각·장소·필요 포지션은 비울 수 없다)
    "안 보냄"과 "null"을 가르지 않았다.

    🔴 `needs` 를 보내면 **통째로 갈아 끼운다.** 부분 갱신은 "어느 포지션을 빼라"를
    표현할 방법이 없어 뜻이 애매해진다.
    """

    played_at: datetime | None = None
    place: str | None = Field(default=None, min_length=1, max_length=120)
    needs: list[PositionNeedSchema] | None = Field(default=None, min_length=1)


class PositionNeedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    position_code: str
    position_label: str
    head_count: int


class MatchResponse(BaseModel):
    """**종목이 없다.** 주최 팀이 결정한다(부록 D.4) — `GET /teams/{team_id}` 를 본다."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    played_at: Rfc3339
    place: str
    needs: list[PositionNeedResponse]
class MatchListingResponse(BaseModel):
    """탐색 목록 한 줄.

    `MatchResponse` 와 달리 **팀 이름·지역·종목이 함께 온다.** 용병이 경기를 고르는
    기준이 그 셋이라, 없으면 화면이 팀을 한 건씩 다시 물어야 한다.

    🔴 종목은 여전히 **팀이 결정한다**(부록 D.4). 여기 실린 값은 저장된 것이 아니라
    `team` 에서 읽어 온 것이라 팀 종목과 어긋날 수가 없다.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    team_name: str
    region: str
    sport_code: str
    played_at: Rfc3339
    place: str
    needs: list[PositionNeedResponse]


class MatchSearchResponse(BaseModel):
    """`GET /admin/users` 와 같은 페이지 형식이다."""

    items: list[MatchListingResponse]
    total: int
    page: int
    size: int


class ApplicationResponse(BaseModel):
    """지원·제안 1건.

    🔴 **`confirmed` 는 서버가 계산한다.** 두 시각을 클라이언트가 보고 판단하게 두면
    확정 조건이 화면마다 갈린다(부록 D.5 — 매칭 확정은 사람이 한다).
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    match_id: UUID
    user_id: UUID
    nickname: str
    team_accepted_at: Rfc3339 | None
    user_accepted_at: Rfc3339 | None
    confirmed: bool


class ApplySchema(BaseModel):
    """`user_id` 를 비우면 **본인이 지원**한다. 채우면 주장이 그 사람에게 제안한다."""

    user_id: UUID | None = None
