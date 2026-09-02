"""8단계 — E-1 / E-2 의 임팩트 영향 산정 + 60fps 수렴 검정. **구현이 아니라 산정이다.**

작업 2.1 / 2.4 / 2.5 와 작업 3에 답한다.

표 21  방식별 임팩트 이동 규모 (base 60fps 기준)
표 22  fps 불변성 — 60/30/20/15/12에서 같은 임팩트를 고르는 비율
표 23  60fps 수렴 검정 — 정보 손실 회복인가, 다같이 고정된 것인가
표 24  실패 모드 — E-1 반폭 바닥, E-2 스냅 손실·마스크 초과
"""
from __future__ import annotations

import numpy as np

from core import FACTORS, FPS_OF, external_pose_threshold, load_clips, side_of
from methods import TAUS, e1_halfwidth, impact_of
from supersub_agent import features as F


def variants() -> list[tuple[str, str, float]]:
    """(라벨, method, tau) 목록. base·E2는 tau와 무관하므로 한 번만 돈다."""
    out = [("base (무수정)", "base", 0.0), ("E-2 (격자만)", "E2", 0.0)]
    for name, tau in TAUS.items():
        out.append((f"E-1 τ={name}", "E1", tau))
        out.append((f"E-1+E-2 τ={name}", "E1E2", tau))
    return out


