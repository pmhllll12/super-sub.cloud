"""`user_title` + `title_definition` 에 대응하는 엔티티. 부록 D 도메인 ③."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.card.domain.value_objects.title_category_vo import TitleCategory


@dataclass(frozen=True)
class TitleEntity:
    """한 사람이 받은 호칭 1개.

    **부여된 것만 존재한다.** 미달을 `False` 로 담지 않는다 — `user_title` 에
    부여된 행만 넣는 스키마 설계와 짝이다(3.5). 미달을 값으로 표시하면 그 순간
    부정 표식이 된다.
    """

    code: str
    label: str
    #: 🔴 **사람이 직접 적은 호칭은 `None` 이다**(`paik` 36번, 2026-09-16).
    #: 분류는 부록 D 가 정의한 셋뿐이고 그건 **부여되는 호칭**의 것이다 —
    #: 사람이 적은 글에 분류를 매길 사람이 없어서(그 항목의 「하지 말 것」)
    #: 새 분류를 만드는 대신 비워 둔다.
    category: TitleCategory | None
    granted_at: datetime
