"""미결 `ho` 45번 5회차 — 구간이 짧아지면 **무엇이 먼저 깨지는가**.

판정 기준은 [`PREREGISTRATION.md`](PREREGISTRATION.md) 에 **돌리기 전에**
고정했다. 여기서 고치지 않는다.

🔴 **조사 회차다** — production 을 **import 만** 한다. `src/` 를 한 줄도
건드리지 않는다.

🔴 **GPU 를 안 쓴다.** `eval/phaseA/cache_target30/` 의 키포인트 사본을 읽는다.
그래서 47·49번의 전처리 갈림이 이 회차에 안 닿는다 — 픽셀을 다시 안 본다.

    uv run python eval/pending45_window_floor/measure_window_floor.py
"""
from __future__ import annotations

import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval" / "phaseA"))

import paths  # noqa: E402
from supersub_agent import features as F  # noqa: E402

#: 사전 등록이 정한 설정 셋 (4회차와 같다).
SETTINGS = (
    ("leg", "extension_peak"),
    ("arm", "extension_peak"),
    ("arm", "distal_apex"),
)

#: 사전 등록이 정한 창 길이. 여기서 늘리거나 줄이지 않는다.
LENGTHS = (60, 40, 30, 20, 15, 12, 10, 8, 6, 5)


def clips():
    """(클립 id, 키포인트) — 캐시 사본에서만 읽는다."""
    for npz in sorted(paths.cache_dir(30).glob("*.npz")):
        d = np.load(npz)
        yield npz.stem, d["keypoints"]


def swing_chain(kps, limb):
    """`extract_features` 가 고르는 것과 **같은** 스윙 측 체인.

    🔴 `extract_features` 는 `segment_phases` 에 **정규화한** 키포인트를 넘긴다
    (`norm = normalize(kps)`). 원본을 넘기면 다른 것을 재게 된다 — 그래서
    여기서도 정규화한 것과 그 위에서 고른 체인을 함께 돌려준다.
    """
    norm = F.normalize(kps)
    chain, _support = F.identify_limb(norm, limb, "auto")
    return norm, chain


def outcome(kps, chain, limb, event, window):
    """한 번의 `segment_phases` 결과를 **사유로** 남긴다.

    사유를 예외 메시지가 아니라 **경계 검사가 쓰는 조건 그대로** 가른다 —
    메시지 문구가 바뀌면 조용히 오분류되기 때문이다(`paik` 11번에서 배운 것:
    stdout 을 긁지 않는다).
    """
    try:
        ph = F.segment_phases(kps, chain, limb=limb, event=event, window=window)
        return "ok", ph.impact
    except F.InsufficientQuality as exc:
        msg = str(exc)
        if "분석 가능한 프레임이 없다" in msg:
            return "empty", None
        if "경계에 있음" in msg:
            return "boundary", None
        return "other:InsufficientQuality", None
    except Exception as exc:  # noqa: BLE001 — 어떤 실패였는지가 결과다
        return f"other:{type(exc).__name__}", None


def usable_range(kps, chain, limb, event):
    """`segment_phases` 가 보는 유효 구간 [first, last]. production 규칙 그대로."""
    series = F.chain_series(kps, chain)
    usable = F.valid_frames(kps, limb, chain) & np.isfinite(series)
    if not usable.any():
        return None
    first = int(np.argmax(usable))
    last = int(len(usable) - 1 - np.argmax(usable[::-1]))
    return first, last


def main() -> int:
    rows = []
    skipped = []          # 기준이 실패해 층을 못 나누는 (클립 × 설정)
    instrument_a = []     # 기준 A — 구간 전체를 창으로 준 것 == 창 없는 것

    for clip, kps in clips():
        for limb, event in SETTINGS:
            try:
                F.check_quality(kps, limb=limb, side="auto")
            except Exception as exc:  # noqa: BLE001
                skipped.append({"clip": clip, "limb": limb, "event": event,
                                "reason": f"quality:{type(exc).__name__}"})
                continue
            norm, chain = swing_chain(kps, limb)
            base_reason, base_impact = outcome(norm, chain, limb, event, None)
            rng = usable_range(norm, chain, limb, event)

            if base_reason != "ok" or rng is None:
                skipped.append({"clip": clip, "limb": limb, "event": event,
                                "reason": base_reason})
                continue
            first, last = rng
            e = base_impact

            # 기준 A — 유효 구간 전체를 창으로 주면 창 없는 것과 같은가.
            win_reason, win_impact = outcome(norm, chain, limb, event, (first, last + 1))
            instrument_a.append({
                "clip": clip, "limb": limb, "event": event,
                "same": win_reason == base_reason and win_impact == base_impact,
                "base": [base_reason, base_impact], "windowed": [win_reason, win_impact],
            })

            span = last - first + 1
            for L in LENGTHS:
                # 겹치지 않는 타일. 자투리는 버린다 (사전 등록).
                n_tiles = span // L
                for i in range(n_tiles):
                    a = first + i * L
                    b = a + L
                    reason, impact = outcome(norm, chain, limb, event, (a, b))
                    rows.append({
                        "clip": clip, "limb": limb, "event": event, "L": L,
                        "a": a, "b": b,
                        "layer": "E" if a <= e < b else "N",
                        "reason": reason,
                        "impact": impact,
                        # 성립했을 때 창 안 상대 위치 — 사후 관찰용
                        "pos": None if impact is None else impact - a,
                    })

    out = {"rows": rows, "skipped": skipped, "instrument_a": instrument_a}
    # 원자료는 15,710행이라 그대로 두면 2.4MB 다. 저장소에 남기는 것이 근거이므로
    # 버리지 않고 압축해서 둔다 (106KB).
    with gzip.open(HERE / "rows.json.gz", "wt", encoding="utf-8") as fh:
        json.dump(out, fh)
    report(out)
    return 0


