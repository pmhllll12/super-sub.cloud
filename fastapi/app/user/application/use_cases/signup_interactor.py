"""가입 인터랙터.

**엔티티 → DTO 변환이 여기서 끝난다.** 라우터로 나가는 것은 원시 타입뿐이라
인바운드 어댑터가 도메인을 임포트하지 않는다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.errors import ApiError
from app.user.application.dtos.signup_dto import SignupCommand, SignupResult
from app.user.application.ports.input.signup_use_case import SignupUseCase
from app.user.application.ports.output.user_port import UserPort
from app.user.domain.entities.user_entity import UserEntity
from app.user.domain.value_objects.email_vo import Email
from app.user.domain.value_objects.nickname_vo import Nickname


class SignupInteractor(SignupUseCase):
    def __init__(self, repository: UserPort) -> None:
        self._repository = repository

    def __call__(self, command: SignupCommand) -> SignupResult:
        email = Email.of(command.email)
        if self._repository.email_exists(email):
            raise ApiError(409, "EMAIL_ALREADY_EXISTS", "이미 가입된 이메일입니다.")

        # 스텁이라 저장하지 않는다. 비밀번호도 아직 해싱하지 않는다 — 저장할 곳이
        # 없기 때문이고, DB 가 붙을 때 Password 에서 bcrypt 해시를 만든다.
        entity = UserEntity(
            id=uuid4(),
            email=email,
            nickname=Nickname.of(command.nickname),
            created_at=datetime.now(timezone.utc),
        )
        return SignupResult(
            id=entity.id,
            email=str(entity.email),
            nickname=str(entity.nickname),
            created_at=entity.created_at,
        )
