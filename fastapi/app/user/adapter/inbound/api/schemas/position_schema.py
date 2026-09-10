"""포지션 HTTP 모델. 계약 문서 3-3절."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PositionResponse(BaseModel):
    """종목별 포지션 한 줄. 약칭(`code`)은 **종목 안에서만** 유일하다 —
    축구 `FW` 와 농구 `F` 는 다른 것이다.
    """

    model_config = ConfigDict(from_attributes=True)

    sport_code: str
    code: str
    label: str
