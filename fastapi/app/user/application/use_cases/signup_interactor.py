"""가입 인터랙터.

**엔티티 → DTO 변환이 여기서 끝난다.** 라우터로 나가는 것은 원시 타입뿐이라
인바운드 어댑터가 도메인을 임포트하지 않는다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.core.errors import ApiError
from app.user.application.dtos.signup_dto import SignupCommand, SignupResult
from app.user.application.ports.input.signup_use_case import SignupUseCase
from app.user.application.ports.output.user_port import UserPort
from app.user.domain.entities.user_entity import UserEntity
from app.user.domain.value_objects.email_vo import Email
from app.user.domain.value_objects.nickname_vo import Nickname
from app.user.domain.value_objects.password_vo import Password


class SignupInteractor(SignupUseCase):
    def __init__(self, repository: UserPort) -> None:
        self._repository = repository

    def __call__(self, command: SignupCommand) -> SignupResult:
        email = Email.of(command.email)
        if self._repository.email_exists(email):
            raise ApiError(409, "EMAIL_ALREADY_EXISTS", "이미 가입된 이메일입니다.")

        entity = UserEntity(
            id=uuid4(),
            email=email,
            nickname=Nickname.of(command.nickname),
            created_at=datetime.now(timezone.utc),
        )
        # 어떻게 보관하는지(해싱)는 저장소의 사정이다. 여기서는 평문을 넘긴다.
        self._repository.create(entity, Password(command.password))
        return SignupResult(
            id=entity.id,
            email=str(entity.email),
            nickname=str(entity.nickname),
            created_at=entity.created_at,
        )
