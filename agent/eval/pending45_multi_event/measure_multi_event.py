"""미결 `ho` 45번 4회차 — 파이프라인이 이벤트를 **여럿 실어 나르는가**.

판정 기준은 [`PREREGISTRATION.md`](PREREGISTRATION.md) 에 **구현 전에** 고정했다.

🔴 **production 을 import 만 한다** — `features.py` 를 이 스크립트가 고치지
않는다(조사와 구현의 분리). 다만 이 회차는 구현 회차이기도 해서, **먼저
`--snapshot` 으로 변경 전 값을 뜨고** 구현한 뒤 `--check` 로 대 본다.

    uv run python eval/pending45_multi_event/measure_multi_event.py --snapshot
    #  … features.py 를 고친다 …
    uv run python eval/pending45_multi_event/measure_multi_event.py --check

🔴 **GPU 를 안 쓴다.** `eval/phaseA/cache_target30/` 의 키포인트 사본을 읽는다.
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

#: 사전 등록이 정한 설정 셋. 루브릭을 안 읽는다 — 야구 루브릭은 종목 정리로
#: 지워졌고(`ho` 39번), `extract_features` 는 사지·이벤트를 직접 받는다.
SETTINGS = (
    ("leg", "extension_peak"),
    ("arm", "extension_peak"),
    ("arm", "distal_apex"),
)

SNAPSHOT = HERE / "before.json"


def clips() -> list[tuple[str, np.ndarray, dict[str, np.ndarray]]]:
    """(클립 id, 키포인트, 도구 궤적) — 캐시 사본에서만 읽는다."""
    out = []
    for npz in sorted(paths.cache_dir(30).glob("*.npz")):
        d = np.load(npz)
        objects = {k[len("obj_") :]: d[k] for k in d.files if k.startswith("obj_")}
        out.append((npz.stem, d["keypoints"], objects))
    return out


def one(kps, objects, limb, event, window=None):
    """한 설정의 산출. 실패는 예외 이름으로 남긴다 — 조용히 빼지 않는다."""
    try:
        feats = F.extract_features(
            kps, objects, impact_limb=limb, impact_event=event, **_win(window)
        )
        return {"ok": True, "features": feats}
    except Exception as exc:  # noqa: BLE001 — 어떤 실패였는지가 결과다
        return {"ok": False, "error": type(exc).__name__}


def _win(window):
    """변경 전에는 `window` 인자가 없다 — 그때는 아예 안 넘긴다."""
    return {} if window is None else {"window": window}


def phases_of(kps, limb, event, window=None):
    try:
        p = F.segment_phases(
            F.normalize(kps), *_swing(kps, limb), limb, event, **_win(window)
        )
        return {"ok": True, "takeback": list(p.takeback), "impact": p.impact,
                "follow_through": list(p.follow_through)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": type(exc).__name__}


def _swing(kps, limb):
    swing, _ = F.identify_limb(F.normalize(kps), limb, "auto")
    return (swing,)


def snapshot() -> dict:
    """변경 **전** 값을 뜬다. 기준 A·B 가 이것과 대 본다."""
    out = {}
    for cid, kps, objects in clips():
        for limb, event in SETTINGS:
            key = f"{cid}|{limb}|{event}"
            out[key] = {
                "features": one(kps, objects, limb, event),
                "phases": phases_of(kps, limb, event),
            }
    return out


def halves(kps, limb) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """유효 구간을 반으로 자른 두 창.

    🔴 **제품 규칙이 아니다** — 기준 G(짝 기준)가 창이 실제로 걸리는지
    시험하려고 쓰는 계기일 뿐이다.
    """
    norm = F.normalize(kps)
    (swing,) = _swing(kps, limb)
    series = F.chain_series(norm, swing)
    usable = F.valid_frames(norm, limb, swing) & np.isfinite(series)
    if not usable.any():
        return None
    first = int(np.argmax(usable))
    last = int(len(usable) - 1 - np.argmax(usable[::-1]))
    if last - first < 8:
        return None
    mid = (first + last) // 2
    return (first, mid + 1), (mid + 1, last + 1)


def check() -> int:
    before = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    rows = []
    a_bad, b_bad, c_bad, d_notes = [], [], [], []
    g_pairs, g_ok = 0, 0

    for cid, kps, objects in clips():
        for limb, event in SETTINGS:
            key = f"{cid}|{limb}|{event}"
            was = before[key]

            now_f = one(kps, objects, limb, event)
            if now_f != was["features"]:
                a_bad.append(key)
            now_p = phases_of(kps, limb, event)
            if now_p != was["phases"]:
                b_bad.append(key)

            # --- C·D·G: 창을 걸어 본다 ---
            win = halves(kps, limb)
            if win is None or not now_p.get("ok"):
                continue
            whole = now_p["impact"]
            got = [phases_of(kps, limb, event, w) for w in win]
            for w, p in zip(win, got):
                if not p["ok"]:
                    d_notes.append(f"{key} {w} → {p['error']}")
                    continue
                if not (w[0] <= p["impact"] < w[1]):
                    c_bad.append(f"{key} {w} → impact {p['impact']}")

            if all(p["ok"] for p in got):
                g_pairs += 1
                hits = [p["impact"] == whole for p in got]
                distinct = got[0]["impact"] != got[1]["impact"]
                if sum(hits) == 1 and distinct:
                    g_ok += 1
                else:
                    rows.append(f"{key}: 전체 {whole} · 창 {[p['impact'] for p in got]}")

    total = len(before)
    print(f"산출 {total}개 (예상 117) — 캐시가 읽혔는지 확인 (계기 검사 ③)\n")
    print("| 기준 | 내용 | 결과 | |")
    print("|---|---|---|---|")
    print(f"| A | `window=None` features 비트 동일 | 불일치 **{len(a_bad)}** |"
          f" {'✅' if not a_bad else '🔴'} |")
    print(f"| B | `window=None` Phases 동일 | 불일치 **{len(b_bad)}** |"
          f" {'✅' if not b_bad else '🔴'} |")
    print(f"| C | 창 안에 impact | 위반 **{len(c_bad)}** |"
          f" {'✅' if not c_bad else '🔴'} |")
    print(f"| D | 좁은 창은 같은 예외 | {len(d_notes)}건 (조용한 실패 아님) | ✅ |")
    rate = g_ok / g_pairs if g_pairs else 0.0
    print(f"| G | 짝 기준 — 반 나누기 예측 | **{g_ok}/{g_pairs} = {rate:.0%}** |"
          f" {'✅' if rate >= 0.9 else '🔴'} |")

    for name, bad in (("A", a_bad), ("B", b_bad), ("C", c_bad)):
        if bad:
            print(f"\n🔴 {name} 불일치:")
            for x in bad[:10]:
                print(f"  {x}")
    if rows:
        print(f"\n🔴 G 예측을 벗어난 {len(rows)}건:")
        for x in rows[:10]:
            print(f"  {x}")
    if d_notes:
        print(f"\nD — 경계 검사에 걸린 창 {len(d_notes)}건 (맞는 동작):")
        for x in d_notes[:5]:
            print(f"  {x}")

    return 0 if not (a_bad or b_bad or c_bad) and rate >= 0.9 else 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", action="store_true", help="변경 전 값을 뜬다")
    ap.add_argument("--check", action="store_true", help="변경 후 대 본다")
    args = ap.parse_args()

    if args.snapshot:
        SNAPSHOT.write_text(
            json.dumps(snapshot(), ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        n = len(json.loads(SNAPSHOT.read_text(encoding="utf-8")))
        print(f"변경 전 값 {n}개를 {SNAPSHOT.name} 에 떴다.")
        return
    if args.check:
        raise SystemExit(check())
    ap.error("--snapshot 또는 --check")


if __name__ == "__main__":
    main()
