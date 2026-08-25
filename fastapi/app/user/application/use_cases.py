"""사용자 컨텍스트의 유스케이스.

라우터(HTTP)와 저장소 사이에 있다. 여기서 아는 것은 도메인과 출력 포트뿐이다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.errors import ApiError
from app.security import TOKEN_EXPIRES_IN, issue_access_token
from app.user.application.ports import UserRepository
from app.user.domain.entities import Membership, User
from app.user.domain.rules import active_memberships
from app.user.domain.value_objects import Email, Nickname, Password


@dataclass(frozen=True)
class IssuedToken:
    access_token: str
    expires_in: int


class SignupUseCase:
    def __init__(self, repository: UserRepository) -> None:
        self._repo = repository

    def __call__(self, email: str, password: str, nickname: str) -> User:
        normalized = Email.of(email)
        if self._repo.email_exists(normalized):
            raise ApiError(409, "EMAIL_ALREADY_EXISTS", "이미 가입된 이메일입니다.")

        # 스텁이라 저장하지 않는다. 비밀번호도 아직 해싱하지 않는다 — 저장할 곳이
        # 없기 때문이고, DB 가 붙을 때 Password 에서 bcrypt 해시를 만든다.
        return User(
            id=uuid4(),
            email=normalized,
            nickname=Nickname.of(nickname),
            created_at=datetime.now(timezone.utc),
        )


class LoginUseCase:
    def __init__(self, repository: UserRepository) -> None:
        self._repo = repository

    def __call__(self, email: str, password: str) -> IssuedToken:
        user = self._repo.find_by_credentials(Email.of(email), Password(password))
        if user is None:
            # 이메일이 없는 경우와 비밀번호가 틀린 경우를 구분하지 않는다 —
            # 구분하면 가입 여부가 새어 나간다(계약 문서 2장).
            raise ApiError(
                401, "INVALID_CREDENTIALS", "이메일 또는 비밀번호가 올바르지 않습니다."
            )

        return IssuedToken(issue_access_token(user.id), TOKEN_EXPIRES_IN)


class MeUseCase:
    def __init__(self, repository: UserRepository) -> None:
        self._repo = repository

    def __call__(self, user_id: UUID) -> tuple[User, list[Membership]]:
        user = self._repo.get(user_id)
        if user is None:
            # 토큰은 유효한데 사용자가 없다 — 탈퇴했거나 스텁 밖의 id 다.
            raise ApiError(401, "INVALID_TOKEN", "토큰이 유효하지 않습니다.")
        return user, active_memberships(self._repo.list_memberships(user_id))
