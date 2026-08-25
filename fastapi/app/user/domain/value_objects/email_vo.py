"""이메일 값 객체."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Email:
    """정규화된 이메일.

    `user.email` 에 유일 제약이 걸려 있으므로(부록 D.7) 대소문자만 다른 값이
    별개 계정이 되면 안 된다. **생성 시점에 한 번 정규화하고 그 뒤로는 믿는다** —
    이렇게 두면 "어디선가 lower() 를 빼먹는" 일이 구조적으로 안 생긴다.
    """

    value: str

    @classmethod
    def of(cls, raw: str) -> Email:
        return cls(raw.strip().lower())

    def __str__(self) -> str:
        return self.value
