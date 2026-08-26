"""구글 로그인 인터랙터.

**이 파일은 구글을 모른다.** `IdentityProviderPort` 가 확인해 준 신원만 받는다.
카카오·애플을 붙일 때 바뀌지 않는다.

세 갈래다.

1. 이미 연결된 외부 계정 → 그 사용자로 로그인
2. 같은 이메일의 기존 계정이 있음 → **이메일이 확인된 경우에만** 연결하고 로그인
3. 처음 온 사람 → 계정을 만들고 로그인
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.core.errors import ApiError
from app.core.security import TOKEN_EXPIRES_IN, issue_access_token
from app.user.application.dtos.login_dto import GoogleLoginCommand, LoginResult
from app.user.application.ports.input.google_login_use_case import GoogleLoginUseCase
from app.user.application.ports.output.identity_provider_port import (
    IdentityProviderPort,
)
from app.user.application.ports.output.user_port import UserPort
from app.user.domain.entities.user_entity import UserEntity
from app.user.domain.value_objects.email_vo import Email
from app.user.domain.value_objects.external_identity_vo import ExternalIdentity
from app.user.domain.value_objects.nickname_vo import MAX_NICKNAME_LENGTH, Nickname


class GoogleLoginInteractor(GoogleLoginUseCase):
    def __init__(
        self, repository: UserPort, provider: IdentityProviderPort
    ) -> None:
        self._repository = repository
        self._provider = provider

    def __call__(self, command: GoogleLoginCommand) -> LoginResult:
        identity = self._provider.verify(command.id_token)

        user = self._repository.find_by_identity(identity.provider, identity.subject)
        if user is None:
            user = self._link_or_create(identity)

        return LoginResult(
            access_token=issue_access_token(user.id),
            expires_in=TOKEN_EXPIRES_IN,
        )

    def _link_or_create(self, identity: ExternalIdentity) -> UserEntity:
        if not identity.email:
            # 이메일 없이 계정을 만들면 `user.email` 유일 제약을 채울 수 없다.
            raise ApiError(
                422, "GOOGLE_EMAIL_MISSING", "구글 계정에서 이메일을 받지 못했습니다."
            )

        email = Email.of(identity.email)
        existing = self._repository.find_by_email(email)
        if existing is not None:
            # 🔴 **확인되지 않은 이메일로는 기존 계정에 연결하지 않는다.**
            # 연결해 주면 아무 이메일이나 적어 남의 계정을 가져갈 수 있다.
            if not identity.email_verified:
                raise ApiError(
                    409,
                    "EMAIL_ALREADY_EXISTS",
                    "이미 가입된 이메일입니다. 비밀번호로 로그인하세요.",
                )
            self._repository.link_identity(
                existing.id, identity.provider, identity.subject
            )
            return existing

        entity = UserEntity(
            id=uuid4(),
            email=email,
            nickname=_nickname_from(identity, email),
            created_at=datetime.now(timezone.utc),
        )
        self._repository.create_with_identity(
            entity, identity.provider, identity.subject
        )
        return entity


def _nickname_from(identity: ExternalIdentity, email: Email) -> Nickname:
    """표시 이름을 닉네임으로 쓴다. 없으면 이메일 앞부분.

    구글의 `name` 은 길이 제한이 없어서 우리 상한을 넘을 수 있다. 자르지 않으면
    저장 시점에 터진다 — **사용자가 고칠 수 없는 실패**라 여기서 맞춰 준다.
    """
    raw = identity.display_name.strip() or str(email).split("@")[0]
    return Nickname.of(raw[:MAX_NICKNAME_LENGTH])
