"""평가·신뢰 규칙. **HTTP도 DB도 없다.**

패킷 B 문서가 「정해야 할 것」으로 남겨 둔 셋을 여기서 정한다. 값 자체보다
**왜 그 값인지**가 중요하다 — 나중에 바꿀 때 근거를 보고 바꾸라고 적어 둔다.

🔴 **정어진이 2026-09-04 에 정했다. 박민호(PM) 판단이 다르면 여기만 고치면 된다** —
숫자와 권한이 전부 이 모듈에 모여 있고 응용 계층은 이걸 부르기만 한다.
"""

from __future__ import annotations

from datetime import datetime, timedelta

# --- 평가 가능 기간 ---------------------------------------------------------
# 🔴 **경기 후 14일.**
#
# 7일도 후보였지만 용병 경기는 주말에 몰린다 — 토요일 경기를 다음 주말에야 열어
# 보는 사람이 7일이면 놓친다. 무기한은 반대로 **기억이 흐려진 평가**를 받는데,
# 평가가 신뢰도의 원자료(D.4)라 그건 값의 질을 떨어뜨린다.
REVIEW_WINDOW = timedelta(days=14)


def reviewable_at(played_at: datetime, now: datetime) -> bool:
    """지금 이 경기를 평가할 수 있는가.

    **경기가 끝난 뒤부터** 열린다. 경기 전 평가는 뜻이 없고, `played_at` 이
    미래인 동안은 아직 뛰지 않았다.
    """
    return played_at < now <= played_at + REVIEW_WINDOW


def within_window(played_at: datetime, now: datetime) -> bool:
    """기간이 지났는지만 본다 — 경기가 끝났는지는 `reviewable_at` 이 본다."""
    return now <= played_at + REVIEW_WINDOW


# --- 불참 기록 권한 ---------------------------------------------------------
# 🔴 **주최 팀 주장만.**
#
# `no_show` 는 제재 기록이라(3.5) 만들 수 있는 사람을 좁힌다. 참가자 누구나
# 기록하게 두면 사이가 틀어진 상대에게 서로 붙일 수 있고, **스키마에 기록자
# 컬럼이 없어**(부록 D) 나중에 누가 붙였는지도 못 따진다.
#
# 경기 취소·지원 거절과 같은 기준이다 — 팀의 결정은 주장이 한다.


# 🔴 `app.match` 의 `OWNER_ROLE` 을 임포트하지 않는다 — 컨텍스트끼리 직접
#    임포트하면 아키텍처 검사가 막는다(`fastapi/CLAUDE.md`). 값이 겹치는 것은
#    **`team_member.role` 이라는 DB 값을 양쪽이 각자 읽기 때문**이지 코드를
#    공유해서가 아니다. 저쪽이 이 값을 바꾸면 여기도 바뀌어야 한다.
OWNER_ROLE = "owner"


def can_record_no_show(team_role: str | None) -> bool:
    return team_role == OWNER_ROLE


# --- 자기 평가 -------------------------------------------------------------
# ⚠️ 부록 D 에도 패킷 B 문서에도 명시가 없다. 스키마로 막지 않았으므로
#    응용에서 막는다 — 자기를 평가한 값은 신뢰도 집계에서 뜻이 없다.


def is_self_review(reviewer_id, reviewee_id) -> bool:
    return reviewer_id == reviewee_id
