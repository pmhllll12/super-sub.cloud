"""입력 포트 — 가입.

라우터는 **이 타입에만 의존한다.** 구현(`SignupInteractor`)을 몰라도 되고,
테스트에서 가짜 유스케이스를 끼울 수도 있다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.user.application.dtos.signup_dto import SignupCommand, SignupResult


class SignupUseCase(ABC):
    @abstractmethod
    def __call__(self, command: SignupCommand) -> SignupResult:
        """가입시킨다. 이미 있는 이메일이면 409 로 떨어진다."""
