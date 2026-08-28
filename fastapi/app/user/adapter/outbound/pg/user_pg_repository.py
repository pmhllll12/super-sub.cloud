"""`UserPort` 의 PostgreSQL 구현.

**유스케이스는 이 파일을 모른다.** `dependencies/user_repository_provider.py` 가
주입하므로, 스텁 ↔ 실제 교체가 프로바이더 한 줄이다.

비밀번호 해싱이 여기 있는 이유: 포트가 평문 `Password` 로 말하고 "어떻게 보관하는가"
는 저장소의 사정이기 때문이다. 알고리즘을 bcrypt 에서 바꿔도 위쪽은 그대로다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.password import PasswordTooLongError, hash_password, verify_password
from app.user.adapter.outbound.mappers.user_mapper import (
    to_membership_entity,
    to_user_entity,
)
from app.user.adapter.outbound.orm.team_member_orm import TeamMemberOrm
from app.user.adapter.outbound.orm.team_orm import TeamOrm
from app.user.adapter.outbound.orm.user_credential_orm import UserCredentialOrm
from app.user.adapter.outbound.orm.user_identity_orm import UserIdentityOrm
from app.user.adapter.outbound.orm.user_orm import UserOrm
from app.user.application.ports.output.user_port import UserPort
from app.user.domain.entities.membership_entity import MembershipEntity
from app.user.domain.entities.user_entity import UserEntity
from app.user.domain.value_objects.email_vo import Email
from app.user.domain.value_objects.nickname_vo import Nickname
from app.user.domain.value_objects.password_vo import Password


# PostgreSQL 의 unique_violation. 드라이버 예외를 직접 뒤지지 않고 표준 SQLSTATE 로
# 판별한다 — psycopg 를 다른 드라이버로 바꿔도 이 값은 같다.
_UNIQUE_VIOLATION = "23505"


def _is_unique_violation(exc: IntegrityError) -> bool:
    return getattr(getattr(exc, "orig", None), "sqlstate", None) == _UNIQUE_VIOLATION


class UserPgRepository(UserPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def email_exists(self, email: Email) -> bool:
        stmt = select(UserOrm.id).where(UserOrm.email == str(email))
        return self._session.execute(stmt).first() is not None

    def create(self, user: UserEntity, password: Password) -> None:
        try:
            password_hash = hash_password(password.value)
        except PasswordTooLongError as exc:
            raise ApiError(422, "VALIDATION_ERROR", str(exc)) from exc

        now = datetime.now(timezone.utc)
        self._session.add(
            UserOrm(
                id=user.id,
                email=str(user.email),
                nickname=str(user.nickname),
                created_at=user.created_at,
            )
        )
        try:
            # 🔴 **flush 를 빼면 안 된다.** 두 모델 사이에 relationship 이 없어서
            # SQLAlchemy 는 INSERT 순서를 알지 못하고, user_credential 이 먼저 나가
            # 외래키 위반이 난다. 여기서 user 를 먼저 내보내 순서를 고정한다.
            self._session.flush()
            self._session.add(
                UserCredentialOrm(
                    id=uuid4(),
                    user_id=user.id,
                    password_hash=password_hash,
                    updated_at=now,
                )
            )
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            # ⚠️ **IntegrityError 를 통째로 409 로 옮기지 않는다.** 그렇게 했더니
            # 위의 외래키 위반이 "이미 가입된 이메일"로 위장돼서, 신규 이메일까지
            # 409 를 받는 버그를 한참 못 찾았다. 유일 제약 위반만 계약의 409 다.
            if _is_unique_violation(exc):
                # 유스케이스가 email_exists 로 먼저 걸러도 동시 요청 두 건은
                # 통과한다. 유일 제약이 마지막 방어선이다.
                raise ApiError(
                    409, "EMAIL_ALREADY_EXISTS", "이미 가입된 이메일입니다."
                ) from exc
            raise

    def find_by_credentials(
        self, email: Email, password: Password
    ) -> UserEntity | None:
        stmt = (
            select(UserOrm, UserCredentialOrm)
            .join(UserCredentialOrm, UserCredentialOrm.user_id == UserOrm.id)
            .where(UserOrm.email == str(email))
        )
        row = self._session.execute(stmt).first()
        if row is None:
            # 없는 이메일과 틀린 비밀번호를 구분하지 않는다 — 구분하면 가입 여부가
            # 새어 나간다(계약 문서 2장). 호출 쪽은 둘 다 None 으로 받는다.
            return None

        user_row, credential = row
        if not verify_password(password.value, credential.password_hash):
            return None
        return to_user_entity(user_row)

    def find_by_identity(self, provider: str, subject: str) -> UserEntity | None:
        stmt = (
            select(UserOrm)
            .join(UserIdentityOrm, UserIdentityOrm.user_id == UserOrm.id)
            .where(
                UserIdentityOrm.provider == provider,
                UserIdentityOrm.subject == subject,
            )
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        return to_user_entity(row) if row is not None else None

    def find_by_email(self, email: Email) -> UserEntity | None:
        stmt = select(UserOrm).where(UserOrm.email == str(email))
        row = self._session.execute(stmt).scalar_one_or_none()
        return to_user_entity(row) if row is not None else None

    def link_identity(self, user_id: UUID, provider: str, subject: str) -> None:
        self._session.add(
            UserIdentityOrm(
                id=uuid4(),
                user_id=user_id,
                provider=provider,
                subject=subject,
                created_at=datetime.now(timezone.utc),
            )
        )
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            if _is_unique_violation(exc):
                # 동시 요청 두 건이 같은 계정을 연결하려 한 경우다. 이미 연결돼
                # 있다는 뜻이므로 호출 쪽이 다시 조회하면 된다.
                raise ApiError(
                    409, "IDENTITY_ALREADY_LINKED", "이미 연결된 계정입니다."
                ) from exc
            raise

    def create_with_identity(
        self, user: UserEntity, provider: str, subject: str
    ) -> None:
        self._session.add(
            UserOrm(
                id=user.id,
                email=str(user.email),
                nickname=str(user.nickname),
                created_at=user.created_at,
            )
        )
        try:
            # user 를 먼저 내보내야 아래 외래키가 성립한다(create 와 같은 이유).
            self._session.flush()
            self._session.add(
                UserIdentityOrm(
                    id=uuid4(),
                    user_id=user.id,
                    provider=provider,
                    subject=subject,
                    created_at=datetime.now(timezone.utc),
                )
            )
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            if _is_unique_violation(exc):
                raise ApiError(
                    409, "EMAIL_ALREADY_EXISTS", "이미 가입된 이메일입니다."
                ) from exc
            raise

    def get(self, user_id: UUID) -> UserEntity | None:
        row = self._session.get(UserOrm, user_id)
        return to_user_entity(row) if row is not None else None

    def update_nickname(self, user_id: UUID, nickname: Nickname) -> None:
        row = self._session.get(UserOrm, user_id)
        if row is None:
            # 존재 확인은 유스케이스가 이미 했다. 그 사이에 사라졌다면 조용히 넘긴다 —
            # 여기서 던지면 같은 판단이 두 곳에 생긴다.
            return
        row.nickname = str(nickname)
        self._session.commit()

    def bump_token_version(self, user_id: UUID) -> None:
        # 🔴 읽고 더해서 쓰지 않는다. `token_version + 1` 을 DB 가 계산해야 동시에
        #    두 번 불려도 한 번이 덮이지 않는다 — 폐기는 덜 되면 의미가 없다.
        self._session.execute(
            update(UserOrm)
            .where(UserOrm.id == user_id)
            .values(token_version=UserOrm.token_version + 1)
        )
        self._session.commit()

    def list_memberships(self, user_id: UUID) -> list[MembershipEntity]:
        """탈퇴 이력을 포함한 전체 소속. 거르는 것은 도메인 규칙의 몫이다."""
        stmt = (
            select(TeamMemberOrm, TeamOrm)
            .join(TeamOrm, TeamOrm.id == TeamMemberOrm.team_id)
            .where(TeamMemberOrm.user_id == user_id)
            .order_by(TeamMemberOrm.joined_at.desc())
        )
        return [
            to_membership_entity(member, team)
            for member, team in self._session.execute(stmt).all()
        ]
