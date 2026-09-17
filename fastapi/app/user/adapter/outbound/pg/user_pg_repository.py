"""`UserPort` 의 PostgreSQL 구현.

**유스케이스는 이 파일을 모른다.** `dependencies/user_repository_provider.py` 가
주입하므로, 스텁 ↔ 실제 교체가 프로바이더 한 줄이다.

비밀번호 해싱이 여기 있는 이유: 포트가 평문 `Password` 로 말하고 "어떻게 보관하는가"
는 저장소의 사정이기 때문이다. 알고리즘을 bcrypt 에서 바꿔도 위쪽은 그대로다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import column, func, insert, or_, select, table, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.password import PasswordTooLongError, hash_password, verify_password
from app.user.adapter.outbound.mappers.user_mapper import (
    to_membership_entity,
    to_user_contact_entity,
    to_user_entity,
)
from app.user.adapter.outbound.orm.team_member_orm import TeamMemberOrm
from app.user.adapter.outbound.orm.team_orm import TeamOrm
from app.user.adapter.outbound.orm.user_contact_orm import UserContactOrm
from app.user.adapter.outbound.orm.user_credential_orm import UserCredentialOrm
from app.user.adapter.outbound.orm.user_identity_orm import UserIdentityOrm
from app.user.adapter.outbound.orm.user_orm import UserOrm
from app.user.application.ports.output.user_port import UserPort
from app.user.domain.entities.membership_entity import MembershipEntity
from app.user.domain.entities.user_contact_entity import (
    UserContactEntity,
    UserContactSummary,
)
from app.user.domain.entities.user_entity import UserEntity
from app.user.domain.value_objects.email_vo import Email
from app.user.domain.value_objects.nickname_vo import Nickname
from app.user.domain.value_objects.password_vo import Password


# PostgreSQL 의 unique_violation. 드라이버 예외를 직접 뒤지지 않고 표준 SQLSTATE 로
# 판별한다 — psycopg 를 다른 드라이버로 바꿔도 이 값은 같다.
_UNIQUE_VIOLATION = "23505"


def _is_unique_violation(exc: IntegrityError) -> bool:
    return getattr(getattr(exc, "orig", None), "sqlstate", None) == _UNIQUE_VIOLATION


def _constraint_name(exc: IntegrityError) -> str | None:
    """어느 유일 제약이 걸렸는지. `email`·`nickname` 둘 다 이 테이블에 있어서
    (2026.09.15, `uq_user_nickname` 추가) `_is_unique_violation`만으로는 어느
    쪽인지 못 가른다 — 이름을 봐야 한다."""
    diag = getattr(getattr(exc, "orig", None), "diag", None)
    return getattr(diag, "constraint_name", None)


# LIKE 패턴에서 특별한 뜻을 갖는 문자. 검색어에 들어오면 리터럴로 바꿔야 한다.
_LIKE_ESCAPE = "\\"


def _escape_like(value: str) -> str:
    """LIKE 메타문자를 리터럴로 만든다.

    🔴 역슬래시를 **먼저** 바꾼다. 나중에 바꾸면 `%` 를 감싸려고 붙인 이스케이프
    문자까지 다시 이스케이프되어 패턴이 깨진다.
    """
    return (
        value.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2)
        .replace("%", f"{_LIKE_ESCAPE}%")
        .replace("_", f"{_LIKE_ESCAPE}_")
    )

# `notification` 은 `notification` 컨텍스트의 테이블이다. 임포트하지 않고
# 원시 SQL 로 쓴다 — `notification_port.py` docstring 참고. 컬럼 이름이 바뀌면
# 여기가 조용히 안 맞게 되므로 `tests/user/adapter/test_user_contact_db.py` 가
# 실제 DB 로 대조한다.
_notification = table(
    "notification",
    column("id"),
    column("recipient_user_id"),
    column("type"),
    column("actor_user_id"),
    column("subject_type"),
    column("subject_id"),
    column("read_at"),
    column("created_at"),
)

# `app.notification.domain.rules.notification_rules` 의 값과 같다(컨텍스트끼리
# 임포트하지 않으므로 값만 복제 — 위 `_UNIQUE_VIOLATION`과 같은 판단).
_NOTIFY_CONTACT_REQUEST = "contact_request"
_NOTIFY_CONTACT_ACCEPTED = "contact_accepted"
_SUBJECT_USER_CONTACT = "user_contact"


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
            # 🔴 **어느 유일 제약인지도 가른다**(2026.09.15) — `uq_user_nickname`이
            # 생기기 전에는 이 테이블에 유일 제약이 email 하나뿐이라 안 가려도
            # 됐다. 안 가르면 닉네임이 겹쳤을 뿐인데 "이미 가입된 이메일"이라고
            # 잘못 답한다.
            if _constraint_name(exc) == "uq_user_nickname":
                raise ApiError(
                    409, "NICKNAME_ALREADY_EXISTS", "이미 사용 중인 닉네임입니다."
                ) from exc
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
            # 어느 유일 제약인지 가른다 — `create`와 같은 이유(2026.09.15).
            if _constraint_name(exc) == "uq_user_nickname":
                raise ApiError(
                    409, "NICKNAME_ALREADY_EXISTS", "이미 사용 중인 닉네임입니다."
                ) from exc
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
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            # `uq_user_nickname`(2026.09.15) 도입 후 — 남이 이미 쓰는 닉네임으로
            # 바꾸려 하면 여기서 걸린다.
            if _constraint_name(exc) == "uq_user_nickname":
                raise ApiError(
                    409, "NICKNAME_ALREADY_EXISTS", "이미 사용 중인 닉네임입니다."
                ) from exc
            raise

    def change_password(self, user_id: UUID, password: Password) -> None:
        try:
            password_hash = hash_password(password.value)
        except PasswordTooLongError as exc:
            # 72바이트를 넘으면 **자르지 않고 거부한다**(SEC-002). 가입과 같은 판단이다.
            raise ApiError(422, "VALIDATION_ERROR", str(exc)) from exc

        now = datetime.now(timezone.utc)
        row = self._session.execute(
            select(UserCredentialOrm).where(UserCredentialOrm.user_id == user_id)
        ).scalar_one_or_none()

        if row is None:
            # 구글로만 가입한 계정에는 자격증명 행이 없다. 여기서 만들어 주면
            # 그때부터 비밀번호 로그인도 된다.
            self._session.add(
                UserCredentialOrm(
                    id=uuid4(),
                    user_id=user_id,
                    password_hash=password_hash,
                    updated_at=now,
                )
            )
        else:
            row.password_hash = password_hash
            row.updated_at = now
        self._session.commit()

    def has_password(self, user_id: UUID) -> bool:
        stmt = select(UserCredentialOrm.id).where(
            UserCredentialOrm.user_id == user_id
        )
        return self._session.execute(stmt).scalar_one_or_none() is not None

    def delete(self, user_id: UUID) -> None:
        # 자격증명·외부 신원·카드·호칭·소속·영상 체인은 **외래키 연쇄**가 함께 지운다
        # (부록 D.6). 여기서 하나씩 지우면 테이블이 늘 때마다 빠뜨린다.
        row = self._session.get(UserOrm, user_id)
        if row is None:
            return
        self._session.delete(row)
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

    def list_users(
        self, *, q: str | None, offset: int, limit: int
    ) -> tuple[list[UserEntity], int]:
        stmt = select(UserOrm)
        count_stmt = select(func.count()).select_from(UserOrm)
        if q:
            # 이메일은 Email.of 로 소문자 정규화해 저장하지만 닉네임은 아니라서
            # 둘 다 대소문자를 가리지 않는 ilike 로 맞춘다.
            # 🔴 `%`·`_` 는 LIKE 메타문자다. 그대로 넘기면 검색어가 패턴이 되어
            #    `q="%"` 한 글자로 전체가 걸린다 — 리터럴로 이스케이프한다.
            pattern = f"%{_escape_like(q)}%"
            condition = or_(
                UserOrm.email.ilike(pattern, escape=_LIKE_ESCAPE),
                UserOrm.nickname.ilike(pattern, escape=_LIKE_ESCAPE),
            )
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)

        total = self._session.execute(count_stmt).scalar_one()
        stmt = stmt.order_by(UserOrm.created_at.desc()).offset(offset).limit(limit)
        rows = self._session.execute(stmt).scalars().all()
        return [to_user_entity(row) for row in rows], total

    def has_card(self, user_id: UUID) -> bool:
        """`player_card` 는 `card` 컨텍스트의 테이블이다.

        `app/core/deps.py` 의 토큰 버전 조회와 같은 이유로 ORM 을 임포트하지 않고
        `table()`/`column()` 원시 쿼리로 읽는다 — 그래야 `user` 가 `card` 를
        임포트하지 않는다(`tests/test_architecture.py` 의 컨텍스트 경계 검사).
        """
        card_table = table("player_card", column("user_id"))
        stmt = select(card_table.c.user_id).where(card_table.c.user_id == user_id)
        return self._session.execute(stmt).first() is not None

    def card_slugs(self, user_ids: list[UUID]) -> dict[UUID, str]:
        """`has_card` 와 같은 이유로 원시 쿼리다 — 카드를 안 만든 사람은 빠진다."""
        if not user_ids:
            return {}
        card_table = table("player_card", column("user_id"), column("public_slug"))
        stmt = select(card_table.c.user_id, card_table.c.public_slug).where(
            card_table.c.user_id.in_(user_ids)
        )
        return {row.user_id: row.public_slug for row in self._session.execute(stmt)}

    def update_searchable(self, user_id: UUID, is_nickname_searchable: bool) -> None:
        stmt = (
            update(UserOrm)
            .where(UserOrm.id == user_id)
            .values(is_nickname_searchable=is_nickname_searchable)
        )
        self._session.execute(stmt)
        self._session.commit()

    def search_by_nickname(
        self, *, q: str, exclude_user_id: UUID, limit: int
    ) -> list[UserEntity]:
        pattern = f"%{_escape_like(q)}%"
        stmt = (
            select(UserOrm)
            .where(UserOrm.is_nickname_searchable.is_(True))
            .where(UserOrm.id != exclude_user_id)
            .where(UserOrm.nickname.ilike(pattern, escape=_LIKE_ESCAPE))
            .order_by(UserOrm.nickname)
            .limit(limit)
        )
        rows = self._session.execute(stmt).scalars().all()
        return [to_user_entity(row) for row in rows]

    def find_contact(
        self, user_a: UUID, user_b: UUID
    ) -> UserContactEntity | None:
        stmt = select(UserContactOrm).where(
            or_(
                (UserContactOrm.requester_user_id == user_a)
                & (UserContactOrm.target_user_id == user_b),
                (UserContactOrm.requester_user_id == user_b)
                & (UserContactOrm.target_user_id == user_a),
            )
        )
        row = self._session.execute(stmt).scalars().first()
        return to_user_contact_entity(row) if row is not None else None

    def find_contact_by_id(self, contact_id: UUID) -> UserContactEntity | None:
        row = self._session.get(UserContactOrm, contact_id)
        return to_user_contact_entity(row) if row is not None else None

    def create_contact_request(
        self, requester_id: UUID, target_id: UUID, note: str | None
    ) -> UserContactEntity:
        """신청 생성과 알림 생성을 **같은 트랜잭션**에서 커밋한다.

        `notification` 은 남의 테이블이라(위 `_notification` 참고) 원시 INSERT 로
        쓴다 — `id`·`created_at` 은 여기서 채운다(그 컨텍스트의 리포지토리를
        거치지 않으므로 기본값이 안 붙는다).
        """
        now = datetime.now(timezone.utc)
        contact_row = UserContactOrm(
            id=uuid4(),
            requester_user_id=requester_id,
            target_user_id=target_id,
            note=note,
            accepted_at=None,
            created_at=now,
        )
        self._session.add(contact_row)
        try:
            self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            if _is_unique_violation(exc):
                raise ApiError(
                    409, "ALREADY_REQUESTED", "이미 신청했거나 지인인 사이입니다."
                ) from exc
            raise

        self._session.execute(
            insert(_notification).values(
                id=uuid4(),
                recipient_user_id=target_id,
                type=_NOTIFY_CONTACT_REQUEST,
                actor_user_id=requester_id,
                subject_type=_SUBJECT_USER_CONTACT,
                subject_id=contact_row.id,
                read_at=None,
                created_at=now,
            )
        )
        self._session.commit()
        return to_user_contact_entity(contact_row)

    def accept_contact_request(self, contact_id: UUID) -> UserContactEntity:
        row = self._session.get(UserContactOrm, contact_id)
        now = datetime.now(timezone.utc)
        row.accepted_at = now
        self._session.execute(
            insert(_notification).values(
                id=uuid4(),
                recipient_user_id=row.requester_user_id,
                type=_NOTIFY_CONTACT_ACCEPTED,
                actor_user_id=row.target_user_id,
                subject_type=_SUBJECT_USER_CONTACT,
                subject_id=row.id,
                read_at=None,
                created_at=now,
            )
        )
        self._session.commit()
        self._session.refresh(row)
        return to_user_contact_entity(row)

    def list_accepted_contacts(self, user_id: UUID) -> list[UserContactSummary]:
        """상대방을 평평하게 조인해 온다. `note`는 내가 신청자일 때만 싣는다."""
        as_requester = self._session.execute(
            select(UserContactOrm, UserOrm.nickname)
            .join(UserOrm, UserOrm.id == UserContactOrm.target_user_id)
            .where(UserContactOrm.requester_user_id == user_id)
            .where(UserContactOrm.accepted_at.isnot(None))
        ).all()
        as_target = self._session.execute(
            select(UserContactOrm, UserOrm.nickname)
            .join(UserOrm, UserOrm.id == UserContactOrm.requester_user_id)
            .where(UserContactOrm.target_user_id == user_id)
            .where(UserContactOrm.accepted_at.isnot(None))
        ).all()

        summaries = [
            UserContactSummary(
                contact_id=contact.id,
                user_id=contact.target_user_id,
                nickname=nickname,
                note=contact.note,
                accepted_at=contact.accepted_at,
            )
            for contact, nickname in as_requester
        ] + [
            UserContactSummary(
                contact_id=contact.id,
                user_id=contact.requester_user_id,
                nickname=nickname,
                note=None,
                accepted_at=contact.accepted_at,
            )
            for contact, nickname in as_target
        ]
        summaries.sort(key=lambda s: s.accepted_at, reverse=True)
        # 🔴 **카드 슬러그를 한 번에 채운다**(미결 `paik` 39번). 한 줄씩 따로
        #    읽으면 지인 수만큼 쿼리가 나간다. 카드를 안 만든 사람은 `None` 이고
        #    그때 화면은 이름표로 남는다 — 정상 갈래다.
        slugs = self.card_slugs([s.user_id for s in summaries])
        for s in summaries:
            s.card_public_slug = slugs.get(s.user_id)
        return summaries

    def list_incoming_contact_requests(
        self, user_id: UUID
    ) -> list[UserContactEntity]:
        stmt = (
            select(UserContactOrm)
            .where(UserContactOrm.target_user_id == user_id)
            .where(UserContactOrm.accepted_at.is_(None))
            .order_by(UserContactOrm.created_at.desc())
        )
        rows = self._session.execute(stmt).scalars().all()
        return [to_user_contact_entity(row) for row in rows]
