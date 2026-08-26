"""호칭 분류 값 객체."""

from __future__ import annotations

from enum import StrEnum


class TitleCategory(StrEnum):
    """`title_definition.category` (SFR-004).

    부록 D 도메인 ③ 이 강점·활동·용병 셋으로 정의한다. 문자열로 두면 오타가
    조용히 통과하므로 열거형으로 고정한다.
    """

    STRENGTH = "강점"
    ACTIVITY = "활동"
    MERCENARY = "용병"
