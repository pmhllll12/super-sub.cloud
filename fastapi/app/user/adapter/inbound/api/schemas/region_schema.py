"""지역 HTTP 모델. 계약 문서. `paik` 19번."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RegionResponse(BaseModel):
    """지역 한 줄. `id`는 경기 조건(`paik` 18번) 저장에 그대로 쓴다."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    city: str
    district: str
    label: str
