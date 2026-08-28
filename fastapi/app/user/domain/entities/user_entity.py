"""`user` 테이블에 대응하는 엔티티. 부록 D 도메인 ①."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.user.domain.value_objects.email_vo import Email
from app.user.domain.value_objects.nickname_vo import Nickname


@dataclass(frozen=True)
class UserEntity:
    """가입한 사람 1명.

    자격증명은 여기 없다 — `user_credential` 로 분리했다. `user` 는 거의 모든
    테이블이 조인하는 허브라 해시가 여기 있으면 무심코 조회될 여지가 생긴다.
    """

    id: UUID
    email: Email
    nickname: Nickname
    created_at: datetime
    # 발급한 토큰을 무효로 만들 때 올리는 값(SEC-004). 새 계정은 0 에서 시작한다.
    token_version: int = 0
