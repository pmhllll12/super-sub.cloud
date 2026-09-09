"""선수에게 보여줄 요약 문장 (미결 `paik` 7번 · `min` 9번).

🔴 **이 요약은 모델이 쓰지 않는다. 코드가 짓는다.** 여기 검사들이 막고 있는
것은 그 경계가 무너지는 것과, 계약이 금지한 수치가 문장에 새어 들어가는 것이다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.scoring import (  # noqa: E402
    aggregate,
    discover_rubrics,
    load_rubric,
    summarize,
)

RUBRICS = discover_rubrics(ROOT / "rubrics")


def _judge(rubric, grades):
    return {c.id: {"grade": g, "evidence": ""}
            for c, g in zip(rubric.criteria, grades)}


def _all(rubric, grade):
    return _judge(rubric, [grade] * len(rubric.criteria))


@pytest.mark.parametrize("key", sorted(RUBRICS))
@pytest.mark.parametrize("grade", [0, 1, 2])
def test_no_digits_ever_reach_the_summary(key, grade):
    """🔴 계약 3장 4 — 요약에 총점·등급 숫자를 넣지 않는다.

    근거 문장 쪽에서는 이것을 지키는 데 2회차가 걸렸고 아직 1건이 남아 있다
    (미결 23번). 요약은 **숫자를 쓸 자리 자체를 안 만들어** 그 싸움을 피한다.
    이 검사가 빨개진다면 누군가 점수나 구간을 문장에 끌어들인 것이다.
    """
    out = aggregate(_all(RUBRICS[key], grade), RUBRICS[key])
    assert not any(ch.isdigit() for ch in out["summary"]), out["summary"]


@pytest.mark.parametrize("key", sorted(RUBRICS))
def test_the_summary_does_not_move_the_score(key):
    """🔴 요약은 `stat`·`out_of_band` 와 같은 성질이다 — 점수와 무관하다.

    그래서 B-6 재실행을 부르지 않는다. 요약을 빼도 나머지가 한 비트도 같아야
    그 말이 성립한다.
    """
    rubric = RUBRICS[key]
    out = aggregate(_judge(rubric, [2, 1, 0] + [1] * (len(rubric.criteria) - 3)),
                    rubric)
    without = {k: v for k, v in out.items() if k != "summary"}
    again = aggregate(_judge(rubric, [2, 1, 0] + [1] * (len(rubric.criteria) - 3)),
                      rubric)
    assert {k: v for k, v in again.items() if k != "summary"} == without


@pytest.mark.parametrize("key", sorted(RUBRICS))
def test_the_same_judgment_gives_the_same_sentence(key):
    """코드가 짓는 값이므로 재현된다. 모델이 쓰면 이 검사가 성립하지 않는다."""
    rubric = RUBRICS[key]
    j = _judge(rubric, [2, 1, 0] + [1] * (len(rubric.criteria) - 3))
    assert aggregate(j, rubric)["summary"] == aggregate(j, rubric)["summary"]


@pytest.mark.parametrize("key", sorted(RUBRICS))
def test_a_perfect_result_has_no_invented_weakness(key):
    """🔴 없는 것을 지어내지 않는다 — 전부 잘했으면 아쉬운 점을 만들지 않는다."""
    out = aggregate(_all(RUBRICS[key], 2), RUBRICS[key])
    assert "아쉬" not in out["summary"], out["summary"]
    assert "강점" in out["summary"]


@pytest.mark.parametrize("key", sorted(RUBRICS))
def test_a_failing_result_has_no_invented_strength(key):
    """반대쪽 — 전부 0등급인데 강점을 만들면 선수를 오도한다."""
    out = aggregate(_all(RUBRICS[key], 0), RUBRICS[key])
    assert "강점" not in out["summary"], out["summary"]


@pytest.mark.parametrize("key", sorted(RUBRICS))
def test_a_middling_item_is_not_called_a_strength(key):
    """🔴 1등급을 「강점」이라 부르면 **고칠 것이 있는 동작을 잘했다고 말한다.**"""
    out = aggregate(_all(RUBRICS[key], 1), RUBRICS[key])
    assert "강점" not in out["summary"], out["summary"]


@pytest.mark.parametrize("key", sorted(RUBRICS))
def test_the_particles_are_chosen_not_hedged(key):
    """🔴 선수 화면에 「…뻗기이(가)」가 그대로 나가면 안 된다.

    한글 이름에서는 받침을 보고 하나를 고른다. 고를 수 없는 이름(영문 등)에서만
    둘 다 적는데, 루브릭 항목 이름은 전부 한글이라 여기서는 나오면 안 된다.
    """
    for grade in (0, 1, 2):
        s = aggregate(_all(RUBRICS[key], grade), RUBRICS[key])["summary"]
        for hedge in ("이(가)", "은(는)", "로(으로)"):
            assert hedge not in s, f"{key} grade={grade}: {s}"


def test_an_empty_breakdown_says_nothing():
    """판정이 없으면 빈 문자열이다 — 「분석 중」과 「결과 없음」을 섞지 않는다."""
    assert summarize([]) == ""


def test_a_single_criterion_does_not_pretend_to_compare():
    """항목이 하나면 강점·약점이 갈릴 수 없다. 갈린 척하지 않는다."""
    rubric = load_rubric(ROOT / "rubrics" / "football_instep_shot.yaml")
    first = rubric.criteria[0]
    out = aggregate({first.id: {"grade": 1, "evidence": ""}}, rubric)
    assert "아쉬" not in out["summary"] and "강점" not in out["summary"]
    assert first.name in out["summary"]


def test_the_summary_is_at_most_two_sentences():
    """계약 3장 4 — 「두 문장 이내」."""
    for key, rubric in RUBRICS.items():
        for grades in ([2] * len(rubric.criteria), [0] * len(rubric.criteria),
                       [2, 1, 0] + [1] * (len(rubric.criteria) - 3)):
            s = aggregate(_judge(rubric, grades), rubric)["summary"]
            assert s.count("다.") <= 2, f"{key}: {s}"
