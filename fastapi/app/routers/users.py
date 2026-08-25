"""내 정보. 계약 문서 2장."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app import stubs
from app.deps import require_token
from app.schemas import MeResponse

router = APIRouter(tags=["users"])


@router.get("/me", response_model=MeResponse)
def read_me(_: Annotated[str, Depends(require_token)]) -> MeResponse:
    return stubs.me()
