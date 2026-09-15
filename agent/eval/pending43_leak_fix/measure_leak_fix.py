"""미결 `ho` 43번 ㉳ 3회차 — 마무리 길이가 **창 밖을 읽던 것**을 막는다.

판정 기준은 [`PREREGISTRATION.md`](PREREGISTRATION.md) 에 **구현 전에** 굳혔다.

🔴 **구현 회차다.** 그래서 **먼저 `--snapshot` 으로 변경 전 값을 뜨고**, 고친
뒤 `--check` 로 대 본다(45번 4회차와 같은 형태).

    uv run python eval/pending43_leak_fix/measure_leak_fix.py --snapshot
    #  … features.py 를 한 줄 고친다 …
    uv run python eval/pending43_leak_fix/measure_leak_fix.py --check

🔴 **GPU 를 안 쓴다** — `eval/phaseA/cache_target30/` 의 키포인트 사본을 읽는다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval" / "phaseA"))

import paths  # noqa: E402
from supersub_agent import features as F  # noqa: E402

#: 2회차와 같은 설정 — 그 회차가 기준 B 의 예측값을 낸 자리다.
SETTINGS = (("leg", "extension_peak"), ("arm", "extension_peak"))

SNAPSHOT = HERE / "before.json"

#: 🔴 사전 등록이 **값까지** 박은 예측. 결과를 보고 고치지 않는다.
PREDICTED = {
    "3R1kvNrGJK0|arm|extension_peak": (109, 104),
    "goeDWOVL95g|arm|extension_peak": (56, 47),
}
LEAK_METRIC = "follow_through_duration_frames"


def clips():
    for npz in sorted(paths.cache_dir(30).glob("*.npz")):
        d = np.load(npz)
        objects = {k[len("obj_"):]: d[k] for k in d.files if k.startswith("obj_")}
        yield npz.stem, d["keypoints"], objects


def one(kps, objects, limb, event):
    try:
        return {"ok": True, "features": F.extract_features(
            kps, objects, impact_limb=limb, impact_event=event)}
    except Exception as exc:  # noqa: BLE001 — 어떤 실패였는지가 결과다
        return {"ok": False, "error": type(exc).__name__}


def phases_of(kps, limb, event):
    norm = F.normalize(kps)
    swing, _ = F.identify_limb(norm, limb, "auto")
    try:
        p = F.segment_phases(norm, swing, limb, event)
        return {"ok": True, "takeback": list(p.takeback), "impact": p.impact,
                "follow_through": list(p.follow_through)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": type(exc).__name__}


def collect() -> dict:
    out = {}
    for cid, kps, objects in clips():
        for limb, event in SETTINGS:
            out[f"{cid}|{limb}|{event}"] = {
                "features": one(kps, objects, limb, event),
                "phases": phases_of(kps, limb, event),
            }
    return out


def check() -> int:
    before = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    now = collect()

    leak_changed: dict[str, tuple] = {}
    other_changed: list[str] = []
    phase_changed: list[str] = []

    for key, was in before.items():
        cur = now[key]
        if cur["phases"] != was["phases"]:
            phase_changed.append(key)
        f0 = was["features"].get("features") or {}
        f1 = cur["features"].get("features") or {}
        for name in sorted(set(f0) | set(f1)):
            if f0.get(name) == f1.get(name):
                continue
            if name == LEAK_METRIC:
                leak_changed[key] = (f0.get(name), f1.get(name))
            else:
                other_changed.append(f"{key}.{name}: {f0.get(name)} → {f1.get(name)}")

    as_predicted = leak_changed == PREDICTED
    b_ok = as_predicted and not other_changed and not phase_changed

    print(f"산출 {len(now)}개 (39 × 2 = 78 예상)\n")
    print("| 기준 | 내용 | 결과 | |")
    print("|---|---|---|---|")
    print(f"| B-1 | 바뀐 것이 **예측한 둘뿐**인가 | {len(leak_changed)}개 "
          f"| {'✅ 예측대로' if as_predicted else '🔴'} |")
    print(f"| B-2 | 다른 지표는 그대로인가 | 불일치 **{len(other_changed)}** "
          f"| {'✅' if not other_changed else '🔴'} |")
    print(f"| B-3 | 임팩트·구간은 그대로인가 | 불일치 **{len(phase_changed)}** "
          f"| {'✅' if not phase_changed else '🔴'} |")
    print(f"| B | 🔴 셋 다 | | {'✅' if b_ok else '🔴'} |")

    print("\n### 바뀐 산출\n")
    print("| 산출 | 전 | 후 | 예측 |")
    print("|---|---:|---:|---|")
    for key in sorted(set(leak_changed) | set(PREDICTED)):
        was_, now_ = leak_changed.get(key, ("—", "—"))
        pred = PREDICTED.get(key)
        mark = "✅ 예측대로" if pred and (was_, now_) == pred else "🔴 예측 밖"
        print(f"| `{key}` | {was_} | {now_} | {mark} |")

    for label, rows in (("B-2", other_changed), ("B-3", phase_changed)):
        if rows:
            print(f"\n🔴 {label} 불일치:")
            for x in rows[:20]:
                print("  " + str(x))

    (HERE / "leak_fix_raw.json").write_text(
        json.dumps({"leak_changed": leak_changed, "other_changed": other_changed,
                    "phase_changed": phase_changed}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    return 0 if b_ok else 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", action="store_true", help="변경 전 값을 뜬다")
    ap.add_argument("--check", action="store_true", help="변경 후 대 본다")
    args = ap.parse_args()

    if args.snapshot:
        SNAPSHOT.write_text(
            json.dumps(collect(), ensure_ascii=False, sort_keys=True),
            encoding="utf-8")
        print(f"변경 전 값 {len(json.loads(SNAPSHOT.read_text(encoding='utf-8')))}개를 "
              f"{SNAPSHOT.name} 에 떴다.")
        return
    if args.check:
        raise SystemExit(check())
    ap.error("--snapshot 또는 --check")


if __name__ == "__main__":
    main()
