"""`report.json` 봉투가 계약(`contracts/report_schema.yaml`)과 같은가.

🔴 **여기 있는 검사는 지우면 안 된다.** 막고 있는 것은 이것이다:

적재(`POST /analyses`)·리포트 읽기 경로·화면 셋이 **같은 JSON 을 읽는다**
(미결 `jin` 27번). 그런데 봉투는 분석 스크립트 안에서 만들어지므로, 키를
하나 지우거나 이름을 바꿔도 **에이전트 테스트는 전부 통과한다.** 백엔드는
자기 코드를 한 줄도 안 고쳤는데 실서버 적재에서 `KeyError` 로 알게 된다 —
그때는 이미 배포된 뒤다.

그래서 필드 목록을 파일로 고정하고, 여기서 **코드가 실제로 내는 봉투**와
맞춰 본다. 어긋나면 어느 쪽이 맞는지 사람이 정하고 **둘을 함께** 고친다.
버전을 올리는 절차는 그 yaml 머리말에 있다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import analyze_s3  # noqa: E402
from supersub_agent.features import (  # noqa: E402
    extract_features,
    gate_ratio,
    keypoint_quality_envelope,
)
from supersub_agent.pose import PoseResult  # noqa: E402
from supersub_agent.scoring import aggregate, load_rubric  # noqa: E402
from test_features import build_sequence  # noqa: E402

CONTRACT = yaml.safe_load(
    (ROOT / "contracts" / "report_schema.yaml").read_text(encoding="utf-8")
)
RUBRIC_PATH = ROOT / "rubrics" / "football_instep_shot.yaml"


def _declared(block: dict) -> set[str]:
    return set(block["fields"])


@pytest.fixture(scope="module")
def report() -> dict:
    """합성 키포인트로 **실제 `build_report`** 를 지나온 봉투.

    스텁으로 손수 만든 dict 를 검사하면 계약과 스텁이 맞는지만 보게 된다 —
    확인해야 하는 것은 **production 함수의 산출**이다. S3·영상·판정 모델은
    봉투 모양과 무관하므로 그 셋만 대신 넣는다.
    """
    kps = build_sequence()
    pose = PoseResult(
        keypoints=kps,
        source_fps=30.0,
        sampled_fps=15.0,
        frame_size=(1920, 1080),
        subject_boxes=[None] * len(kps),
    )
    rubric = load_rubric(RUBRIC_PATH)
    features = extract_features(
        kps, {}, rubric.impact_limb, rubric.impact_event, "auto"
    )
    applicable = rubric.applicable_criteria(features)
    assert len(applicable) >= 2, "항목이 둘 이상이어야 skipped 를 만들 수 있다"
    # 🔴 한 항목을 일부러 빼서 `skipped[]` 가 실제로 채워지게 한다 — 비어 있으면
    #    그 필드 목록은 검사되지 않고, 그게 비어 있어서 못 잡힌 자리다.
    judged = applicable[:-1]
    judgments = {
        c.id: {
            "grade": 1,
            "evidence": "디딤발이 공 옆에 안정적으로 놓였습니다.",
            "metric_ref": next(iter(c.measured_by), ""),
        }
        for c in judged
    }
    result = aggregate(judgments, rubric, features=features)
    return analyze_s3.build_report(
        video="s3://버킷/videos/u1/clip.mp4",
        video_id="1b3c",
        stamp="20260910T000000Z",
        rubric=rubric,
        rubric_path=str(RUBRIC_PATH),
        swing_side="auto",
        focus=None,
        target_fps=30,
        pose=pose,
        features=features,
        result=result,
        previews={"impact": "s3://버킷/reports/u1/1b3c/impact.jpg"},
        judge_backend="stub",
        judge_model="stub-model",
        timing={"fetch_s": 1.0, "measure_s": 2.0, "judge_s": 3.0, "preview_s": 4.0},
    )


# --- 봉투 ------------------------------------------------------------------


def test_the_schema_version_in_the_report_is_the_contract_version(report):
    """봉투가 말하는 버전과 계약 파일의 버전이 같아야 한다.

    다르면 백엔드가 **모르는 major** 판정을 잘못 내린다 — 계약은 1.0 인데
    봉투가 2.0 이라고 말하면 정상 리포트가 통째로 거부된다.
    """
    assert analyze_s3.REPORT_SCHEMA_VERSION == CONTRACT["version"]
    assert report["schema_version"] == CONTRACT["version"]


def test_the_envelope_keys_are_exactly_the_contract(report):
    declared = set(CONTRACT["envelope"])
    assert set(report) == declared, (
        "리포트 봉투와 contracts/report_schema.yaml 이 어긋났다. "
        f"코드에만 있는 키 {set(report) - declared} · "
        f"계약에만 있는 키 {declared - set(report)}. "
        "적재·읽기 경로·화면이 이 목록을 읽는다 — 둘을 함께 고칠 것."
    )


@pytest.mark.parametrize("key", ["rubric", "focus", "timing", "subject"])
def test_the_declared_blocks_have_exactly_their_fields(report, key):
    declared = _declared(CONTRACT["envelope"][key])
    assert set(report[key]) == declared, f"{key} 블록이 계약과 다르다"


def test_the_result_block_has_exactly_its_fields(report):
    assert set(report["result"]) == set(CONTRACT["result"]["fields"])


def test_open_blocks_are_declared_open(report):
    """키가 지표 코드인 블록은 목록을 고정하지 않는다 — 그 사실을 계약이 적는다."""
    for key in ("features", "frame_metrics_seconds", "previews"):
        assert CONTRACT["envelope"][key].get("open") is True, (
            f"{key} 는 키가 열려 있는 블록이다 — 계약에 open: true 로 남길 것"
        )


# --- 항목별 판정 (제안 (b) 테이블이 받을 자리) --------------------------------


def test_the_breakdown_fields_are_exactly_the_contract(report):
    declared = set(CONTRACT["breakdown_item"]["fields"])
    assert report["result"]["breakdown"], "판정된 항목이 없으면 검사가 무의미하다"
    for item in report["result"]["breakdown"]:
        assert set(item) == declared, (
            f"{item.get('criterion_id')}: breakdown 항목이 계약과 다르다. "
            f"코드에만 {set(item) - declared} · 계약에만 {declared - set(item)}"
        )


def test_the_skipped_fields_are_exactly_the_contract(report):
    declared = set(CONTRACT["skipped_item"]["fields"])
    assert report["result"]["skipped"], "제외된 항목이 없으면 검사가 무의미하다"
    for item in report["result"]["skipped"]:
        assert set(item) == declared


def test_the_http_only_fields_are_not_in_the_s3_report(report):
    """🔴 `margin`·`confident` 는 HTTP 데모 경로에만 있다.

    적재가 그 둘을 필수로 읽으면 실서버에서 `KeyError` 다. 어느 쪽에 있는지를
    계약이 적어 두고, 여기서 **S3 봉투에는 없다**는 것을 고정한다.
    """
    http_only = set(CONTRACT["http_only_breakdown_fields"])
    for item in report["result"]["breakdown"]:
        assert not (http_only & set(item)), (
            f"{item['criterion_id']}: HTTP 전용 필드가 S3 리포트에 섞였다. "
            "싣기로 정했다면 계약의 breakdown_item 으로 옮길 것"
        )


# --- 키포인트 품질 (미결 `jin` 27번 곁가지) ----------------------------------


def test_the_quality_block_carries_the_ratio_the_gate_measured(report):
    """게이트가 쓴 비율이 그대로 실려야 한다 — 두 번 계산하지 않는다."""
    kps = build_sequence()
    block = report["keypoint_quality"]
    assert block["known"] is True
    assert set(block) == _declared(CONTRACT["envelope"]["keypoint_quality"])
    assert block["swing_side_valid_ratio"] == pytest.approx(
        round(gate_ratio(kps, "leg", "auto"), 4)
    )
    # 리포트가 존재한다는 것 자체가 게이트를 통과했다는 뜻이다.
    assert block["swing_side_valid_ratio"] >= block["threshold"]


def test_the_quality_block_does_not_invent_a_ratio_it_could_not_measure():
    """🔴 정규화가 안 되는 입력에 0.0 을 적으면 「쟀는데 나빴다」로 읽힌다."""
    block = keypoint_quality_envelope(np.zeros((5, 17, 3)), "leg", "auto")
    assert block["known"] is False
    assert "swing_side_valid_ratio" not in block
    assert set(block) == set(CONTRACT["envelope"]["keypoint_quality"]["degraded_fields"])


def test_the_quality_block_is_not_part_of_features():
    """🔴 `features` 에 키를 더하면 판정 입력이 달라져 B-6 재실행을 부른다."""
    kps = build_sequence()
    before = dict(extract_features(kps, {}, "leg", "extension_peak", "auto"))
    keypoint_quality_envelope(kps, "leg", "auto")
    after = extract_features(kps, {}, "leg", "extension_peak", "auto")
    assert set(after) == set(before)
    assert "keypoint_quality" not in after
