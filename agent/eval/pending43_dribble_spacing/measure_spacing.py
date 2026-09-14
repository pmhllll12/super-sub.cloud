"""미결 `ho` 43번 ㉳ 1회차 — 간격이 **짧아지면** 구간 분할이 어디서 무너지나.

판정 기준은 [`PREREGISTRATION.md`](PREREGISTRATION.md) 에 **재기 전에**
고정했다(`e2f079e`).

🔴 **조사 회차다 — `src/` 를 고치지 않는다.** production 을 import 만 한다.
🔴 **GPU 를 안 쓴다** — `eval/phaseA/cache_target30/` 의 키포인트 사본을 읽는다.

    uv run python eval/pending43_dribble_spacing/measure_spacing.py
"""
from __future__ import annotations

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

#: 사전 등록이 정한 구간 길이. 4 는 **구조적으로 불가능한 값**이라 계기 검사다.
LENGTHS = (4, 5, 6, 8, 10, 12, 15, 20, 30, 45, 60)

#: 🔴 `distal_apex` 를 뺐다 — G 가 각속도를 계기로 쓰는데 그쪽은 높이로
#: 임팩트를 정해 같은 축이 아니다.
SETTINGS = (("leg", "extension_peak"), ("arm", "extension_peak"))


def clips():
    for npz in sorted(paths.cache_dir(30).glob("*.npz")):
        yield npz.stem, np.load(npz)["keypoints"]


def prepared(kps, limb):
    """(정규화 키포인트, 스윙 체인, 각속도, 유효 마스크, 유효 구간)."""
    norm = F.normalize(kps)
    swing, _ = F.identify_limb(norm, limb, "auto")
    series = F.chain_series(norm, swing)
    usable = F.valid_frames(norm, limb, swing) & np.isfinite(series)
    if not usable.any():
        return None
    first = int(np.argmax(usable))
    last = int(len(usable) - 1 - np.argmax(usable[::-1]))
    return norm, swing, np.gradient(series), usable, (first, last)


def main() -> None:
    rows: dict[int, dict] = {L: {"ok": 0, "tried": 0, "pct": []} for L in LENGTHS}
    n_clips = 0

    for cid, kps in clips():
        for limb, event in SETTINGS:
            got = prepared(kps, limb)
            if got is None:
                continue
            norm, swing, velocity, usable, (first, last) = got
            n_clips += 1

            # 🔴 백분위의 분모는 **클립 전체**다. 구간 안에서 재면 argmax 라
            #    언제나 100 이 나온다 — 정의상 참이라 아무것도 말해 주지 않는다.
            pool = velocity[usable & np.isfinite(velocity)]
            if pool.size == 0:
                continue

            for L in LENGTHS:
                # 타일링이 유효 구간을 넘지 않게 한다. 넘으면 미검출 구간이
                # 분모에 들어가 "어려워서"가 아니라 "클립이 끝나서" 실패한다.
                for a in range(first, last + 1 - L + 1, L):
                    win = (a, a + L)
                    rows[L]["tried"] += 1
                    try:
                        ph = F.segment_phases(norm, swing, limb, event, window=win)
                    except F.InsufficientQuality:
                        continue
                    rows[L]["ok"] += 1
                    v = velocity[ph.impact]
                    if np.isfinite(v):
                        rows[L]["pct"].append(float((pool < v).mean() * 100.0))

    print(f"클립×설정 {n_clips}개 (39 × 2 = 78 예상) — 계기 검사 ③\n")
    print("| L (프레임) | 시도 | 성립 | 성립률 | 임팩트 각속도 백분위 (중앙) |")
    print("|---:|---:|---:|---:|---:|")
    curve = []
    for L in LENGTHS:
        r = rows[L]
        rate = r["ok"] / r["tried"] if r["tried"] else 0.0
        med = float(np.median(r["pct"])) if r["pct"] else float("nan")
        curve.append((L, rate, med))
        print(f"| {L} | {r['tried']} | {r['ok']} | **{rate:.0%}** | "
              f"{med:.1f}" + (" |" if r["pct"] else " (없음) |"))

    # --- 판정 ---
    a_ok = rows[4]["ok"] == 0
    b_ok = all(rows[L]["tried"] > 0 for L in LENGTHS)
    mono = [curve[i][1] <= curve[i + 1][1] + 1e-9 for i in range(len(curve) - 1)]
    c_bad = [f"L={curve[i][0]}→{curve[i+1][0]}" for i, ok in enumerate(mono) if not ok]
    need90 = next((L for L, rate, _ in curve if rate >= 0.90), None)
    g_small = next(m for L, _, m in curve if L == 5)
    g_large = next(m for L, _, m in curve if L == 60)
    g_ok = g_small < g_large

    print("\n| 기준 | 내용 | 결과 | |")
    print("|---|---|---|---|")
    print(f"| A | 계기 검사 — `L ≤ 4` 성립 0건 | **{rows[4]['ok']}건** |"
          f" {'✅' if a_ok else '🔴'} |")
    print(f"| B | `L` 11개 전부 남는가 | {sum(rows[L]['tried'] > 0 for L in LENGTHS)}/11 |"
          f" {'✅' if b_ok else '🔴'} |")
    print(f"| C | 성립률이 `L` 에 단조 비감소 | 위반 **{len(c_bad)}** |"
          f" {'✅' if not c_bad else '🔴'} |")
    print(f"| D | 성립률 90% 에 필요한 `L` | **{need90 if need90 else '없음'}** | 보고 |")
    print(f"| G | 짝 기준 — `L=5` 백분위 < `L=60` | **{g_small:.1f} < {g_large:.1f}** |"
          f" {'✅ 예측대로' if g_ok else '🔴 예측이 틀렸다'} |")
    if c_bad:
        print("\n🔴 C 위반:", ", ".join(c_bad))

    (HERE / "spacing_raw.json").write_text(
        json.dumps(
            {str(L): {"tried": rows[L]["tried"], "ok": rows[L]["ok"],
                      "pct_median": (float(np.median(rows[L]["pct"]))
                                     if rows[L]["pct"] else None)}
             for L in LENGTHS},
            ensure_ascii=False, indent=1,
        ),
        encoding="utf-8",
    )


