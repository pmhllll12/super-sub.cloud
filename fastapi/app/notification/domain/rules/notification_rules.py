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

KNOWN_TYPES = frozenset({CONTACT_REQUEST, CONTACT_ACCEPTED})
