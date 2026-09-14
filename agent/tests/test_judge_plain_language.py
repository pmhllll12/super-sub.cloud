"""근거 문장 프롬프트에 **코드 심벌이 없는가** (미결 `ho` 43번 ㉱).

🔴 **이 검사를 지우면 결함이 조용히 돌아온다.** 막고 있는 것은 이것이다:

2026-09-11 실서버 저널에 이렇게 나갔다 —

    2등급  차는 다리 뻗기
      측정값 swing_knee_angle_at_impact=151.6로 임팩트 직전 무릎각이 …

`build_prompt` 가 지표 코드를 **JSON 그대로** 넣었고 모델이 그걸 베꼈다.
`build_prompt` 의 docstring 이 이미 같은 논리를 쓴다: 「프롬프트에 없는 숫자는
베껴 쓸 수 없다」. **심벌도 같다** — 그래서 출력이 아니라 **입력**을 검사한다.
결정론적이라 LLM 없이 돈다.

🔴 **여기서 잡히지 않는 것도 적어 둔다**: 루브릭 `grades[g]` 문구가 품고 있는
**구간 숫자**(「140~165도」)는 이 검사가 안 본다. 그건 미결 23번이고 처방이
스키마를 늘려 **지도자 검수(2·34번)에 묶여 있다.** 둘은 다른 결함이다.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from supersub_agent.judge import build_prompt, label_for, metric_labels
from supersub_agent.scoring import discover_rubrics

ROOT = Path(__file__).resolve().parent.parent


def _all_criteria():
    """살아 있는 전 루브릭 × 전 항목 — draft 도 포함한다(승격되면 그대로 나간다)."""
    for key, rubric in sorted(discover_rubrics(str(ROOT / "rubrics")).items()):
        for c in rubric.criteria:
            yield key, c


def test_the_metric_label_source_actually_loads():
    """정본이 안 읽히면 아래 검사가 **공허하게 통과한다** — 먼저 확인한다."""
    labels = metric_labels()
    assert labels, "contracts/metric_definitions.yaml 에서 라벨을 하나도 못 읽었다"
    assert labels.get("swing_knee_angle_at_impact") == "임팩트 시 주동 무릎 각"


@pytest.mark.parametrize("key,criterion", list(_all_criteria()),
                         ids=lambda v: v if isinstance(v, str) else v.id)
def test_no_metric_code_leaks_into_the_prompt(key, criterion):
    """기준 A — 전 루브릭 × 전 항목 × 전 등급에서 지표 코드가 **0건**."""
    codes = sorted(metric_labels())
    for grade in (0, 1, 2):
        metrics = {m: 1.0 for m in criterion.measured_by}
        prompt = build_prompt(criterion, metrics, grade)
        leaked = [c for c in codes if c in prompt]
        assert not leaked, (
            f"{key}/{criterion.id} {grade}등급 프롬프트에 지표 코드가 있다: {leaked}\n"
            f"모델이 그대로 베껴 쓴다 — 라벨로 바꿀 것"
        )
        # 항목 id 도 코드다 (`swing_knee_extension`).
        assert criterion.id not in prompt, (
            f"{key}/{criterion.id}: 항목 코드가 프롬프트에 있다 — 이름만 넣을 것"
        )


@pytest.mark.parametrize("key,criterion", list(_all_criteria()),
                         ids=lambda v: v if isinstance(v, str) else v.id)
def test_the_label_is_actually_there_instead(key, criterion):
    """기준 B — 코드만 지우고 **아무것도 안 넣는 것**을 막는다.

    코드를 빼는 가장 쉬운 방법은 그 줄을 통째로 지우는 것인데, 그러면 모델이
    무엇을 잰 값인지 모른 채 숫자만 받는다. 라벨이 실제로 들어갔는지 본다.
    """
    prompt = build_prompt(
        criterion, {m: 1.0 for m in criterion.measured_by}, 2)
    for m in criterion.measured_by:
        assert label_for(m) in prompt, (
            f"{key}/{criterion.id}: {m} 의 라벨 「{label_for(m)}」이 프롬프트에 없다"
        )


def test_a_missing_label_never_falls_back_to_the_code():
    """🔴 폴백이 코드이면 유출이 되살아난다 — 그 길을 막는다."""
    assert label_for("no_such_metric_code_at_all") == "측정값"
    assert label_for("no_such_metric_code_at_all", "차는 다리 뻗기") == "차는 다리 뻗기"


def test_the_leak_this_test_was_written_for_is_gone():
    """실서버에 나갔던 그 문장 형태가 다시 만들어지지 않는가.

    회귀 검사라 일반 규칙과 따로 둔다 — 규칙이 바뀌어도 **이 사례**는 남는다.
    """
    rubrics = discover_rubrics(str(ROOT / "rubrics"))
    instep = rubrics["football/instep_shot"]
    c = next(x for x in instep.criteria if x.id == "swing_knee_extension")
    prompt = build_prompt(c, {"swing_knee_angle_at_impact": 151.6}, 2)

    assert "swing_knee_angle_at_impact=151.6" not in prompt
    assert "swing_knee_angle_at_impact" not in prompt
    assert "임팩트 시 주동 무릎 각 151.6" in prompt
    # 🔴 등급 번호는 여전히 없어야 한다 (미결 23번의 처방을 되돌리지 않는다).
    assert "2등급" not in prompt and "등급 2" not in prompt
    assert not re.search(r"\[\s*[012]\s*\]", prompt), "등급 번호가 프롬프트에 있다"
