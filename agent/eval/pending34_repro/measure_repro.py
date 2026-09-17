#!/usr/bin/env python3
"""재현성 — **3장 정의**로 잰다: 동일 영상 5회 반복, 총점 표준편차 (미결 `ho` 34번).

    uv run python eval/pending34_repro/measure_repro.py            # 전체
    uv run python eval/pending34_repro/measure_repro.py --runs 2   # 빨리 확인
    uv run python eval/pending34_repro/measure_repro.py --child …  # 내부용

판정 기준은 [`PREREGISTRATION.md`](PREREGISTRATION.md) 에 **코드보다 먼저**
고정했다(`cd353f0`). 결과를 보고 고치지 않는다.

🔴 **`scripts/analyze.py --repeat` 와 다른 것을 잰다.** 그쪽은 `features` 를
한 번만 뽑고 **판정만** 반복한다 — 6장이 말한 「동일 측정값으로 3회」다.
여기는 **영상부터** 다시 돌린다. 3장 표의 「동일 영상 5회」가 이쪽이다.

🔴 **회차마다 새 프로세스로 돈다.** 같은 프로세스에서 반복하면 모델 가중치·
전역 상태가 회차 간에 남아 **실제보다 재현성이 좋게 나온다.**

🔴 **판정 모델을 안 돌린다.** 총점은 등급의 가중합이고 등급은
`Criterion.grade_for` 가 정한다 — 모델은 근거 문장만 쓴다. 전제가 맞는지는
기준 E 가 판정한다(사전 등록 2절).
"""
# ┌ 🔴 2026.09.11 — 이 회차는 그대로 재실행되지 않는다 ──────────────────────┐
# │ 축구 단일 종목 전환(미결 `ho` 39번)으로 아래가 읽는 야구·농구 루브릭이   │
# │ 저장소에 없다. 결과는 이 폴더의 RESULTS.md 에 그대로 있고, 그것이 정본   │
# │ 이다. 재실행하려면 루브릭을 먼저 꺼내 놓을 것:                           │
# │     git show bf21391:agent/rubrics/<이름>.yaml > rubrics/<이름>.yaml     │
# │ 🔴 **스크립트 로직은 고치지 않았다.** 사전 등록된 측정이라 사후에 고치면 │
# │ RESULTS.md 가 무엇을 잰 기록인지 알 수 없게 된다.                       │
# └─────────────────────────────────────────────────────────────────────────┘
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

SOCCER = ROOT / "data" / "goldenset" / "soccerkicks_video"

# 사전 등록 3절의 표본. 🔴 결과를 보고 바꾸지 않는다.
CLIPS = [
    (SOCCER / "10_penalty1.avi", "football_instep_shot.yaml"),
    (SOCCER / "11_freekick.avi", "football_instep_shot.yaml"),
    (SOCCER / "12_penalty.avi", "football_instep_shot.yaml"),
    (ROOT / "data" / "bball_shot.mp4", "basketball_jump_shot.yaml"),
]


def child(video: Path, rubric_name: str) -> None:
    """한 회차. 포즈부터 다시 뽑고 총점까지 낸 뒤 JSON 한 줄을 낸다."""
    from supersub_agent.features import extract_features
    from supersub_agent.pose import extract_keypoints
    from supersub_agent.scoring import aggregate, load_rubric

    rubric = load_rubric(ROOT / "rubrics" / rubric_name)
    try:
        pose = extract_keypoints(str(video))
        features = extract_features(
            pose.keypoints, impact_limb=rubric.impact_limb,
            impact_event=rubric.impact_event, objects=pose.objects,
        )
    except Exception as exc:  # noqa: BLE001 — 품질 게이트 포함. 기준 D 가 본다.
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"},
                         ensure_ascii=False))
        return

    applicable = rubric.applicable_criteria(features)
    judgments = {c.id: {"grade": c.grade_for(features), "evidence": ""}
                 for c in applicable}
    result = aggregate(judgments, rubric, features=features)
    print(json.dumps({
        "ok": True,
        "score": result["score"],
        "grade": result["grade"],
        "grades": {c.id: judgments[c.id]["grade"] for c in applicable},
        "features": features,
    }, ensure_ascii=False, sort_keys=True))


