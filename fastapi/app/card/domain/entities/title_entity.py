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
    category: TitleCategory
    granted_at: datetime
