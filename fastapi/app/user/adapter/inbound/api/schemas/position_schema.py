"""포지션 HTTP 모델. 계약 문서 3-3절."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PositionResponse(BaseModel):
    """종목별 포지션 한 줄. 약칭(`code`)은 **종목 안에서만** 유일하다 —
    축구 `FW` 와 농구 `F` 는 다른 것이다.
    """

    model_config = ConfigDict(from_attributes=True)

    # 🔴 `id` 가 다른 도메인이 포지션을 지목하는 값이다 — 클라이언트는 이것을
    #    `PUT /me/match-preferences` 의 `position_ids` 로 되돌려 보낸다.
    #    `code` 로는 못 보낸다(종목 안에서만 유일하다).
    id: UUID
    sport_code: str
    code: str
    label: str
