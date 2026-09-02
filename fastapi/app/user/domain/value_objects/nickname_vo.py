"""닉네임 값 객체.

**검증하지 않고 정규화만 한다.** 이 패키지의 값 객체가 전부 그렇다 — 형식 검사는
인바운드 스키마가, 길이는 DB 컬럼(`varchar(20)`)이 막는다. 우회해서 넣어도
`StringDataRightTruncation` 이 난다(2026-09-01 실측).

🔴 **여기에 길이 검증을 넣지 말 것.** `Nickname.of` 는 `user_mapper` 가 **DB 에서
읽은 값을 감쌀 때도** 쓴다. 검증을 넣으면 이미 저장된 값 때문에 **조회가 깨진다.**
"""

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
