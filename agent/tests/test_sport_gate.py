"""축구 아닌 영상을 거르는 게이트 (미결 `ho` 43번 ㉮).

🔴 **지우면 안 되는 검사가 둘 있다.**

⑴ **`sports_ball` 이 거절 근거로 들어오는 것.** COCO 에서 축구공·농구공·
   야구공이 **한 클래스**라 종목을 안 가른다. 실측(`eval/pending43_sport_gate/`)
   으로 야구 39편 중 **12편이 공을 갖고 있어**, 공을 근거로 쓰면 그 12편이
   그대로 통과하거나 — 반대로 「공이 없으면 거절」로 두면 정상 축구 업로드가
   막힌다.

⑵ **종목 불일치가 품질 게이트와 같은 사유로 보고되는 것.** 둘 다 실패지만
   사용자가 할 일이 **정반대**다. 품질은 「다시 찍으세요」, 종목은 「다른
   영상을 올리세요」다. 뭉뚱그리면 같은 파일을 다시 올린다 — 미결 41번이
   실서버에서 아홉 번 그랬다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from supersub_agent.pose import (  # noqa: E402
    COUNTER_EVIDENCE_TOOLS,
    TOOL_KO,
    TRACKED_LABELS,
    sport_conflict,
)

import worker  # noqa: E402


def _track(n: int = 5) -> np.ndarray:
    return np.zeros((n, 3))


def test_a_ball_alone_is_never_a_reason_to_reject():
    """🔴 ⑴ — 축구 클립 19편이 실측에서 **전부** `sports_ball` 하나뿐이었다."""
    assert sport_conflict({"sports_ball": _track()}, "football") is None


def test_the_ball_is_not_in_the_counter_evidence_list_at_all():
    """🔴 ⑴ 을 목록 수준에서도 막는다 — 「한 종목만 빼먹었다」가 안 되게."""
    for sport, tools in COUNTER_EVIDENCE_TOOLS.items():
        assert "sports_ball" not in tools, (
            f"{sport}: COCO 는 종목별 공을 구분하지 않는다 — 야구 39편 중 12편이 "
            f"공을 갖고 있었다 (eval/pending43_sport_gate/)"
        )


@pytest.mark.parametrize("tool", ["baseball_bat", "tennis_racket"])
def test_a_contradicting_tool_is_caught(tool):
    assert sport_conflict({tool: _track()}, "football") == tool
    # 공이 함께 있어도 어긋나는 도구가 이긴다 — 야구 클립 7편이 그 조합이었다.
    assert sport_conflict({tool: _track(), "sports_ball": _track()}, "football") == tool


def test_nothing_detected_is_not_a_rejection():
    """도구가 하나도 없으면 통과한다 — 실측에서 야구 8편이 그랬고, 그래도 통과다.

    🔴 **31%가 그냥 통과한다는 뜻이다.** 이 게이트는 벽이 아니라 걸름망이고,
    그것을 검사로도 못박아 둔다 — 「이제 다른 종목은 안 들어온다」고 읽으면 안 된다.
    """
    assert sport_conflict({}, "football") is None


def test_a_sport_we_have_no_rule_for_is_not_rejected():
    """규칙이 없는 종목은 **거절하지 않는다** — 없는 근거로 막지 않는다."""
    assert sport_conflict({"baseball_bat": _track()}, "basketball") is None


def test_every_counter_evidence_tool_is_actually_detectable():
    """🔴 검출기가 못 내는 이름을 적어 두면 **영원히 안 걸리는 규칙**이 된다."""
    detectable = set(TRACKED_LABELS.values())
    for sport, tools in COUNTER_EVIDENCE_TOOLS.items():
        for tool in tools:
            assert tool in detectable, (
                f"{sport}: `{tool}` 은 TRACKED_LABELS 에 없어 절대 검출되지 않는다"
            )


def test_every_counter_evidence_tool_has_a_human_name():
    """🔴 사용자에게 `baseball_bat` 을 보여주지 않는다 (㉱ 와 같은 취지)."""
    for tools in COUNTER_EVIDENCE_TOOLS.values():
        for tool in tools:
            assert TOOL_KO.get(tool), f"`{tool}` 의 한국어 이름이 없다"


def test_a_sport_mismatch_is_not_reported_as_a_quality_problem():
    """🔴 ⑵ — 사용자가 할 일이 정반대다. 사유가 갈려야 한다."""
    mismatch = worker.failure_reason(
        worker.Outcome(3, "종목 불일치: 야구 배트가 보입니다 — 축구 영상이 아닌 것 같습니다.")
    )
    quality = worker.failure_reason(
        worker.Outcome(2, "분석 중단: 하반신 스윙 측 키포인트 유효 프레임 비율 53% < 기준 70%.")
    )
    assert "종목" in mismatch
    assert "품질 게이트" not in mismatch, (
        "종목 불일치에 「품질 게이트 미달」이 붙으면 사용자가 같은 파일을 다시 "
        "올린다 (미결 41번)"
    )
    assert "재촬영" not in mismatch, "다시 찍어서 풀리는 문제가 아니다"
    assert "품질 게이트" in quality, "품질 쪽 사유는 그대로여야 한다"
    # 🔴 **이 줄이 이 검사의 이빨이다.** 위 셋만 두었더니 code 3 분기를 통째로
    #    지워도 통과했다 — 일반 분기가 내는 「종료 코드 3: 종목 불일치: …」가
    #    위 조건을 **전부 만족**하기 때문이다(`last_line` 에 이미 말이 들어 있다).
    #    계기가 재려던 것을 안 재고 있었다. 분기의 **존재**를 못박는다.
    assert not mismatch.startswith("종료 코드"), (
        "code 3 분기가 없어 일반 분기로 떨어졌다 — 사용자에게 종료 코드를 보인다"
    )


def test_the_mismatch_reason_is_not_double_labelled():
    """`analyze_s3` 가 이미 라벨을 붙이므로 워커가 또 붙이면 안 된다."""
    reason = worker.failure_reason(worker.Outcome(3, "종목 불일치: 야구 배트가 보입니다"))
    assert reason.count("종목 불일치") == 1, reason


def test_analyze_s3_exits_with_the_mismatch_code_not_the_quality_one():
    """🔴 종료 코드가 계약이다 — `analyze_s3` 와 `worker` 가 3으로 합의한다.

    워커 쪽만 검사하면 `analyze_s3` 가 종목 불일치를 **2로** 내보내도 안 걸린다.
    그러면 사용자는 다시 「품질 게이트 미달 — 재촬영이 필요하다」를 본다.
    `test_observability` 가 파일을 직접 읽는 것과 같은 방식으로 못박는다.
    """
    src = (ROOT / "scripts" / "analyze_s3.py").read_text(encoding="utf-8")
    assert "except SportMismatch" in src, "종목 불일치를 따로 잡지 않는다"
    handler = src.split("except SportMismatch", 1)[1].split("except ", 1)[0]
    assert "SystemExit(3)" in handler, (
        "종목 불일치가 3이 아닌 코드로 나간다 — 품질 게이트(2)와 섞이면 "
        "「재촬영이 필요하다」가 나가고 사용자가 같은 파일을 다시 올린다"
    )


def test_an_unknown_exit_code_still_says_something():
    """3을 더하면서 나머지 코드가 조용히 삼켜지지 않는지."""
    assert "5" in worker.failure_reason(worker.Outcome(5, "모델 적재 실패"))
