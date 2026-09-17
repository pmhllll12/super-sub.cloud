"""과금 규칙. **HTTP도 DB도 없다.**

패킷 A 문서(`docs/backend-work-split.md`)가 「정해야 할 것」으로 남겨 둔 셋
(무료 크레딧 지급 시점·액수, 분석 1건당 차감액, `reason` 값 목록)은 여기서
정하지 않는다 — 정책은 박민호(PM)·사용자와 함께 정할 값이지 지금 구조를 막는
것이 아니다(패킷 A 문서 「정해지기 전에도 테이블과 조회는 만들 수 있습니다」).

여기서 정하는 것은 **구조가 무너지지 않기 위한 최소 제약**뿐이다.
"""

from __future__ import annotations


def is_valid_delta(delta: int) -> bool:
    """0인 증감은 뜻이 없다 — 지급도 차감도 아닌 행은 이력을 오염시킨다."""
    return delta != 0


def is_valid_fee(fee) -> bool:
    """코치 연결 수수료는 음수일 수 없다. 0(무료 연결)은 허용한다."""
    return fee >= 0