def main() -> None:
    clips = load_clips()
    VARS = variants()
    # rec[label][k][clip] = (snapped_idx, phys, diag)
    rec: dict[str, dict[int, dict[str, tuple]]] = {
        lb: {k: {} for k in FACTORS} for lb, _, _ in VARS
    }
    u60_of: dict[str, np.ndarray] = {}
    side60: dict[str, str] = {}

    with external_pose_threshold():
        for name, kp in clips.items():
            try:
                n60 = F.normalize(kp)
                sw60, _ = F.identify_limb(n60, "arm", "auto")
                s60 = F.chain_series(n60, sw60)
                u60_of[name] = F.valid_frames(n60, "arm", sw60) & np.isfinite(s60)
                side60[name] = side_of(sw60)
            except F.InsufficientQuality:
                continue

            for k in FACTORS:
                try:
                    nk = F.normalize(kp[::k])
                    swk, _ = F.identify_limb(nk, "arm", "auto")
                except F.InsufficientQuality:
                    continue
                # 스윙 팔이 뒤집힌 경우는 임팩트 비교에서 뺀다 (독립 원인, 표 9)
                if side_of(swk) != side60[name]:
                    continue
                for lb, method, tau in VARS:
                    try:
                        rec[lb][k][name] = impact_of(nk, swk, "arm", k, method, tau)
                    except (F.InsufficientQuality, ValueError):
                        pass

    base60 = {n: v[1] for n, v in rec["base (무수정)"][1].items()}

    print(f"클립 {len(clips)}건 · base 60fps 임팩트 산출 {len(base60)}건\n")

    print("표 21 — 방식별 임팩트 이동 규모 (base 60fps 임팩트 대비, 물리 프레임)")
    print(f"{'방식':>18} {'fps':>4} {'n':>4} {'동일':>6} {'|이동| 중앙':>11} "
          f"{'평균':>7} {'최대':>6}")
    for lb, _, _ in VARS:
        for k in (1, 4):          # 60fps와 15fps만 보여 준다 (전체는 표 23)
            common = [n for n in rec[lb][k] if n in base60]
            if not common:
                continue
            d = np.array([abs(rec[lb][k][n][1] - base60[n]) for n in common])
            print(f"{lb:>18} {FPS_OF[k]:>4} {len(d):>4} {(d == 0).mean() * 100:>5.0f}% "
                  f"{np.median(d):>10.0f} {d.mean():>7.1f} {d.max():>6.0f}")

    print("\n표 22 — fps 불변성 (한 클립이 60/30/20/15/12에서 같은 물리 임팩트를 고르는가)")
    print(f"{'방식':>18} {'5개 fps 전부 산출':>16} {'전부 동일':>10} "
          f"{'60 대비 동일(30/20/15/12)':>28}")
    for lb, _, _ in VARS:
        allk = [n for n in rec[lb][1] if all(n in rec[lb][k] for k in FACTORS)]
        if not allk:
            continue
        same_all = sum(
            1 for n in allk
            if len({rec[lb][k][n][1] for k in FACTORS}) == 1
        )
        per = []
        for k in FACTORS[1:]:
            eq = sum(1 for n in allk if rec[lb][k][n][1] == rec[lb][1][n][1])
            per.append(f"{eq / len(allk) * 100:.0f}%")
        print(f"{lb:>18} {len(allk):>16} {same_all / len(allk) * 100:>9.0f}% "
              f"{'  '.join(per):>28}")

    print("\n표 23 — 60fps 수렴 검정 (거리 = |해당 fps 임팩트 − base 60fps 임팩트|, 물리 프레임)")
    print("  ※ 60fps는 정답이 아니다. 솎기 전 원본이므로 **정보 우위** 기준일 뿐이다.")
    print(f"{'방식':>18} " + " ".join(f"{FPS_OF[k]:>10}fps" for k in FACTORS))
    for lb, _, _ in VARS:
        cells = []
        for k in FACTORS:
            common = [n for n in rec[lb][k] if n in base60]
            d = np.array([abs(rec[lb][k][n][1] - base60[n]) for n in common])
            cells.append(f"{np.median(d):>5.0f}/{d.mean():>6.1f}" if len(d) else "     -")
        print(f"{lb:>18} " + " ".join(f"{c:>13}" for c in cells))
    print("  (셀 = 거리 중앙 / 평균)")

    print("\n  ≤2프레임 안에 드는 비율")
    print(f"{'방식':>18} " + " ".join(f"{FPS_OF[k]:>7}fps" for k in FACTORS))
    for lb, _, _ in VARS:
        cells = []
        for k in FACTORS:
            common = [n for n in rec[lb][k] if n in base60]
            d = np.array([abs(rec[lb][k][n][1] - base60[n]) for n in common])
            cells.append(f"{(d <= 2).mean() * 100:>6.0f}%" if len(d) else "     -")
        print(f"{lb:>18} " + " ".join(f"{c:>10}" for c in cells))

    print("\n표 24 — 실패 모드")
    print("  (a) E-1 반폭이 1프레임으로 바닥치는가 (τ가 한 프레임 간격보다 짧을 때)")
    print(f"{'τ':>10} " + " ".join(f"{FPS_OF[k]:>12}fps" for k in FACTORS))
    for name, tau in TAUS.items():
        cells = []
        for k in FACTORS:
            h, floored = e1_halfwidth(k, tau)
            cells.append(f"{h}f={h * k / 60:.3f}s{'*' if floored else ' '}")
        print(f"{name:>10} " + " ".join(f"{c:>15}" for c in cells))
    print("        * = 바닥침 (요구한 τ보다 넓은 창을 쓰게 된다)")

    print("\n  (b) E-2 스냅 손실 — 60Hz에서 찾은 임팩트를 데시메이션 격자로 되돌릴 때")
    for lb, method, _ in VARS:
        if method not in ("E2", "E1E2"):
            continue
        for k in (2, 4):
            v = [d["snap_loss_frames"] for _n, (_i, _p, d) in rec[lb][k].items()]
            if not v:
                continue
            v = np.array(v)
            print(f"    {lb:>18} {FPS_OF[k]:>3}fps  손실 0프레임 {(v == 0).mean() * 100:>3.0f}%   "
                  f"중앙 {np.median(v):.1f}   최대 {v.max():.0f}")

    print("\n  (c) E-2 보간 임팩트가 60fps usable 마스크 밖에 놓이는 비율")
    for lb, method, _ in VARS:
        if method not in ("E2", "E1E2"):
            continue
        cells = []
        for k in FACTORS:
            bad = tot = 0
            for n, (_i, p, _d) in rec[lb][k].items():
                u = u60_of.get(n)
                if u is None:
                    continue
                tot += 1
                pi = int(round(p))
                if pi >= len(u) or not u[pi]:
                    bad += 1
            cells.append(f"{bad / tot * 100:>5.1f}%" if tot else "    -")
        print(f"    {lb:>18} " + " ".join(f"{FPS_OF[k]:>3}fps {c}" for k, c in
                                          zip(FACTORS, cells)))


if __name__ == "__main__":
    main()
