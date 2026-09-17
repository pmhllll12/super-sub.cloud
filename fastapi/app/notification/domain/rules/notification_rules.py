"""알림 타입 허용 목록. **HTTP도 DB도 없다.**

참조 테이블로 만들지 않는다 — 종류가 코드 배포마다 늘어나는 값이라 데이터로
두면 마이그레이션 없이 새 값이 들어올 수 있는데, 그건 `type`을 아는 코드
(클라이언트 렌더링)가 항상 코드 배포와 같이 가야 하는 이 값의 성격과 안 맞는다.
"""

from __future__ import annotations

# `user_contact`(user 컨텍스트)가 만드는 알림 두 가지. 새 컨텍스트가 알림을
# 만들 때마다 여기 늘어난다 — 정본은 이 상수이지 흩어진 문자열이 아니다.
CONTACT_REQUEST = "contact_request"
CONTACT_ACCEPTED = "contact_accepted"

# `team_match_request`(match 컨텍스트, `paik` 17번)가 만드는 알림 다섯 가지.
TEAM_MATCH_REQUESTED = "team_match_requested"
TEAM_MATCH_ACCEPTED = "team_match_accepted"
TEAM_MATCH_REJECTED = "team_match_rejected"
TEAM_MATCH_REQUEST_CANCELLED = "team_match_request_cancelled"
TEAM_MATCH_CANCELLED = "team_match_cancelled"

# `team_invitation`(user 컨텍스트, `min` 20번)가 만드는 알림 세 가지. 무르기
# (cancel)는 보낸 쪽이 스스로 하는 것이라 알림이 없다(`team_match_request`의
# `cancel`과 같은 판단).
TEAM_INVITATION_SENT = "team_invitation_sent"
TEAM_INVITATION_ACCEPTED = "team_invitation_accepted"
TEAM_INVITATION_REJECTED = "team_invitation_rejected"

KNOWN_TYPES = frozenset(
    {
        CONTACT_REQUEST,
        CONTACT_ACCEPTED,
        TEAM_MATCH_REQUESTED,
        TEAM_MATCH_ACCEPTED,
        TEAM_MATCH_REJECTED,
        TEAM_MATCH_REQUEST_CANCELLED,
        TEAM_MATCH_CANCELLED,
        TEAM_INVITATION_SENT,
        TEAM_INVITATION_ACCEPTED,
        TEAM_INVITATION_REJECTED,
    }
)
