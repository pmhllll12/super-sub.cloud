"""내 정보 유스케이스가 주고받는 DTO."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final
from datetime import datetime
from uuid import UUID


# 자리표시자 — `app.card.application.dtos.card_dto.UNSET`과 같은 판단(컨텍스트끼리
# 임포트하지 않으므로 공용으로 두지 않고 컨텍스트마다 따로 정의한다). `None`은
# "지운다"는 뜻으로 이미 쓰이는 필드가 있을 수 있어 "안 보냄"과 구분해야 한다.
UNSET: Final[Any] = object()


@dataclass(frozen=True)
class MeQuery:
    user_id: UUID


@dataclass(frozen=True)
class UpdateMeCommand:
    """인바운드 → 유스케이스.

    결과는 조회와 **같은 `MeResult`** 다. 수정 응답만 형태가 다르면 클라이언트가
    파서를 두 벌 들고 있어야 한다.
    """

    user_id: UUID
    nickname: str
    # `UNSET`이면 안 바뀐다. `True`/`False`면 그 값으로 바뀐다(지인 검색 노출 여부).
    is_nickname_searchable: bool | Any = UNSET


@dataclass(frozen=True)
class ChangePasswordCommand:
    """비밀번호 변경. **현재 비밀번호를 함께 받는다** — 토큰만으로는 바꿀 수 없다."""

    user_id: UUID
    current_password: str
    new_password: str


@dataclass(frozen=True)
class DeleteMeCommand:
    """탈퇴. 비밀번호가 있는 계정만 `password` 를 요구한다."""

    user_id: UUID
    password: str | None = None


@dataclass(frozen=True)
class MembershipResult:
    team_id: UUID
    name: str
    region: str
    sport_code: str
    role: str
    joined_at: datetime


@dataclass(frozen=True)
class MeResult:
    id: UUID
    email: str
    nickname: str
    created_at: datetime
    is_nickname_searchable: bool
    # 지금 소속된 팀만. 거르는 규칙은 domain/rules/membership_rules.py 에 있다.
    teams: list[MembershipResult] = field(default_factory=list)
