"""평가·신뢰 요청·응답 형태. 계약 3-9절."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.shared import Rfc3339


class ReviewOptionResponse(BaseModel):
    """평가 선택지 하나. **배열의 순서가 화면 노출 순서다.**"""

    code: str
    category: str
    label: str


class SubmitReviewSchema(BaseModel):
    """평가 제출.

    🔴 **점수가 없다.** 고른 선택지 코드만 보낸다 — 평가는 선택형이다(3.4).
    """

    reviewee_id: UUID
    option_codes: list[str] = Field(min_length=1, max_length=20)


class ReviewResponse(BaseModel):
    id: UUID
    match_id: UUID
    reviewer_id: UUID
    reviewee_id: UUID
    submitted_at: Rfc3339
    selected_codes: list[str]


class RecordNoShowSchema(BaseModel):
    user_id: UUID


class NoShowResponse(BaseModel):
    id: UUID
    match_id: UUID
    user_id: UUID
    recorded_at: Rfc3339


class FileReportSchema(BaseModel):
    target_user_id: UUID
    reason: str = Field(min_length=1, max_length=1000)


class ReportResponse(BaseModel):
    """접수 확인만 돌려준다.

    ⚠️ **신고 내용을 되돌려주지 않는다.** 신고자에게도 사본을 주면 그 응답이
    떠돌아다니고, 대상에게는 더더욱 보이면 안 된다.
    """

    id: UUID
    target_user_id: UUID
    created_at: Rfc3339
