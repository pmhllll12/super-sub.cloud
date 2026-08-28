"""출력 포트.

유스케이스가 **저장소의 구현을 모르게** 하는 경계다. 지금은 스텁이 이 자리에
들어가고 DB 가 생기면 PostgreSQL 구현이 들어간다 — 유스케이스는 고치지 않는다.

포트는 **엔티티와 값 객체로 말한다.** DTO 는 인바운드 쪽 경계용이라 여기서 쓰지 않는다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.user.domain.entities.membership_entity import MembershipEntity
from app.user.domain.entities.user_entity import UserEntity
from app.user.domain.value_objects.email_vo import Email
from app.user.domain.value_objects.nickname_vo import Nickname
from app.user.domain.value_objects.password_vo import Password


class UserPort(ABC):
    @abstractmethod
    def email_exists(self, email: Email) -> bool:
        """이미 가입된 이메일인지."""

    @abstractmethod
    def create(self, user: UserEntity, password: Password) -> None:
        """사용자와 자격증명을 함께 저장한다.

        **평문 비밀번호를 받는다.** 어떻게 보관할지(해싱 방식)는 저장소의 사정이지
        유스케이스가 알 일이 아니다 — 알고리즘을 바꿔도 이 위쪽은 그대로다.

        이메일이 이미 있으면 409 로 떨어진다. 유스케이스가 `email_exists` 로 먼저
        확인하지만, 동시 요청 두 건은 그 검사만으로 막지 못하므로 저장소도 막는다.
        """

    @abstractmethod
    def find_by_credentials(
        self, email: Email, password: Password
    ) -> UserEntity | None:
        """자격증명이 맞으면 사용자를, 아니면 None 을 돌려준다.

        **왜 틀렸는지는 알려주지 않는다** — 호출 쪽이 구분하지 못하게 해서
        가입 여부가 새어 나가는 것을 막는다.
        """

    @abstractmethod
    def find_by_identity(self, provider: str, subject: str) -> UserEntity | None:
        """외부 제공자 계정에 연결된 사용자. 없으면 None.

        **이메일이 아니라 `subject` 로 찾는다** — 이메일은 바뀔 수 있다.
        """

    @abstractmethod
    def find_by_email(self, email: Email) -> UserEntity | None:
        """이메일로 사용자를 찾는다. 외부 신원을 기존 계정에 연결할 때만 쓴다."""

    @abstractmethod
    def link_identity(self, user_id: UUID, provider: str, subject: str) -> None:
        """기존 사용자에게 외부 계정을 연결한다."""

    @abstractmethod
    def create_with_identity(
        self, user: UserEntity, provider: str, subject: str
    ) -> None:
        """외부 계정으로 처음 들어온 사람을 만든다.

        **비밀번호가 없다.** `user_credential` 행을 만들지 않으므로 이 계정은
        비밀번호 로그인이 불가능하다 — 나중에 비밀번호를 설정하는 기능이 생기면
        그때 자격증명을 추가한다.
        """

    @abstractmethod
    def get(self, user_id: UUID) -> UserEntity | None: ...

    @abstractmethod
    def update_nickname(self, user_id: UUID, nickname: Nickname) -> None:
        """닉네임을 바꾼다. 없는 사용자면 아무 일도 하지 않는다.

        존재 확인은 유스케이스가 이미 한다(없으면 401). 여기서 또 던지면 같은
        판단이 두 곳에 생긴다.
        """

    @abstractmethod
    def change_password(self, user_id: UUID, password: Password) -> None:
        """비밀번호를 바꾼다. **평문을 받는다** — 해싱은 저장소의 사정이다(`create` 와 같다).

        비밀번호가 없던 계정(구글로만 가입)에 부르면 자격증명을 새로 만든다.
        """

    @abstractmethod
    def has_password(self, user_id: UUID) -> bool:
        """비밀번호 자격증명이 있는 계정인지.

        구글로만 가입한 계정에는 없다. 탈퇴할 때 **비밀번호를 요구할지 가르는 기준**이라
        "자격증명 조회 실패"와 구분해야 한다 — 둘을 합치면 소셜 계정이 탈퇴할 수 없다.
        """

    @abstractmethod
    def delete(self, user_id: UUID) -> None:
        """계정을 지운다. **파생 데이터는 외래키 연쇄가 함께 지운다**(부록 D.6).

        연쇄를 코드로 짜지 않는 이유는 삭제 경로가 늘 때마다 빠뜨리기 때문이다.
        어떤 테이블이 따라 지워지는지는 스키마가 정본이다.
        """

    @abstractmethod
    def bump_token_version(self, user_id: UUID) -> None:
        """그 사용자의 토큰 버전을 1 올린다 — **기존 토큰이 전부 무효가 된다**(SEC-004).

        읽고 더해서 쓰지 않고 **DB 안에서 증가시킨다.** 동시에 두 번 불려도 값이
        덮이지 않아야 하고, 폐기는 한 번이라도 덜 되면 의미가 없다.
        """

    @abstractmethod
    def list_memberships(self, user_id: UUID) -> list[MembershipEntity]:
        """탈퇴 이력을 포함한 전체 소속. 거르는 것은 도메인 규칙의 몫이다."""
