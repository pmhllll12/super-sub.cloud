"""스쿼드 규칙. **HTTP도 DB도 없다.**"""

from __future__ import annotations

# `team_member.role` 의 값은 `user` 컨텍스트가 정한다. **여기서 임포트할 수 없어서**
# (컨텍스트 경계) 문자열로 받는다 — 저쪽이 값을 바꾸면 여기가 조용히 틀린다.
# 그래서 `tests/card/adapter/test_squad_db.py` 가 실제 가입으로 이 값을 확인한다.
#
# ⚠️ `app/match/domain/rules/match_rules.py` 에도 같은 상수가 있다. 가져오지 않는
# 이유는 컨텍스트끼리 임포트하지 않기 때문이고, 둘이 갈리면 DB 검사가 잡는다.
OWNER_ROLE = "owner"


def can_manage(team_role: str | None) -> bool:
    """스쿼드를 만들고 카드를 등재·제외할 수 있는가. **주장만 할 수 있다.**

    스쿼드는 공개 슬러그로 밖에 보이는 **팀의 얼굴**이다(SFR-009 의 카드가 개인의
    얼굴인 것과 같다). 팀을 대표하는 행위라 경기 등록과 같은 기준을 쓴다.

    소속이 아니면 `team_role` 이 None 이고, 그것도 할 수 없다는 뜻이다.
    """
    return team_role == OWNER_ROLE


def can_read(team_role: str | None) -> bool:
    """팀 스쿼드를 팀 화면에서 볼 수 있는가. **소속이면 된다.**

    공개 슬러그로는 누구나 볼 수 있으므로 이 검사는 비밀을 지키는 것이 아니라,
    **팀 id 로 남의 팀 구성을 훑는 것**을 막는 것이다. 슬러그는 96비트 난수라
    추측할 수 없지만 팀 id 는 다른 경로에서 새어 나올 수 있다.
    """
    return team_role is not None
