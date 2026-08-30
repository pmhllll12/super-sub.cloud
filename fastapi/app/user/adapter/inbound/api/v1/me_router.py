"""내 정보 라우터. 계약 문서 2장."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import CurrentUserId
from app.user.adapter.inbound.api.schemas.me_schema import (
    ChangePasswordSchema,
    DeleteMeSchema,
    MeResponse,
    UpdateMeSchema,
)
from app.user.application.dtos.me_dto import (
    ChangePasswordCommand,
    DeleteMeCommand,
    MeQuery,
    MeResult,
    UpdateMeCommand,
)
from app.user.dependencies.change_password_provider import ChangePasswordUseCaseDep
from app.user.dependencies.delete_me_provider import DeleteMeUseCaseDep
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


@me_router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    user_id: CurrentUserId,
    use_case: DeleteMeUseCaseDep,
    body: DeleteMeSchema | None = None,
) -> None:
    """탈퇴한다. 계정과 파생 데이터가 함께 지워진다(SEC-006).

    비밀번호가 있는 계정은 **비밀번호를 함께 보내야 한다** — 되돌릴 수 없는
    동작이라 토큰만으로는 실행하지 않는다.
    """
    use_case(
        DeleteMeCommand(
            user_id=user_id, password=body.password if body else None
        )
    )


@me_router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: ChangePasswordSchema,
    user_id: CurrentUserId,
    use_case: ChangePasswordUseCaseDep,
) -> None:
    """비밀번호를 바꾼다. **성공하면 기존 토큰이 전부 무효가 된다**(SEC-004).

    지금 쓰던 토큰도 함께 끊기므로 앱은 다시 로그인시켜야 한다.
    """
    use_case(
        ChangePasswordCommand(
            user_id=user_id,
            current_password=body.current_password,
            new_password=body.new_password,
        )
    )
