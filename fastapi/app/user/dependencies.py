"""이 컨텍스트의 의존성 주입.

**저장소 구현을 고르는 곳은 여기다.** DB 가 붙으면 `StubUserRepository` 를
`PgUserRepository` 로 바꾸면 되고 유스케이스·라우터는 고치지 않는다.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.user.adapter.outbound.stub_repository import StubUserRepository
from app.user.application.ports import UserRepository
from app.user.application.use_cases import LoginUseCase, MeUseCase, SignupUseCase


def get_repository() -> UserRepository:
    return StubUserRepository()


_Repo = Annotated[UserRepository, Depends(get_repository)]


def get_signup_use_case(repo: _Repo) -> SignupUseCase:
    return SignupUseCase(repo)


def get_login_use_case(repo: _Repo) -> LoginUseCase:
    return LoginUseCase(repo)


def get_me_use_case(repo: _Repo) -> MeUseCase:
    return MeUseCase(repo)


Signup = Annotated[SignupUseCase, Depends(get_signup_use_case)]
Login = Annotated[LoginUseCase, Depends(get_login_use_case)]
Me = Annotated[MeUseCase, Depends(get_me_use_case)]
