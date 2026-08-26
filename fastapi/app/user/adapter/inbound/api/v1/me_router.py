"""내 정보 라우터. 계약 문서 2장."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUserId
from app.user.adapter.inbound.api.schemas.me_schema import (
    MeResponse,
    UpdateMeSchema,
)
from app.user.application.dtos.me_dto import MeQuery, MeResult, UpdateMeCommand
from app.user.dependencies.me_provider import MeUseCaseDep
from app.user.dependencies.update_me_provider import UpdateMeUseCaseDep

me_router = APIRouter(tags=["users"])


@me_router.get("/me", response_model=MeResponse)
def read_me(user_id: CurrentUserId, use_case: MeUseCaseDep) -> MeResult:
    return use_case(MeQuery(user_id=user_id))


@me_router.patch("/me", response_model=MeResponse)
def update_me(
    body: UpdateMeSchema, user_id: CurrentUserId, use_case: UpdateMeUseCaseDep
) -> MeResult:
    """닉네임을 바꾸고 **바뀐 뒤의 내 정보 전체**를 돌려준다.

    응답이 `GET /me` 와 같으므로 클라이언트는 파서를 하나만 들면 된다.
    """
    return use_case(UpdateMeCommand(user_id=user_id, nickname=body.nickname))
