"""경기 등록 규칙. **HTTP도 DB도 없다.**"""

from __future__ import annotations

from datetime import datetime

# `team_member.role` 의 값은 `user` 컨텍스트가 정한다. **여기서 임포트할 수 없어서**
# (컨텍스트 경계) 문자열로 받는다 — 저쪽이 값을 바꾸면 여기가 조용히 틀린다.
# 그래서 `tests/match/adapter/test_match_db.py` 가 실제 가입으로 이 값을 확인한다.
OWNER_ROLE = "owner"


def can_register(team_role: str | None) -> bool:
    """경기를 등록할 수 있는가. **주장만 할 수 있다.**

    경기 등록은 팀을 대표하는 행위다 — 상대 팀·지원자에게 이 팀의 약속이 된다.
    소속이 아니면 `team_role` 이 None 이고, 그것도 등록할 수 없다는 뜻이다.
    """
    return team_role == OWNER_ROLE


def is_registrable(played_at: datetime, now: datetime) -> bool:
    """지난 경기는 등록하지 않는다.

    이 테이블의 목적은 **모집**이다(SFR-010 — 필요 포지션과 인원을 함께 적는다).
    이미 끝난 경기를 등록하면 지원할 수 없는 모집 글이 남는다.

    ⚠️ 스키마가 막는 것이 아니라 **앱이 정한 규칙**이다. 기록용으로 지난 경기를
    넣어야 할 일이 생기면 여기를 고치면 된다.
    """
    return played_at > now
