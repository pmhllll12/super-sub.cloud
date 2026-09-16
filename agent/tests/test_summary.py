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


def _card(rubric, grades, features=None):
    from supersub_agent.scoring import card
    result = aggregate(_judge(rubric, grades), rubric)
    return card(result["breakdown"], rubric, features), result


def _inside(interval):
    """그 구간 안의 값 하나. 방향이 갈리는 항목에 측정값을 만들어 주는 자리다."""
    lo, hi = interval
    if lo is None:
        return hi - 1.0
    if hi is None:
        return lo + 1.0
    return (lo + hi) / 2.0


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


# -- 불릿 문장의 출처: 루브릭의 `card_lines` (2026.09.16) --------------------
#
#    코드가 짓던 틀(「…가 이번 동작의 강점입니다」)은 항목 이름만 갈아 끼우는
#    문장이었다. 선수에게 보이는 문구는 **지도자가 검수**해야 하므로 칭호와
#    같은 자리(루브릭)로 옮겼다. 아래 검사들이 그 배선과, 고정 문장이라서
#    생기는 함정을 막는다.


@pytest.mark.parametrize("key", sorted(RUBRICS))
@pytest.mark.parametrize("grade", [0, 1, 2])
def test_every_criterion_documents_a_card_line_for_every_grade(key, grade):
    """🔴 새 항목이 문장 없이 배포되는 것을 막는다.

    빠져도 **터지지 않는다** — 코드가 지은 틀로 조용히 떨어질 뿐이라, 검수받지
    않은 문장이 섞인 채 나가도 아무도 모른다. 등급 셋을 다 요구하는 이유는
    0등급 줄이 가장 빠뜨리기 쉬워서다.

    구간마다 쓴 등급(반대 방향이 한 등급에 있는 자리)은 **구간 수만큼** 있어야
    한다 — 하나라도 비면 그 방향의 선수만 조용히 틀로 떨어진다.
    """
    for c in RUBRICS[key].criteria:
        written = c.card_lines.get(grade, ())
        assert written, f"{key}/{c.id}: {grade}등급 문장 없음"
        assert len(written) in (1, len(c.bands.get(grade, ()))), (
            f"{key}/{c.id}: {grade}등급 문장 {len(written)}개가 구간 수와 안 맞는다"
        )
        assert all(s.strip() for s in written), f"{key}/{c.id}: {grade}등급 빈 문장"


@pytest.mark.parametrize("key", sorted(RUBRICS))
def test_card_lines_say_only_what_a_fixed_sentence_may_say(key):
    """🔴 **등급마다 고정된 문장**이라 적어서는 안 되는 것이 있다.

    수치는 측정값과 함께 움직이지 않는다 — 「약 16cm」를 구간 문장에 적으면 그
    구간의 **모든 영상**이 재지도 않은 수치를 달고 나간다. 경기 기록은 애초에
    우리가 잰 것이 아니다. 렌더된 카드만 보는 검사로는 모자라다 — 그쪽은
    최고·최저 항목만 지나가므로 나머지 문장은 검사되지 않는다.
    """
    for c in RUBRICS[key].criteria:
        for grade, written in c.card_lines.items():
            # 🔴 문자열을 그대로 순회하지 않는다 — 문장이 구간마다 여럿이라
            #    튜플이고, 튜플을 문자로 아는 검사는 **조용히 다 통과한다.**
            assert isinstance(written, tuple), f"{c.id}/{grade}: 튜플이 아니다"
            for line in written:
                assert not any(ch.isdigit() for ch in line), f"{c.id}/{grade}: {line}"
                for word in ("경기", "활동량", "출전", "연속", "꾸준"):
                    assert word not in line, f"{c.id}/{grade}: 경기 기록의 말 — {word}"


@pytest.mark.parametrize("key", sorted(RUBRICS))
@pytest.mark.parametrize("grade", [0, 2])
def test_the_bullet_is_the_sentence_the_rubric_wrote(key, grade):
    """🔴 루브릭 문장이 실제로 카드에 실리는지 — 배선이 끊기면 조용히 폴백한다.

    적재기가 `card_lines` 를 안 읽거나 `card()` 가 루브릭을 못 받으면 예외 없이
    코드 틀로 돌아간다. 그 상태로도 다른 검사들은 전부 초록이다.

    방향이 갈리는 항목은 **측정값이 있어야** 루브릭 문장이 나온다. 그래서 각
    항목의 값을 그 등급의 첫 구간 안에 놓고 부른다 — 값을 안 주면 그 항목만
    조용히 틀로 떨어져 이 검사가 무는 범위가 줄어든다.
    """
    rubric = RUBRICS[key]
    features = {c.band_metric: _inside(c.bands[grade][0]) for c in rubric.criteria}
    got, _ = _card(rubric, [grade] * len(rubric.criteria), features)
    written = {s.strip() for c in rubric.criteria for s in c.card_lines.get(grade, ())}
    assert got["notes"], "불릿이 비었다"
    for note in got["notes"]:
        assert note in written, f"루브릭이 안 쓴 문장이 카드에 있다: {note}"