def posthoc() -> None:
    """🔴 **사후 관찰 — 판정에 안 쓴다.** 「그냥 `2` 를 낮추면 되지 않나」.

    경계 검사 `impact - first < m or last - impact < m` 의 `m` 을 바꿔 본다.
    🔴 **`src/` 를 안 고친다** — 규칙을 여기 복제해서 잰다(로드맵 2절이 허용한
    형태). production 의 `m` 은 **2 그대로**다.

    사전 등록이 끝난 뒤에 떠오른 질문이라 **판정 문장이 없다.** 크기만 본다.
    """
    print("\n\n## 🔴 사후 관찰 — 경계 여유 `m` 을 바꾸면 (판정에 안 씀)\n")
    print("| m | L | 시도 | 성립 | 성립률 | 백분위(중앙) |")
    print("|---:|---:|---:|---:|---:|---:|")
    for m in (0, 1, 2):
        for L in (10, 15, 30):
            tried = ok = 0
            pcts = []
            for _cid, kps in clips():
                for limb, _event in SETTINGS:
                    got = prepared(kps, limb)
                    if got is None:
                        continue
                    norm, swing, velocity, usable, (first, last) = got
                    pool = velocity[usable & np.isfinite(velocity)]
                    if pool.size == 0:
                        continue
                    for a in range(first, last + 1 - L + 1, L):
                        tried += 1
                        w = usable.copy()
                        w[:a] = False
                        w[a + L:] = False
                        cand = w & np.isfinite(velocity)
                        if not cand.any():
                            continue
                        t = int(np.argmax(np.where(cand, velocity, -np.inf)))
                        lo = int(np.argmax(w))
                        hi = int(len(w) - 1 - np.argmax(w[::-1]))
                        if t - lo < m or hi - t < m:   # production 과 같은 규칙
                            continue
                        ok += 1
                        pcts.append(float((pool < velocity[t]).mean() * 100.0))
            rate = ok / tried if tried else 0.0
            med = float(np.median(pcts)) if pcts else float("nan")
            star = " ← production" if m == 2 else ""
            print(f"| {m} | {L} | {tried} | {ok} | **{rate:.0%}** | {med:.1f} |{star}")


if __name__ == "__main__":
    main()
    if "--posthoc" in sys.argv:
        posthoc()
