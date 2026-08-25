"""가입 유스케이스가 주고받는 DTO.

**계층을 건너는 데이터는 전부 여기를 지난다.** 라우터는 엔티티를 모르고 도메인은
HTTP 를 모른다. 그래서 값 객체가 아니라 **원시 타입**으로만 담는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class SignupCommand:
    """인바운드 → 유스케이스."""

    email: str
    password: str
    nickname: str


@dataclass(frozen=True)
class SignupResult:
    """유스케이스 → 인바운드."""

    id: UUID
    email: str
    nickname: str
    created_at: datetime
