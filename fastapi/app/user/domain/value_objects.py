"""사용자 컨텍스트의 값 객체.

값 자체가 규칙을 들고 있게 한다. 예를 들어 이메일 정규화를 여기 두면
"어디선가는 `lower()`를 빼먹는" 일이 생기지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass

# 계약 문서 2장. 대문자·특수문자는 강제하지 않는다 — 사용자를 예측 가능한
# 패턴으로 몰 뿐이다. 5장 요구사항이 비어 있어 최소한만 건다.
MIN_PASSWORD_LENGTH = 8

# 카드에 표시되는 값이라 상한이 필요한데 근거 문서가 없어서 정했다.
MAX_NICKNAME_LENGTH = 20


@dataclass(frozen=True)
class Email:
    """정규화된 이메일.

    `user.email` 에 유일 제약이 걸려 있으므로(부록 D.7) 대소문자만 다른 값이
    별개 계정이 되면 안 된다. **생성 시점에 한 번 정규화하고 그 뒤로는 믿는다.**
    """

    value: str

    @classmethod
    def of(cls, raw: str) -> Email:
        return cls(raw.strip().lower())

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Nickname:
    value: str

    @classmethod
    def of(cls, raw: str) -> Nickname:
        return cls(raw.strip())

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Password:
    """평문 비밀번호. **저장하지 않는다** — 검증에만 쓴다.

    DB 가 붙으면 여기서 bcrypt 해시를 만들어 `user_credential.password_hash` 로
    넘긴다. 지금은 저장할 곳이 없어 해싱하지 않는다.
    """

    value: str

    def is_acceptable(self) -> bool:
        return len(self.value) >= MIN_PASSWORD_LENGTH
