"""가입 유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.user.application.ports.input.signup_use_case import SignupUseCase
from app.user.application.use_cases.signup_interactor import SignupInteractor
from app.user.dependencies.user_repository_provider import UserRepositoryDep


def get_signup_use_case(repository: UserRepositoryDep) -> SignupUseCase:
    return SignupInteractor(repository)


SignupUseCaseDep = Annotated[SignupUseCase, Depends(get_signup_use_case)]
