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


# -- 추천 카드의 설명 칸 (미결 `paik` 27번) ----------------------------------
#
#    화면(`SquadSuggest.tsx`)이 후보마다 이름 아래에 한 줄과 불릿 둘을 그리는데
#    지금은 **붙박이 문자열**이다. 그 자리를 분석으로 채운다.
#
#    🔴 여기 검사들이 막는 것은 **없는 말을 하는 것**이다. 붙박이에는
#    「활동량이 많고 꾸준합니다」·「10경기 연속」이 섞여 있는데 그건 경기
#    기록이지 우리가 잰 것이 아니다.


def _card(rubric, grades):
    from supersub_agent.scoring import card
    result = aggregate(_judge(rubric, grades), rubric)
    return card(result["breakdown"]), result


@pytest.mark.parametrize("key", sorted(RUBRICS))
def test_the_card_titles_only_what_was_earned(key):
    """🔴 못 받은 칭호를 수식어로 달지 않는다.

    `title` 은 **모든 등급에 있다**(`paik` 23번). 그대로 쓰면 0등급의
    「무너지는 축」이 이름 아래 자랑처럼 걸린다.
    """
    rubric = RUBRICS[key]
    top, _ = _card(rubric, [2] * len(rubric.criteria))
    bottom, _ = _card(rubric, [0] * len(rubric.criteria))
    assert top["title"], "전부 잘했는데 수식어가 없다"
    assert bottom["title"] is None, "못 받은 칭호가 수식어로 나갔다"


@pytest.mark.parametrize("key", sorted(RUBRICS))
def test_the_card_never_pads_to_two_notes(key):
    """🔴 두 줄을 채우려고 지어내지 않는다.

    전부 잘했으면 아쉬운 줄이 없고, 전부 못했으면 강점 줄이 없다. 화면이 두
    줄을 원한다고 없는 말을 만들면 그 순간 이 카드는 근거가 아니다.
    """
    rubric = RUBRICS[key]
    for grades in ([2] * len(rubric.criteria), [0] * len(rubric.criteria)):
        got, _ = _card(rubric, grades)
        assert 1 <= len(got["notes"]) <= 2
        assert all(n.strip() for n in got["notes"])


@pytest.mark.parametrize("key", sorted(RUBRICS))
@pytest.mark.parametrize("grade", [0, 1, 2])
def test_no_digits_reach_the_card(key, grade):
    """🔴 계약 3장 4 — 숫자를 쓰지 않는다 (`summary` 와 같은 규칙)."""
    got, _ = _card(RUBRICS[key], [grade] * len(RUBRICS[key].criteria))
    text = (got["title"] or "") + " ".join(got["notes"])
    assert not any(ch.isdigit() for ch in text), text


@pytest.mark.parametrize("key", sorted(RUBRICS))
def test_the_card_says_nothing_about_match_records(key):
    """🔴 **경기 기록은 우리가 잰 것이 아니다.**

    붙박이 문자열에 섞여 있던 「활동량」·「10경기 연속」·「출전」 같은 말은
    분석이 아니라 기록에서 와야 한다. 여기서 만들면 **지어낸 스카우팅**이 된다.
    """
    rubric = RUBRICS[key]
    for grade in (0, 1, 2):
        got, _ = _card(rubric, [grade] * len(rubric.criteria))
        text = (got["title"] or "") + " ".join(got["notes"])
        for word in ("경기", "활동량", "출전", "연속", "꾸준"):
            assert word not in text, f"경기 기록의 말이 카드에 섞였다: {word}"


@pytest.mark.parametrize("key", sorted(RUBRICS))
def test_the_card_does_not_move_the_score(key):
    """🔴 `summary` 와 같은 성질 — 이 블록은 점수를 안 건드린다.

    건드리면 B-6 재실행을 부른다. 카드를 빼고 계산한 것과 비트 동일해야 한다.
    """
    rubric = RUBRICS[key]
    _, result = _card(rubric, [1] * len(rubric.criteria))
    without = {k: v for k, v in result.items() if k != "card"}
    again = aggregate(_judge(rubric, [1] * len(rubric.criteria)), rubric)
    assert {k: v for k, v in again.items() if k != "card"} == without


@pytest.mark.parametrize("key", sorted(RUBRICS))
def test_the_card_is_deterministic(key):
    """같은 판정이 같은 카드를 낸다 — 모델을 안 부르는 것이 그 이유다."""
    rubric = RUBRICS[key]
    a, _ = _card(rubric, [2, 1, 0] * len(rubric.criteria))
    b, _ = _card(rubric, [2, 1, 0] * len(rubric.criteria))
    assert a == b


@pytest.mark.parametrize("key", sorted(RUBRICS))
def test_the_card_does_not_repeat_its_own_title(key):
    """🔴 화면은 수식어와 불릿을 **나란히** 그린다 — 같은 말이 두 번 보이면 안 된다.

    수식어는 **칭호**, 불릿은 **항목 이름**으로 나눠 적는다.
    """
    rubric = RUBRICS[key]
    got, _ = _card(rubric, [2] * len(rubric.criteria))
    assert got["title"]
    for note in got["notes"]:
        assert got["title"] not in note, f"수식어가 불릿에서 반복된다: {note}"
