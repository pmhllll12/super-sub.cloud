"""비밀번호 값 객체."""

from __future__ import annotations

from dataclasses import dataclass

# 계약 문서 2장. 대문자·특수문자는 강제하지 않는다 — 사용자를 예측 가능한
# 패턴으로 몰 뿐이다. 5장 요구사항이 비어 있어 최소한만 건다.
MIN_PASSWORD_LENGTH = 8


@dataclass(frozen=True)
class Password:
    """평문 비밀번호. **저장하지 않는다** — 검증에만 쓴다.

    DB 가 붙으면 여기서 bcrypt 해시를 만들어 `user_credential.password_hash` 로
    넘긴다. 지금은 저장할 곳이 없어 해싱하지 않는다.
    """

    value: str

    def is_acceptable(self) -> bool:
        return len(self.value) >= MIN_PASSWORD_LENGTH
