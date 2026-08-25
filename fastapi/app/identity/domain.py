"""사용자·팀 도메인 규칙.

**여기에는 HTTP도 DB도 없다.** 순수 함수라 서버를 띄우지 않고 테스트한다.
부록 D 도메인 ①(user · user_credential · team_member)에 대응한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

# 계약 문서 2장. 대문자·특수문자는 강제하지 않는다 — 사용자를 예측 가능한
# 패턴으로 몰 뿐이다. 5장 요구사항이 비어 있어 최소한만 건다.
MIN_PASSWORD_LENGTH = 8

# 닉네임 상한. 카드에 표시되는 값이라 상한이 필요한데 근거 문서가 없어서 정했다.
MAX_NICKNAME_LENGTH = 20


@dataclass(frozen=True)
class Membership:
    """team_member 한 행. left_at 이 채워져 있으면 나간 소속이다."""

    team_id: UUID
    name: str
    region: str
    sport_code: str
    role: str
    joined_at: datetime
    left_at: datetime | None


def normalize_email(raw: str) -> str:
    """이메일을 저장·비교하기 전에 통일한다.

    `user.email`에 유일 제약이 걸려 있으므로(부록 D.7) 대소문자만 다른 값이
    별개 계정이 되면 안 된다.
    """
    return raw.strip().lower()


def active_memberships(memberships: list[Membership]) -> list[Membership]:
    """지금 소속된 팀만 남긴다.

    team_member 는 탈퇴해도 행이 남는다 — 경기·평가 이력이 참조하기 때문에
    left_at 으로 소프트 삭제한다(부록 D 도메인 ①). **거르지 않으면 나간 팀이
    내 정보에 그대로 나온다.**
    """
    return [m for m in memberships if m.left_at is None]


def is_password_acceptable(password: str) -> bool:
    return len(password) >= MIN_PASSWORD_LENGTH
