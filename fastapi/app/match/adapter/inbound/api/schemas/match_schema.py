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
