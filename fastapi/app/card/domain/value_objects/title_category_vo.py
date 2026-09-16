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

    # 🔴 **여기에 값을 더하지 않는다.** `tests/card/domain/test_card_rules.py`
    # 의 「부록 D 가 정의한 셋만 있다」가 이 목록을 부록 D 에 묶어 둔다.
    # 사람이 직접 적는 호칭(`paik` 36번)은 분류가 **없다** — 새 분류를
    # 만드는 대신 `TitleEntity.category` 를 `None` 으로 둔다(2026-09-16).