def test_a_two_directioned_grade_tells_which_direction_it_was():
    """🔴 한 등급 안에 **반대 방향**이 있으면 문장도 갈린다 (2026.09.16).

    인사이드 패스의 골반 회전 1등급은 「덜 돌았다(8~15도)」와 「너무 많이
    돌았다(35도 초과)」가 같은 등급이다. 한 문장으로 부르면 **고칠 방향이 안
    보인다** — 지도자 검수 서식을 만들다 드러났다.
    """
    from supersub_agent.scoring import card
    rubric = RUBRICS["football/inside_pass"]
    hip = rubric.get("hip_rotation")
    assert hip.card_line_for(1, 10.0) != hip.card_line_for(1, 40.0)
    assert "덜" in hip.card_line_for(1, 10.0)

    # 카드까지 실제로 갈리는지 — 골반만 1등급이고 나머지는 0등급으로 둔다.
    grades = [1 if c.id == "hip_rotation" else 0 for c in rubric.criteria]
    result = aggregate(_judge(rubric, grades), rubric)
    for value, expected in ((10.0, hip.card_line_for(1, 10.0)),
                            (40.0, hip.card_line_for(1, 40.0))):
        got = card(result["breakdown"], rubric, {"hip_rotation_range_deg": value})
        assert got["notes"] == [expected], (value, got)


def test_without_a_measurement_the_card_does_not_guess_a_direction():
    """🔴 **방향을 찍지 않는다.** 덜 돈 선수에게 「너무 많이 돌린다」고 말하는 것은
    아무 말도 안 하는 것보다 나쁘다.

    측정값이 없으면(평가·재현 경로가 `features` 없이 부른다) 루브릭 문장 대신
    방향을 말하지 않는 틀로 떨어진다.
    """
    from supersub_agent.scoring import card
    rubric = RUBRICS["football/inside_pass"]
    hip = rubric.get("hip_rotation")
    assert hip.card_line_for(1) == ""

    grades = [1 if c.id == "hip_rotation" else 0 for c in rubric.criteria]
    result = aggregate(_judge(rubric, grades), rubric)
    got = card(result["breakdown"], rubric)          # features 없음
    assert got["notes"] and got["notes"][0] not in hip.card_lines[1]


# -- 아쉬운 항목은 추천 카드에 안 적는다 (2026.09.16 결정) -------------------
#
#    이 카드는 **남이 보는 화면**이고 묻는 것은 「이 선수를 부를까」다. 사람 이름
#    옆의 약점 한 줄은 그 판단에 보태기보다 **사람을 규정하는 쪽**으로 읽힌다.
#    본인 리포트에는 그대로 있다 — 거기서는 코칭이지 낙인이 아니다.


@pytest.mark.parametrize("key", sorted(RUBRICS))
def test_the_card_names_only_the_best_grade_it_found(key):
    """🔴 아쉬운 항목이 추천 카드에 섞이는 것을 막는다.

    예전에는 **가장 낮은 항목**을 일부러 한 줄 적었다(「…은 아직 아쉽습니다」).
    등급이 갈린 판정으로 재야 무는 검사다 — 전부 같은 등급이면 위아래가 같아서
    무엇을 골랐든 통과한다.
    """
    rubric = RUBRICS[key]
    n = len(rubric.criteria)
    grades = [2, 1, 0] + [1] * (n - 3)
    got, result = _card(rubric, grades)
    top = max(int(b["grade"]) for b in result["breakdown"])
    said = {c.card_line_for(top).strip() for c in rubric.criteria}
    for note in got["notes"]:
        assert note in said, f"가장 잘한 등급이 아닌 항목이 카드에 있다: {note}"


@pytest.mark.parametrize("key", sorted(RUBRICS))
def test_a_card_without_a_strength_still_speaks_but_calls_it_nothing(key):
    """🔴 2등급이 없어도 **비우지 않는다** — 그 선수에게서 가장 나은 항목을 적는다.

    실측으로는 드물다(축구 18편 중 1편). 그렇다고 빈 카드를 내보내면 화면은
    **분석이 없는 것**과 구분하지 못한다.

    🔴 다만 **1등급을 「강점」이라 부르지 않는다** — `summarize` 와 같은 규칙이고,
    그 선을 넘으면 카드가 못한 것을 잘한 것으로 옮겨 적기 시작한다.
    """
    rubric = RUBRICS[key]
    got, _ = _card(rubric, [1] * len(rubric.criteria))
    assert got["notes"], "가장 나은 항목조차 안 적었다"
    assert got["title"] is None, "2등급이 없는데 수식어가 걸렸다"
    assert "강점" not in " ".join(got["notes"])


@pytest.mark.parametrize("key", sorted(RUBRICS))
def test_the_card_still_speaks_without_a_rubric(key):
    """루브릭 없이 `breakdown` 만 들고 불려도 돌아야 한다 (평가·재현 경로).

    빈 카드를 내보내는 것보다 코드가 지은 단조로운 문장이 낫다.
    """
    from supersub_agent.scoring import card
    rubric = RUBRICS[key]
    result = aggregate(_all(rubric, 2), rubric)
    got = card(result["breakdown"])
    assert got["notes"] and all(n.strip() for n in got["notes"])


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
