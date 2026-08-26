"""구글 로그인 유스케이스 조립."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.user.application.ports.input.google_login_use_case import GoogleLoginUseCase
from app.user.application.use_cases.google_login_interactor import (
    GoogleLoginInteractor,
)
from app.user.dependencies.identity_verifier_provider import IdentityVerifierDep
from app.user.dependencies.user_repository_provider import UserRepositoryDep


def get_google_login_use_case(
    repository: UserRepositoryDep, verifier: IdentityVerifierDep
) -> GoogleLoginUseCase:
    return GoogleLoginInteractor(repository, verifier)


GoogleLoginUseCaseDep = Annotated[
    GoogleLoginUseCase, Depends(get_google_login_use_case)
]
