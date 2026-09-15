"""`notification`. 부록 D 도메인 ①. 미결 `jin` 35번."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class NotificationEntity:
    """알림 1건.

    **문구를 저장하지 않는다.** `type`+`actor_user_id`+`subject_type`으로 클라이언트가
    렌더링한다 — 렌더링된 문장은 파생값이라 부록 D 정규화 원칙(제3정규형, D.4)에
    맞지 않는다. `actor_user_id`는 알림을 유발한 사람(없을 수 있다 — 시스템이
    직접 만드는 알림도 나중에 생길 수 있어 nullable). `subject_type`+`subject_id`는
    이 알림이 가리키는 대상(예: `user_contact` 행 하나)인데, 타입마다 대상
    테이블이 달라 **FK를 걸지 않는다**(컨텍스트 경계 — 아래 포트 참고).
    """

    id: UUID
    recipient_user_id: UUID
    type: str
    actor_user_id: UUID | None
    subject_type: str | None
    subject_id: UUID | None
    read_at: datetime | None
    created_at: datetime

    @property
    def is_read(self) -> bool:
        return self.read_at is not None
