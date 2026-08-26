"""저장소 프로바이더.

**이 컨텍스트에서 구현을 고르는 유일한 곳이다.** DB 가 붙으면 여기 한 줄만
`UserPgRepository` 로 바꾸면 되고 인터랙터·라우터는 고치지 않는다.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.user.adapter.outbound.stub.user_stub_repository import (
    StubUserRepository,
)
from app.user.application.ports.output.user_port import UserPort


def get_user_repository() -> UserPort:
    return StubUserRepository()


UserRepositoryDep = Annotated[UserPort, Depends(get_user_repository)]