def run_once(video: Path, rubric_name: str) -> dict:
    cmd = [sys.executable, str(Path(__file__).resolve()),
           "--child", str(video), "--rubric", rubric_name]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    line = next((l for l in reversed(p.stdout.splitlines()) if l.startswith("{")), "")
    if not line:
        return {"ok": False, "error": f"자식이 결과를 안 냈다 (코드 {p.returncode})",
                "stderr": p.stderr[-400:]}
    return json.loads(line)


def criterion_e() -> tuple[bool, str]:
    """기준 E — 등급이 모델과 무관한가. 전제가 깨지면 이 측정의 범위가 틀린 것이다."""
    import inspect

    from supersub_agent import judge

    # `judge_criterion` 은 `Judge` 의 메서드다 — 모듈 함수로 찾으면 없다.
    src = inspect.getsource(judge.Judge.judge_criterion)
    ok = "criterion.grade_for(features)" in src
    return ok, ("Judge.judge_criterion 이 grade_for 로 등급을 받는다"
                if ok else "🔴 등급이 모델 경로로 넘어갔다 — 이 측정은 무효다")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--child", type=Path, help="내부용 — 한 회차만 돈다")
    ap.add_argument("--rubric", default="football_instep_shot.yaml")
    ap.add_argument("--runs", type=int, default=5, help="반복 (3장 정의는 5)")
    args = ap.parse_args()

    if args.child:
        child(args.child, args.rubric)
        return

    e_ok, e_msg = criterion_e()
    print(f"기준 E — {e_msg}\n")
    if not e_ok:
        raise SystemExit(1)

    verdicts: list[bool] = []
    for video, rubric_name in CLIPS:
        if not video.exists():
            print(f"⚠ 없는 클립이라 건너뛴다: {video}")
            continue
        print(f"=== {video.name} ({rubric_name}) · {args.runs}회 ===")
        runs = [run_once(video, rubric_name) for _ in range(args.runs)]
        for i, r in enumerate(runs, 1):
            print(f"  {i}회차: " + (f"{r['score']}점 ({r['grade']})" if r["ok"]
                                    else f"🔴 실패 — {r['error']}"))

        oks = [r["ok"] for r in runs]
        d = len(set(oks)) == 1
        if not all(oks):
            # 기준 D 불합격이거나 전 회차 실패. 뒤 기준은 판정하지 않는다.
            print(f"  D 품질 게이트 결과 불변: {'✅' if d else '🔴'}"
                  + ("  (전 회차 실패 — A~C 판정 불가)" if d else ""))
            verdicts.append(d and False)
            print()
            continue

        scores = [r["score"] for r in runs]
        sd = statistics.pstdev(scores)
        a = sd <= 3.0
        b = len({json.dumps(r["grades"], sort_keys=True) for r in runs}) == 1
        c = len({json.dumps(r["features"], sort_keys=True) for r in runs}) == 1
        print(f"  A 총점 표준편차 {sd:.2f} (≤3.0)      {'✅' if a else '🔴'}  {scores}")
        print(f"  B 등급 벡터 동일                  {'✅' if b else '🔴'}")
        print(f"  C features 비트 동일              {'✅' if c else '🔴'}")
        print(f"  D 품질 게이트 결과 불변           {'✅' if d else '🔴'}")
        if a and not c:
            print("  🔴 C 불합격은 A 합격으로 상쇄되지 않는다 — 등급 구간이"
                  " 가려 주고 있을 뿐이고 경계 클립에서 터진다 (사전 등록 4절)")
        verdicts.append(a and b and c and d)
        print()

    print("=" * 60)
    print(f"판정: {sum(verdicts)}/{len(verdicts)} 클립 합격"
          + ("  — 전부 합격" if verdicts and all(verdicts) else ""))
    raise SystemExit(0 if verdicts and all(verdicts) else 1)


if __name__ == "__main__":
    main()
