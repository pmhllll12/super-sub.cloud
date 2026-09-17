"""스쿼드 HTTP 모델. 계약 문서 3-7절."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SquadMemberResponse(BaseModel):
    """등재된 카드 1장.

    `card_public_slug` 로 그 사람의 공개 카드(`/cards/{slug}`)로 갈 수 있다 —
    **내부 id 를 밖에 내보내지 않는 것**이 카드와 같은 원칙이다.

    `grid_col`·`grid_row` 는 홈 스쿼드 판에서 이 카드가 선 칸이다(미결 `paik` 9번).
    판에 안 올렸으면 둘 다 `null` 이다.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    player_card_id: UUID
    card_public_slug: str
    nickname: str
    position_code: str
    position_label: str
    grid_col: int | None = None
    grid_row: int | None = None


class SquadResponse(BaseModel):
    """**종목이 없다.** 주최 팀이 결정한다(부록 D.4) — `GET /teams/{team_id}` 를 본다.

    `formation` 은 홈 판의 판 크기(`"3:3"`·`"5:5"`·`"7:7"`)다 — 아직 안 정했으면 `null`.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    public_slug: str
    formation: str | None = None
    members: list[SquadMemberResponse]


class _GridPlacement(BaseModel):
    """홈 판 격자 칸. **열·행 번호이고 픽셀이 아니다** (미결 `paik` 9번).

    🔴 **both-or-neither** — 판에서만 빼려면 둘 다 `null` 로 준다. 한쪽만 주면 422.
    상한 15 는 픽셀 좌표를 거르는 방어값이다(지금 격자는 3열 × 4행 — 정본은 계약 3-7).
    """

    grid_col: int | None = Field(default=None, ge=0, le=15)
    grid_row: int | None = Field(default=None, ge=0, le=15)

    @model_validator(mode="after")
    def _both_or_neither(self) -> "_GridPlacement":
        if (self.grid_col is None) != (self.grid_row is None):
            raise ValueError("grid_col 과 grid_row 는 함께 주거나 함께 비웁니다.")
        return self


class EnlistCardSchema(_GridPlacement):
    """카드를 등재한다. 등재하면서 판에 바로 올리려면 `grid_col`·`grid_row` 를 준다.

    `position_code` 가 이 팀 종목에 있는지는 서버가 확인한다(422 `UNKNOWN_POSITION`).
    약칭은 종목 안에서만 유일하다 — 야구 `C` 는 포수, 농구 `C` 는 센터다.
    """

    player_card_id: UUID
    position_code: str = Field(min_length=1, max_length=20)


class MoveMemberSchema(_GridPlacement):
    """등재 하나의 포지션·판 배치를 바꾼다 (미결 `paik` 9번).

    `position_code` 는 **항상 준다** — 등재는 포지션 없이 존재하지 않는다. 포지션은
    그대로 두고 칸만 옮기려면 지금 포지션 코드를 그대로 실으면 된다.
    """

    position_code: str = Field(min_length=1, max_length=20)


class SetFormationSchema(BaseModel):
    """판 크기를 저장한다 (미결 `paik` 9번). 클라이언트가 `"3:3"`·`"5:5"`·`"7:7"` 로 쓴다."""

    formation: str = Field(min_length=1, max_length=8)
