"""경기 조건(`paik` 18번) 검증 규칙. **HTTP도 DB도 없다.**"""

from __future__ import annotations

from datetime import time

# `team_member.role` 값은 `user` 컨텍스트가 정한다 — `match_rules.py`와 같은
# 이유로 문자열 상수를 복제한다(임포트 금지, 저쪽이 값을 바꾸면 DB 테스트가 잡는다).
OWNER_ROLE = "owner"

MIN_WEEKDAY = 0
MAX_WEEKDAY = 6


def is_valid_slot(weekday: int, start: time, end: time) -> bool:
    """요일 0~6, **시작이 끝보다 앞이어야 한다.**

    🔴 뒤집힌 시간을 받으면 겹침 계산에서 **늘 거짓**이 되어 조용히 아무것도
    안 걸린다(`paik` 18번이 명시한 사고) — 그래서 저장 전에 거부한다.
    """
    if not (MIN_WEEKDAY <= weekday <= MAX_WEEKDAY):
        return False
    return start < end


def overlap_minutes(
    a_weekday: int,
    a_start: time,
    a_end: time,
    b_weekday: int,
    b_start: time,
    b_end: time,
) -> int:
    """두 시간대가 겹치는 분. 요일이 다르면 0(`paik` 20번 소프트 근거)."""
    if a_weekday != b_weekday:
        return 0
    start = max(a_start, b_start)
    end = min(a_end, b_end)
    if start >= end:
        return 0
    start_minutes = start.hour * 60 + start.minute
    end_minutes = end.hour * 60 + end.minute
    return end_minutes - start_minutes


def region_tier(
    a_city: str, a_district: str, b_city: str, b_district: str
) -> str:
    """지역 계층 — `district`(같은 구) > `city`(같은 시) > `none`(그 외).

    `paik` 20번 정상호 회신 그대로: 문자열 완전일치가 아니라 3단계다.
    """
    if a_city == b_city and a_district == b_district:
        return "district"
    if a_city == b_city:
        return "city"
    return "none"
