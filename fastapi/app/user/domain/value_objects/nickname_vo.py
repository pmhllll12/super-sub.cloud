"""닉네임 값 객체."""

from __future__ import annotations

from dataclasses import dataclass

# 카드에 표시되는 값이라 상한이 필요한데 근거 문서가 없어서 정했다.
MAX_NICKNAME_LENGTH = 20


@dataclass(frozen=True)
class Nickname:
    value: str

    @classmethod
    def of(cls, raw: str) -> Nickname:
        return cls(raw.strip())

    def __str__(self) -> str:
        return self.value
