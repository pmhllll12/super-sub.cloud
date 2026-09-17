"""미결 `ho` 43번 ㉳ 2회차 — 창 안에서 나온 값은 **동작을 재는가, 분할을 재는가**.

판정 기준은 [`PREREGISTRATION.md`](PREREGISTRATION.md) 에 **재기 전에** 고정했다.

🔴 **조사 회차다 — `src/`·`rubrics/` 를 고치지 않는다.** production 을 import 만
한다. 기준 G 만 규칙을 **복제**해서 잰다(1회차 사후 관찰과 같은 형태).
🔴 **GPU 를 안 쓴다** — `eval/phaseA/cache_target30/` 의 키포인트 사본을 읽는다.

    uv run python eval/pending43_dribble_metrics/measure_window_metrics.py
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
from supersub_agent import scoring  # noqa: E402

#: 1회차와 같은 설정. `distal_apex` 는 임팩트를 높이로 정해 같은 축이 아니다.
SETTINGS = (("leg", "extension_peak"), ("arm", "extension_peak"))

#: 1회차 곡선의 굵은 값(10·15) + 양끝. 사전 등록이 정했다.
LENGTHS = (10, 15, 30, 60)

#: 창에 **묶이는** 지표 — 구간 경계가 정의에 들어 있다.
CUT_METRICS = ("hip_rotation_range_deg", "swing_hip_flexion_after_impact_deg")

#: 창에 **안 묶일 것으로 읽은** 지표 — `ankle_speed[t:]` 가 클립 끝까지 본다.
LEAK_METRIC = "follow_through_duration_frames"

#: D-2 가 쓰는 항목. 구간 의존 지표를 밴드로 쓰는 것이 이 둘뿐이다.
RUBRIC_PATH = ROOT / "rubrics" / "football_instep_shot.yaml"
BAND_CRITERIA = ("hip_rotation", "follow_through")

BEFORE = ROOT / "eval" / "pending45_multi_event" / "before.json"


def clips():
    for npz in sorted(paths.cache_dir(30).glob("*.npz")):
        d = np.load(npz)
        objects = {k[len("obj_"):]: d[k] for k in d.files if k.startswith("obj_")}
        yield npz.stem, d["keypoints"], objects


def _win(window):
    return {} if window is None else {"window": window}


def one(kps, objects, limb, event, window=None):
    """45번 4회차 `measure_multi_event.one()` 과 **같은 모양**으로 낸다 (기준 A)."""
    try:
        feats = F.extract_features(
            kps, objects, impact_limb=limb, impact_event=event, **_win(window)
        )
        return {"ok": True, "features": feats}
    except Exception as exc:  # noqa: BLE001 — 어떤 실패였는지가 결과다
        return {"ok": False, "error": type(exc).__name__}


def prepared(kps, limb):
    """1회차 `measure_spacing.prepared()` 와 같은 규칙의 유효 구간."""
    norm = F.normalize(kps)
    swing, _ = F.identify_limb(norm, limb, "auto")
    series = F.chain_series(norm, swing)
    usable = F.valid_frames(norm, limb, swing) & np.isfinite(series)
    if not usable.any():
        return None
    first = int(np.argmax(usable))
    last = int(len(usable) - 1 - np.argmax(usable[::-1]))
    return norm, swing, (first, last)


def phases_of(kps, limb, event, window=None):
    got = prepared(kps, limb)
    if got is None:
        return None
    norm, swing, _ = got
    try:
        return F.segment_phases(norm, swing, limb, event, **_win(window))
    except Exception:  # noqa: BLE001
        return None


def decel_pair(kps, t, ft_end):
    """`follow_through_duration_frames` 를 **production 규칙**과 **창 끝에서 끊은
    규칙**으로 각각 센다 (기준 G).

    🔴 `src/` 를 안 고치고 규칙을 여기 복제한다. production 의 `post` 는
    `ankle_speed[t:]` — 클립 끝까지다.
    """
    norm = F.normalize(kps)
    swing_knee, _plant = F.identify_legs(norm, "auto")
    swing_ankle = F.L_ANKLE if swing_knee == F.L_KNEE else F.R_ANKLE
    xy = norm[:, :, :2]
    speed = np.linalg.norm(np.diff(xy[:, swing_ankle], axis=0), axis=1)

    def count(post):
        thr = float(post[0]) * 0.3 if post.size else 0.0
        return int(np.argmax(post < thr)) if (post < thr).any() else int(len(post))

    return count(speed[t:]), count(speed[t:ft_end])


def grades(rubric, feats):
    out = {}
    for c in rubric.criteria:
        if c.id not in BAND_CRITERIA:
            continue
        try:
            out[c.id] = c.grade_for(feats)
        except Exception:  # noqa: BLE001 — 값이 없으면 판정에서 빠진다
            pass
    return out


def main() -> None:
    before = json.loads(BEFORE.read_text(encoding="utf-8"))
    rubric = scoring.load_rubric(RUBRIC_PATH)

    a_bad: list[str] = []
    g_changed: list[str] = []
    n_base = 0
    # L 별 집계
    agg = {L: {"pairs": 0, "leak_same": 0, "leak_diff": [],
               "outside": 0, "rel": {m: [] for m in CUT_METRICS},
               "worse": {m: 0 for m in CUT_METRICS},
               "changed": {m: 0 for m in CUT_METRICS},
               "grade_pairs": 0, "grade_changed": 0, "grade_down": 0,
               "grade_up": []} for L in LENGTHS}

    for cid, kps, objects in clips():
        for limb, event in SETTINGS:
            key = f"{cid}|{limb}|{event}"
            base = one(kps, objects, limb, event)
            n_base += 1

            # --- A: 45번 4회차 스냅샷과 비트 동일 ---
            if key in before and base != before[key]["features"]:
                a_bad.append(key)

            ph0 = phases_of(kps, limb, event)
            if not base["ok"] or ph0 is None:
                continue
            f0 = base["features"]
            t0 = ph0.impact

            # --- G: 누수를 창 끝에서 끊으면 window=None 산출이 바뀌는가 ---
            prod, bounded = decel_pair(kps, t0, ph0.follow_through[1])
            if prod != bounded:
                g_changed.append(f"{key}: {prod} → {bounded}")

            got = prepared(kps, limb)
            if got is None:
                continue
            _norm, _swing, (first, last) = got

            for L in LENGTHS:
                for a in range(first, last + 1 - L + 1, L):
                    win = (a, a + L)
                    ph = phases_of(kps, limb, event, win)
                    if ph is None or ph.impact != t0:
                        continue          # 같은 순간을 같은 정의로 잡은 짝만
                    res = one(kps, objects, limb, event, win)
                    if not res["ok"]:
                        continue
                    fw = res["features"]
                    r = agg[L]
                    r["pairs"] += 1

                    # C-1 · D-3 — 누수
                    if fw.get(LEAK_METRIC) == f0.get(LEAK_METRIC):
                        r["leak_same"] += 1
                    else:
                        r["leak_diff"].append(
                            f"{key} {win}: {f0.get(LEAK_METRIC)} → {fw.get(LEAK_METRIC)}")
                    if LEAK_METRIC in fw and t0 + int(fw[LEAK_METRIC]) >= win[1]:
                        r["outside"] += 1

                    # C-2 · D-1 — 창에 묶인 지표
                    for m in CUT_METRICS:
                        if m not in f0 or m not in fw:
                            continue
                        if abs(fw[m] - f0[m]) > 1e-9:
                            r["changed"][m] += 1
                            if fw[m] > f0[m] + 1e-9:
                                r["worse"][m] += 1     # 🔴 예측을 벗어난 방향
                        if abs(f0[m]) > 1e-9:
                            r["rel"][m].append((fw[m] - f0[m]) / f0[m] * 100.0)

                    # D-2 — 등급
                    g0, gw = grades(rubric, f0), grades(rubric, fw)
                    shared = set(g0) & set(gw)
                    for cid_ in shared:
                        r["grade_pairs"] += 1
                        if g0[cid_] != gw[cid_]:
                            r["grade_changed"] += 1
                            if gw[cid_] < g0[cid_]:
                                r["grade_down"] += 1
                            else:
                                r["grade_up"].append(
                                    f"{key} {win} {cid_}: {g0[cid_]} → {gw[cid_]}")

    # ---------------- 출력 ----------------
    print(f"window=None 산출 {n_base}개 (39 × 2 = 78 예상) — 계기 검사 ③\n")

    print("## 1. 짝 수와 누수\n")
    print("| L | 같은 임팩트 짝 | 누수지표 동일 | 창 밖을 읽음 |")
    print("|---:|---:|---:|---:|")
    for L in LENGTHS:
        r = agg[L]
        p = r["pairs"]
        same = f"{r['leak_same']}/{p}" if p else "—"
        out = f"{r['outside']}/{p} = {r['outside']/p:.0%}" if p else "—"
        print(f"| {L} | {p} | {same} | {out} |")

    print("\n## 2. 창에 묶인 지표 — 상대 변화 (중앙, %)\n")
    print("| L | " + " | ".join(CUT_METRICS) + " | 바뀐 짝 | 커진 짝(예측 위반) |")
    print("|---:|" + "---:|" * (len(CUT_METRICS) + 2))
    for L in LENGTHS:
        r = agg[L]
        cells = []
        for m in CUT_METRICS:
            v = r["rel"][m]
            cells.append(f"{np.median(v):+.1f}" if v else "—")
        chg = " / ".join(str(r["changed"][m]) for m in CUT_METRICS)
        bad = " / ".join(str(r["worse"][m]) for m in CUT_METRICS)
        print(f"| {L} | " + " | ".join(cells) + f" | {chg} | {bad} |")

    print("\n## 3. 등급 (축구 인스텝 `hip_rotation`·`follow_through`)\n")
    print("| L | 판정 짝 | 등급 바뀜 | 내려감 | 올라감 |")
    print("|---:|---:|---:|---:|---:|")
    for L in LENGTHS:
        r = agg[L]
        gp = r["grade_pairs"]
        chg = f"{r['grade_changed']}/{gp} = {r['grade_changed']/gp:.0%}" if gp else "—"
        print(f"| {L} | {gp} | {chg} | {r['grade_down']} | {len(r['grade_up'])} |")

    # ---------------- 판정 ----------------
    b_ok = agg[30]["pairs"] >= 20
    c1_diff = [d for L in LENGTHS for d in agg[L]["leak_diff"]]
    c1_ok = not c1_diff
    changed_any = any(agg[L]["changed"][m] for L in LENGTHS for m in CUT_METRICS)
    worse_any = sum(agg[L]["worse"][m] for L in LENGTHS for m in CUT_METRICS)
    c2_ok = changed_any and worse_any == 0
    c_ok = c1_ok and c2_ok

    print("\n## 판정\n")
    print("| 기준 | 내용 | 결과 | |")
    print("|---|---|---|---|")
    print(f"| A | `window=None` 이 45번 4회차 스냅샷과 비트 동일 | 불일치 **{len(a_bad)}** "
          f"| {'✅' if not a_bad else '🔴'} |")
    print(f"| B | `L=30` 짝 ≥ 20 | **{agg[30]['pairs']}쌍** | {'✅' if b_ok else '🔴'} |")
    print(f"| C-1 | 누수지표가 짝에서 100% 동일 | 불일치 **{len(c1_diff)}** "
          f"| {'✅ 예측대로' if c1_ok else '🔴 예측이 틀렸다'} |")
    print(f"| C-2 | 창 지표는 달라지고 **전부 작아진다** | 바뀜 "
          f"**{sum(agg[L]['changed'][m] for L in LENGTHS for m in CUT_METRICS)}** · "
          f"커진 것 **{worse_any}** | {'✅ 예측대로' if c2_ok else '🔴 예측이 틀렸다'} |")
    print(f"| C | 🔴 짝 예측 — **둘 다** | | {'✅' if c_ok else '🔴'} |")
    print("| D | 크기 보고 | 위 1~3절 | ✅ 보고함 |")
    print(f"| G | 창 끝에서 끊으면 `window=None` 이 바뀌는 산출 | **{len(g_changed)}개** "
          f"| {'✅ B-6 안 부른다' if not g_changed else '🔴 B-6 를 부른다'} |")

    if a_bad:
        print("\n🔴 A 불일치:", ", ".join(a_bad[:10]))
    if c1_diff:
        print("\n🔴 C-1 를 벗어난 짝:")
        for x in c1_diff[:10]:
            print("  " + x)
    for L in LENGTHS:
        for x in agg[L]["grade_up"][:5]:
            print(f"  🔴 등급이 올라간 짝 (L={L}): {x}")
    if g_changed:
        print(f"\n🔴 G — 창 끝에서 끊으면 달라지는 산출 {len(g_changed)}개:")
        for x in g_changed[:10]:
            print("  " + x)

    (HERE / "window_metrics_raw.json").write_text(
        json.dumps(
            {"n_base": n_base, "a_mismatch": a_bad, "g_changed": g_changed,
             "by_length": {str(L): {
                 "pairs": agg[L]["pairs"], "leak_same": agg[L]["leak_same"],
                 "leak_diff": agg[L]["leak_diff"], "outside": agg[L]["outside"],
                 "changed": agg[L]["changed"], "worse": agg[L]["worse"],
                 "rel_median": {m: (float(np.median(agg[L]["rel"][m]))
                                    if agg[L]["rel"][m] else None)
                                for m in CUT_METRICS},
                 "grade_pairs": agg[L]["grade_pairs"],
                 "grade_changed": agg[L]["grade_changed"],
                 "grade_down": agg[L]["grade_down"],
                 "grade_up": agg[L]["grade_up"],
             } for L in LENGTHS}},
            ensure_ascii=False, indent=1,
        ),
        encoding="utf-8",
    )


def posthoc() -> None:
    """🔴 **사후 관찰 — 판정에 안 쓴다.** 강등을 만드는 것이 **어느 항목**인가.

    사전 등록이 D-2 를 항목 합계로만 적어 두어서, 끝난 뒤에 갈라 본다.
    **판정 문장이 없다 — 크기만 본다.**
    """
    rubric = scoring.load_rubric(RUBRIC_PATH)
    print("\n\n## 🔴 사후 관찰 — 강등을 만드는 항목 (판정에 안 씀)\n")
    print("| L | 항목 | 판정 짝 | 내려감 | 비율 |")
    print("|---:|---|---:|---:|---:|")
    rows = {L: {c: [0, 0] for c in BAND_CRITERIA} for L in LENGTHS}
    #: 창 쪽에서 **지표가 아예 빠진** 짝 — 그 항목은 판정에서 제외되고
    #: 가중치가 재정규화된다(미결 21번의 규약). 위 표의 분모 차이가 이것이다.
    dropped = {L: {m: 0 for m in CUT_METRICS} for L in LENGTHS}

    for _cid, kps, objects in clips():
        for limb, event in SETTINGS:
            base = one(kps, objects, limb, event)
            ph0 = phases_of(kps, limb, event)
            got = prepared(kps, limb)
            if not base["ok"] or ph0 is None or got is None:
                continue
            f0, t0 = base["features"], ph0.impact
            _norm, _swing, (first, last) = got
            g0 = grades(rubric, f0)
            for L in LENGTHS:
                for a in range(first, last + 1 - L + 1, L):
                    win = (a, a + L)
                    ph = phases_of(kps, limb, event, win)
                    if ph is None or ph.impact != t0:
                        continue
                    res = one(kps, objects, limb, event, win)
                    if not res["ok"]:
                        continue
                    for m in CUT_METRICS:
                        if m in f0 and m not in res["features"]:
                            dropped[L][m] += 1
                    gw = grades(rubric, res["features"])
                    for c in set(g0) & set(gw):
                        rows[L][c][0] += 1
                        if gw[c] < g0[c]:
                            rows[L][c][1] += 1

    for L in LENGTHS:
        for c in BAND_CRITERIA:
            n, down = rows[L][c]
            rate = f"{down / n:.0%}" if n else "—"
            print(f"| {L} | `{c}` | {n} | {down} | **{rate}** |")

    print("\n🔴 창 쪽에서 지표가 **아예 빠진** 짝 (그 항목은 판정에서 제외된다)\n")
    print("| L | " + " | ".join(f"`{m}`" for m in CUT_METRICS) + " |")
    print("|---:|" + "---:|" * len(CUT_METRICS))
    for L in LENGTHS:
        print(f"| {L} | " + " | ".join(str(dropped[L][m]) for m in CUT_METRICS) + " |")


if __name__ == "__main__":
    main()
    if "--posthoc" in sys.argv:
        posthoc()