def report(out) -> None:
    rows, skipped, inst = out["rows"], out["skipped"], out["instrument_a"]

    print(f"(클립 × 설정) 기준 성공 {len(inst)} · 층 못 나눔 {len(skipped)}"
          f" / {len(inst) + len(skipped)}")
    if skipped:
        by = defaultdict(int)
        for s in skipped:
            by[s["reason"]] += 1
        print("  못 나눈 사유:", dict(by))

    bad_a = [i for i in inst if not i["same"]]
    print(f"\n[A 계기] 구간 전체 창 == 창 없음 : 불일치 {len(bad_a)} / {len(inst)}")
    for b in bad_a[:5]:
        print("   ", b)

    others = [r for r in rows if r["reason"].startswith("other")]
    print(f"[C 계기] 분류 안 된 실패(other) : {len(others)} / {len(rows)}")
    for o in others[:5]:
        print("   ", o)

    print(f"\n타일 {len(rows)}개")
    print(f"{'L':>4} | {'산수':>6} | {'층 E':>16} | {'층 N':>18} | {'E-N':>6} | {'산수-N':>7}")
    print("-" * 78)
    table = {}
    for L in LENGTHS:
        sub = [r for r in rows if r["L"] == L]
        e = [r for r in sub if r["layer"] == "E"]
        n = [r for r in sub if r["layer"] == "N"]
        arith = (L - 4) / L
        er = sum(r["reason"] == "ok" for r in e) / len(e) if e else float("nan")
        nr = sum(r["reason"] == "ok" for r in n) / len(n) if n else float("nan")
        table[L] = {"arith": arith, "E": er, "N": nr, "nE": len(e), "nN": len(n)}
        print(f"{L:>4} | {arith:6.1%} | {er:7.1%} ({len(e):>4}) | "
              f"{nr:7.1%} ({len(n):>6}) | {er - nr:+6.1%} | {arith - nr:+7.1%}")

    # B — 층 E 가 산수와 ±15%p 안인가
    off_b = [L for L, t in table.items() if abs(t["E"] - t["arith"]) > 0.15]
    print(f"\n[B 계기] 층 E 가 (L-4)/L 에서 ±15%p 밖인 L : {off_b or '없음'}")

    # D — 모든 L 에서 층 N < 층 E
    flipped = [L for L, t in table.items() if not (t["N"] < t["E"])]
    print(f"[D] 층 N < 층 E 가 뒤집힌 L : {flipped or '없음'}")

    # E — 층 N 실패 중 boundary 비중
    nf = [r for r in rows if r["layer"] == "N" and r["reason"] != "ok"]
    nb = sum(r["reason"] == "boundary" for r in nf)
    print(f"[E] 층 N 실패 {len(nf)} 중 boundary {nb} = "
          f"{nb / len(nf):.1%}" if nf else "[E] 층 N 실패 0")

    # F — 층 N 이 산수보다 20%p 이상 낮은 L
    gap = [L for L, t in table.items() if t["arith"] - t["N"] >= 0.20]
    print(f"[F] 층 N 이 산수보다 20%p 이상 낮은 L : {gap or '없음'}")

    # G — 쏠림. 클립별 층 N 성립률, 하위 3편을 빼도 F 가 유지되는가
    per = defaultdict(lambda: [0, 0])
    for r in rows:
        if r["layer"] == "N":
            per[r["clip"]][1] += 1
            per[r["clip"]][0] += r["reason"] == "ok"
    ranked = sorted(per.items(), key=lambda kv: kv[1][0] / kv[1][1])
    print("\n[G] 클립별 층 N 성립률 — 낮은 쪽 5편 / 높은 쪽 3편")
    for c, (ok, tot) in ranked[:5]:
        print(f"    {c:<14} {ok / tot:6.1%} ({ok}/{tot})")
    print("    …")
    for c, (ok, tot) in ranked[-3:]:
        print(f"    {c:<14} {ok / tot:6.1%} ({ok}/{tot})")

    worst3 = {c for c, _ in ranked[:3]}
    print(f"\n[G] 하위 3편({', '.join(sorted(worst3))})을 빼고 다시:")
    kept = [r for r in rows if r["clip"] not in worst3]
    gap2 = []
    for L in LENGTHS:
        n = [r for r in kept if r["L"] == L and r["layer"] == "N"]
        if not n:
            continue
        nr = sum(r["reason"] == "ok" for r in n) / len(n)
        arith = (L - 4) / L
        if arith - nr >= 0.20:
            gap2.append(L)
    print(f"    F 가 유지되는 L : {gap2 or '없음'}")


if __name__ == "__main__":
    raise SystemExit(main())
