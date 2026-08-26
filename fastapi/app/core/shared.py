"""컨텍스트가 공유하는 최소한의 것.

여기에 도메인 규칙을 넣지 않는다 — 규칙은 각 컨텍스트의 `domain.py`에 둔다.
이 파일은 직렬화 형식처럼 **어느 컨텍스트에도 속하지 않는 것**만 담는다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from pydantic import PlainSerializer


def _rfc3339(dt: datetime) -> str:
    """`2026-08-25T10:30:00Z` 형태로 낸다.

    기본 직렬화는 `+00:00`으로 끝난다. 둘 다 RFC 3339 로 유효하지만 계약 문서에
    `Z`로 적어 두었으므로 문서와 응답을 맞춘다.
    """
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


Rfc3339 = Annotated[datetime, PlainSerializer(_rfc3339, return_type=str)]
