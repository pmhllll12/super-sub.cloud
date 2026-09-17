"""루브릭 근거·검증 상태 4축 정본이 루브릭과 어긋나지 않는지 (미결 `ho` 36번).

🔴 **여기 있는 검사는 지우면 안 된다.** 막고 있는 것은 둘이다.

**(1) 새 세부기준이 근거 판정 없이 들어오는 것.** 항목을 하나 더하면 그것은
자동으로 「검증 안 됨」이 아니라 **아무 데도 안 적힌 상태**가 된다. 그러면
「6종이 다 검증됐다」는 말을 막을 근거가 그 항목에만 없어진다. 외부 검토가
두 번 연달아 경고한 것이 정확히 그 오독이다.

**(2) 미검증 인용이 정본에 박히는 것.** 검토가 PubMed 링크를 여럿 달아
왔는데 **원문을 열어 확인하지 않았다.** 미검증 인용은 「출처 없음」보다
나쁘다 — 없는 근거를 있다고 말하는 것이 된다. 그래서 `citation` 은
`citation_verified: true` 와 **함께여야만** 통과한다. 확인한 사람이 둘을
같이 넣는다.

🔴 정본은 `contracts/rubric_evidence.yaml` 이다. `rubrics/` 에 두면
`discover_rubrics` 가 루브릭으로 읽어 **배포에서 죽는다.**
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "contracts" / "rubric_evidence.yaml"
RUBRIC_DIR = ROOT / "rubrics"

CRITERION_AXES = ("biomechanical_basis", "threshold_validity")


@pytest.fixture(scope="module")
def evidence():
    return yaml.safe_load(EVIDENCE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rubrics():
    """(키, 파싱된 루브릭) — draft 도 본다. 닫아 둔 것을 여는 날 터지지 않게."""
    out = {}
    for path in sorted(RUBRIC_DIR.glob("*.yaml")):
        d = yaml.safe_load(path.read_text(encoding="utf-8"))
        out[f"{d['sport']}/{d['motion']}"] = d
    return out


def test_the_vocabulary_has_no_verified_level(evidence):
    """🔴 「검증됨」이라는 등급을 만들지 않는다.

    이 프로젝트에 그렇게 말할 수 있는 축이 아직 하나도 없다. 어휘에 없으면
    잘못 적을 수도 없다 — 누군가 `verified` 를 더하려 하면 여기서 걸린다.
    """
    assert "verified" not in evidence["levels"], (
        "🔴 `verified` 등급을 만들려 하고 있다. 그렇게 말하려면 정답 라벨이 "
        "있어야 하고, 지금은 없다 (미결 ho 2번). 등급을 늘리기 전에 "
        "무엇을 근거로 그렇게 부르는지부터 사전 등록할 것."
    )


def test_every_rubric_has_an_event_verdict(evidence, rubrics):
    """이벤트 타당성은 **루브릭**의 성질이라 루브릭마다 하나씩 있어야 한다."""
    missing = sorted(set(rubrics) - set(evidence["rubrics"]))
    assert not missing, (
        f"🔴 근거 정본에 없는 루브릭: {missing}. "
        f"{EVIDENCE.relative_to(ROOT)} 의 `rubrics:` 에 "
        "`event_validity` 를 적을 것."
    )
    orphan = sorted(set(evidence["rubrics"]) - set(rubrics))
    assert not orphan, f"🔴 루브릭이 없는데 근거만 남아 있다: {orphan}"

    for key, entry in evidence["rubrics"].items():
        assert entry["impact_event"] == rubrics[key]["kinematics"]["impact_event"], (
            f"🔴 {key}: 근거 정본이 적은 `impact_event` 가 루브릭과 다르다 — "
            f"{entry['impact_event']!r} 대 "
            f"{rubrics[key]['kinematics']['impact_event']!r}. "
            "이벤트를 바꿨으면 그 타당성 판정도 다시 해야 한다."
        )
        assert entry["status"] == rubrics[key]["status"], (
            f"🔴 {key}: `status` 가 루브릭과 다르다 — draft 를 active 로 "
            "올렸으면 근거 판정을 다시 볼 자리다."
        )


def test_every_criterion_has_both_criterion_axes(evidence, rubrics):
    """새 세부기준이 근거 판정 없이 들어오는 것을 막는다."""
    problems = []
    for key, rubric in rubrics.items():
        declared = evidence["criteria"].get(key, {})
        actual = {c["id"] for c in rubric.get("criteria", [])}
        for missing in sorted(actual - set(declared)):
            problems.append(f"{key}.{missing} — 근거 정본에 없다")
        for orphan in sorted(set(declared) - actual):
            problems.append(f"{key}.{orphan} — 루브릭에 없는데 근거만 있다")
        for cid in sorted(actual & set(declared)):
            for axis in CRITERION_AXES:
                if axis not in declared[cid]:
                    problems.append(f"{key}.{cid} — `{axis}` 가 없다")
    assert not problems, (
        "🔴 4축 정본과 루브릭이 어긋난다:\n  " + "\n  ".join(problems)
        + f"\n\n{EVIDENCE.relative_to(ROOT)} 를 고칠 것. 🔴 항목을 더하면 "
        "그것은 「검증 안 됨」이 아니라 **아무 데도 안 적힌 상태**가 된다."
    )


def test_every_scored_metric_has_a_measurement_verdict(evidence, rubrics):
    """측정 타당성은 **지표**의 성질이다 — 쓰이는 지표는 전부 판정이 있어야 한다.

    같은 지표가 세 루브릭에 쓰이면 판정은 **한 곳**에 있다. 루브릭마다
    복사해 두면 한쪽만 고쳐진다(미결 10번의 형태).
    """
    used = {m for r in rubrics.values() for c in r.get("criteria", [])
            for m in c["measured_by"]}
    missing = sorted(used - set(evidence["metrics"]))
    assert not missing, (
        f"🔴 측정 타당성 판정이 없는 지표: {missing}. "
        f"{EVIDENCE.relative_to(ROOT)} 의 `metrics:` 에 적을 것."
    )
    orphan = sorted(set(evidence["metrics"]) - used)
    assert not orphan, (
        f"🔴 어느 루브릭도 안 쓰는데 판정만 남아 있다: {orphan}. "
        "항목을 지웠으면 판정도 함께 정리할 것."
    )


def test_every_level_comes_from_the_closed_vocabulary(evidence):
    """어휘 밖의 등급을 쓰면 표가 못 읽히는 값으로 채워진다."""
    allowed = set(evidence["levels"])
    bad = []

    def check(where, node):
        if isinstance(node, dict) and "level" in node:
            if node["level"] not in allowed:
                bad.append(f"{where}: {node['level']!r}")

    for row in evidence["global"]:
        check(f"global.{row['id']}", row)
    for name, entry in evidence["metrics"].items():
        check(f"metrics.{name}", entry["measurement_validity"])
    for key, entry in evidence["rubrics"].items():
        check(f"rubrics.{key}", entry["event_validity"])
    for key, crits in evidence["criteria"].items():
        for cid, axes in crits.items():
            for axis in CRITERION_AXES:
                check(f"criteria.{key}.{cid}.{axis}", axes[axis])

    assert not bad, (
        "🔴 닫힌 어휘 밖의 등급이다:\n  " + "\n  ".join(bad)
        + f"\n\n쓸 수 있는 것: {sorted(allowed)}"
    )


def test_no_unverified_citation_reaches_the_document(evidence):
    """🔴 미검증 인용이 정본에 박히는 것을 막는다.

    외부 검토가 PubMed 링크를 여럿 달아 왔지만 **원문을 열어 확인하지
    않았다.** 확인 안 한 인용을 근거로 적으면 「출처 없음」보다 나쁘다 —
    없는 근거를 있다고 말하는 것이 되고, 미결 34번이 정한 「검증을 포기하고
    **출처**로 낮춘다」의 값어치가 거기서 무너진다.

    확인한 사람이 `citation` 과 `citation_verified: true` 를 **함께** 넣는다.
    """
    naked = []
    urlish = []

    def check(where, node):
        if not isinstance(node, dict):
            return
        if node.get("citation") and not node.get("citation_verified"):
            naked.append(where)
        note = str(node.get("note", ""))
        if "http://" in note or "https://" in note:
            urlish.append(where)

    for name, entry in evidence["metrics"].items():
        check(f"metrics.{name}", entry["measurement_validity"])
    for key, entry in evidence["rubrics"].items():
        check(f"rubrics.{key}", entry["event_validity"])
    for key, crits in evidence["criteria"].items():
        for cid, axes in crits.items():
            for axis in CRITERION_AXES:
                check(f"criteria.{key}.{cid}.{axis}", axes[axis])

    assert not naked, (
        "🔴 `citation_verified: true` 없이 인용이 붙어 있다:\n  "
        + "\n  ".join(naked)
        + "\n\n원문을 (가) 실재하는지 (나) 우리가 붙이려는 문장을 실제로 "
        "뒷받침하는지 확인한 뒤에만 넣을 것 (미결 ho 36번)."
    )
    assert not urlish, (
        "🔴 `note` 안에 링크를 숨겨 놓았다:\n  " + "\n  ".join(urlish)
        + "\n\n인용은 `citation` 필드로, `citation_verified` 와 함께."
    )


def test_thresholds_are_not_claimed_as_settled(evidence):
    """🔴 임계값 타당성이 조용히 올라가는 것을 막는다.

    임계값은 전부 **지도자 검수 전 임시값**이고, 거기에 「상한 초과가
    0등급으로 나간다」(미결 20번)가 겹쳐 있다. 어느 한 항목만 등급을
    올리고 싶어지면 **그때가 사전 등록을 받을 때**지 이 파일을 고칠 때가
    아니다. 「분포에 맞춰 긋는 길」은 미결 34번에서 이미 기각됐다.
    """
    settled = []
    for key, crits in evidence["criteria"].items():
        for cid, axes in crits.items():
            level = axes["threshold_validity"]["level"]
            if level not in ("unverified", "blocked"):
                settled.append(f"{key}.{cid}: {level}")
    assert not settled, (
        "🔴 임계값 타당성을 올려 적었다:\n  " + "\n  ".join(settled)
        + "\n\n올리려면 지도자 검수(미결 ho 2번)나 사전 등록된 측정이 "
        "먼저다. 외부 검토는 AI 단독 판독이라 근거가 되지 않는다."
    )
