"""내 정보 라우터. 계약 문서 2장."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUserId
from app.user.adapter.inbound.api.schemas.me_schema import MeResponse
from app.user.application.dtos.me_dto import MeQuery, MeResult
from app.user.dependencies.me_provider import MeUseCaseDep

me_router = APIRouter(tags=["users"])


@me_router.get("/me", response_model=MeResponse)
def read_me(user_id: CurrentUserId, use_case: MeUseCaseDep) -> MeResult:
    return use_case(MeQuery(user_id=user_id))
