"""팀 안에서의 역할."""

from __future__ import annotations

from enum import Enum


class TeamRole(str, Enum):
    """`team_member.role` 의 값.

    ⚠️ **부록 D 는 이 값을 열거하지 않는다.** 컬럼은 `String(20)` 자유 문자열이다.
    그래서 문서에 없는 제약을 DB 로 늘리지 않고 **앱이 쓰는 집합만** 여기서 정한다.
    기존 데이터(시드·스텁)가 쓰던 `member` 를 그대로 두고 `owner` 만 더했다.

    `owner` 는 팀을 만든 사람이다. 지금 스키마에는 소유권 이양이 없으므로
    (`team` 에 소유자 컬럼이 없고 역할만 있다) **마지막 owner 는 나갈 수 없다**
    — `team_rules.is_last_owner` 를 볼 것.
    """

    OWNER = "owner"
    MEMBER = "member"

    def __str__(self) -> str:
        return self.value
