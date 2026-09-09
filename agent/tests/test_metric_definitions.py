"""지표 코드 정본이 루브릭과 어긋나지 않는지 (미결 `jin` 23번).

🔴 **여기 있는 검사는 지우면 안 된다.** 막고 있는 것은 이것이다:

새 종목·동작 루브릭이 새 지표 코드를 들고 들어왔는데 `metric_definition` 시드에
그 코드가 없으면, **그 종목의 적재가 전부 `UNKNOWN_METRIC_CODE` 로 거부된다.**
그런데 에이전트 쪽 테스트는 전부 통과하고 스텁도 통과한다 — 실서버에 배포한
뒤에야 드러난다. 루브릭을 고치는 순간 여기서 빨개지는 것이 유일하게 값싼 자리다.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "export_metric_definitions", ROOT / "scripts" / "export_metric_definitions.py"
)
export = importlib.util.module_from_spec(_spec)
sys.modules["export_metric_definitions"] = export
_spec.loader.exec_module(export)


# `features` 에 실려 나가지만 어느 루브릭도 채점에 쓰지 않는 코드.
# 시드에서 빠지면 적재가 통째로 거부되므로 여기 고정해 둔다.
UNSCORED_BUT_EMITTED = {"impact_frame"}

# 단위는 이 넷만 쓴다. 새 단위를 늘리려면 받는 쪽(`metric_definition`)과
# 함께 정해야 한다 — 조용히 늘리면 화면이 못 읽는 값이 쌓인다.
ALLOWED_UNITS = {"deg", "ratio", "s", "score"}


def test_every_rubric_metric_is_declared():
    """🔴 draft 까지 본다 — 닫아 둔 루브릭을 여는 날 터지지 않게."""
    missing = export.check_coverage(include_draft=True)
    assert not missing, (
        f"정본(contracts/metric_definitions.yaml)에 없는 코드를 루브릭이 쓴다: "
        f"{missing}. 여기를 통과 못 하면 그 종목 적재가 실서버에서 전부 거부된다."
    )


def test_unscored_emitted_metrics_are_declared():
    """루브릭이 안 쓰는데 `features` 가 내보내는 코드도 시드에 있어야 한다."""
    declared = {m["code"] for m in export.load_definitions()["metrics"]}
    assert UNSCORED_BUT_EMITTED <= declared, (
        f"{UNSCORED_BUT_EMITTED - declared} 가 정본에 없다. "
        "채점에 안 쓰여도 features 에 실려 나가면 적재는 거부된다."
    )


def test_units_are_from_the_agreed_set():
    for row in export.build_rows(include_draft=True):
        assert row["unit"] in ALLOWED_UNITS, (
            f"{row['code']}: 합의 밖 단위 {row['unit']!r}"
        )


def test_frame_metrics_are_declared_in_seconds():
    """🔴 프레임 수를 프레임으로 보내지 않는다.

    DB 행에는 `sampled_fps` 가 없어서 프레임 수만 저장하면 나중에 읽는 쪽이
    30fps 를 가정하고 곱한다. 그 가정이 틀린 클립이 평가셋에 있다.
    """
    from supersub_agent.features import FRAME_DURATION_METRICS, FRAME_INDEX_METRICS

    by_code = {m["code"]: m for m in export.load_definitions()["metrics"]}
    for code in FRAME_DURATION_METRICS | FRAME_INDEX_METRICS:
        assert code in by_code, f"{code} 가 정본에 없다"
        assert by_code[code]["unit"] == "s", (
            f"{code}: 프레임 단위 지표는 초(`s`)로 선언해야 한다 — "
            f"지금 {by_code[code]['unit']!r}"
        )


def test_grade_codes_do_not_collide_across_sports():
    """🔴 항목 id 만으로는 안 된다.

    `follow_through` 는 농구 「던진 뒤 손목 마무리」이고 축구 「차고 난 뒤
    마무리」다. 코드당 한 행인 A안에서 id 만 쓰면 둘 중 하나의 이름이 지워진다.
    """
    rows = [r for r in export.build_rows(include_draft=True)
            if r["kind"].startswith("grade")]
    assert rows, "등급 행이 하나도 안 나왔다"
    by_code = {}
    for r in rows:
        assert r["code"] not in by_code, f"등급 코드가 겹친다: {r['code']}"
        by_code[r["code"]] = r["label"]
    assert len(set(by_code.values())) == len(by_code), (
        "서로 다른 코드가 같은 라벨을 쓴다 — 화면에서 못 가른다"
    )


def test_rows_are_unique_and_complete():
    rows = export.build_rows(include_draft=False)
    codes = [r["code"] for r in rows]
    assert len(codes) == len(set(codes))
    for r in rows:
        assert r["label"].strip(), f"{r['code']}: label 이 비었다"
        assert r["code"].strip()


def test_the_exporter_refuses_when_a_code_is_undeclared(monkeypatch):
    """정본에서 코드를 빼면 **내보내기가 실패해야 한다** — 조용히 빠지지 않게."""
    real = export.load_definitions

    def crippled():
        d = dict(real())
        d["metrics"] = [m for m in d["metrics"]
                        if m["code"] != "trunk_forward_lean_deg_at_impact"]
        return d

    monkeypatch.setattr(export, "load_definitions", crippled)
    assert "trunk_forward_lean_deg_at_impact" in export.check_coverage(True)
