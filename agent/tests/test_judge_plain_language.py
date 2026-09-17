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


# -- 단위 (2회차, 2026.09.16) ------------------------------------------------
#
#    1회차는 단위를 **일부러 뺐다** — 계약의 `unit` 이 `s` 인데 `features` 의 값은
#    프레임이라, 그대로 붙이면 9프레임이 「9초」가 되기 때문이다. 🔴 **그런데 빼는
#    것으로는 안 막혔다.** 2회차 실측(EXAONE 1.2B, 120문장): 값을 언급한 21건 중
#    **15건(71%)** 이 초·분을 붙였다 — 「지속 시간: 9」가 단위를 부르는 문장이라
#    모델이 가장 그럴듯한 것을 지어냈다. 참인 단위를 주니 **0건**이 됐고 프레임
#    표기가 0 → 23 이 됐다(`before_units.csv` · `after_units.csv`).


def _frame_metrics():
    from supersub_agent.judge import metric_units
    return [c for c, u in metric_units().items() if u == "프레임"]


def test_frame_valued_metrics_are_declared_as_frames_not_seconds():
    """🔴 계약의 `unit: s` 를 그대로 믿으면 안 된다.

    `emitted_from: frame_metrics_seconds` 는 **환산을 거쳐야 초가 된다**는
    선언이다 — `features` 안에서는 프레임이다. 이 구분이 무너지면 프롬프트가
    다시 「12초」를 부른다.
    """
    assert "follow_through_duration_frames" in _frame_metrics()
    assert "impact_frame" in _frame_metrics()


@pytest.mark.parametrize("key,criterion", list(_all_criteria()))
def test_every_number_in_the_prompt_carries_its_unit(key, criterion):
    """측정값 줄의 숫자에는 **참인 단위**가 붙어 있어야 한다.

    붙어 있지 않으면 모델이 지어낸다 — 그것이 이 회차가 고친 결함이다.
    """
    from supersub_agent.judge import metric_units

    metrics = {m: 12 for m in criterion.measured_by}
    prompt = build_prompt(criterion, metrics, 1)
    for code in criterion.measured_by:
        unit = metric_units().get(code, "")
        if not unit:  # ratio 는 무차원이라 일부러 안 붙인다
            continue
        assert f"12{unit}" in prompt, (
            f"{key}/{criterion.id}: {code} 의 값에 단위 「{unit}」가 없다 — "
            "맨 숫자를 주면 모델이 단위를 지어낸다"
        )


@pytest.mark.parametrize("key,criterion", list(_all_criteria()))
def test_the_prompt_never_calls_a_frame_count_a_second(key, criterion):
    """🔴 실물 결함 그대로 — 프레임 값에 「초」가 붙으면 안 된다."""
    metrics = {m: 12 for m in criterion.measured_by}
    prompt = build_prompt(criterion, metrics, 1)
    assert not re.search(r"12\s*초", prompt), f"{key}/{criterion.id}: 프레임을 초로 적었다"


@pytest.mark.parametrize("key,criterion", list(_all_criteria()))
def test_the_anchors_use_the_same_ruler_as_the_measurement(key, criterion):
    """🔴 앵커와 측정값이 **같은 자**여야 한다.

    측정값만 단위를 붙이면 모델이 두 다른 자를 나란히 보게 된다. (같은 이유로
    측정값을 초로 환산하는 것도 안 된다 — 앵커가 프레임이고, 그 앵커가 어느
    fps 격자에서 매겨졌는지는 미결 7번이 아직 안 닫았다.)

    🔴 **앵커마다 자기 자리에서 본다** (2026.09.17, 미결 23번 가-3). 전에는
    프롬프트 하나를 만들어 **모든 앵커**가 거기 있다고 보았는데, 이제
    판정 등급의 앵커는 **값이 앉은 조각의 것만** 실린다(양방향 구간에서
    반대 방향 예시가 모델을 끌고 가서다). 그래서 앵커마다 **그 앵커의 값으로**
    프롬프트를 만들어 본다 — 검사의 목적(같은 자를 쓰는가)은 그대로고,
    오히려 **앵커 하나하나가 실제로 실리는지**까지 함께 본다.
    """
    from supersub_agent.judge import metric_units

    for anchor in criterion.anchors or []:
        metrics = {m: 12 for m in criterion.measured_by}
        metrics.update(anchor["measured"])
        prompt = build_prompt(criterion, metrics, int(anchor["grade"]))
        for code, value in anchor["measured"].items():
            unit = metric_units().get(code, "")
            if unit:
                assert f"{value}{unit}" in prompt, (
                    f"{key}/{criterion.id}: 앵커 {code}={value} 에 단위가 없다"
                )
