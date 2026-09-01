"""9단계 — E-1 / E-2 의 지표·등급 영향 산정 (작업 2.2 / 2.3). **구현이 아니다.**

두 가지를 나눠 본다.

  (i)  채택 영향  — 같은 fps에서 base 대비 무엇이 바뀌는가 (부작용 상한 판단용)
  (ii) fps 일관성 — 그 방식 안에서 60fps와 15fps가 같은 등급을 내는가 (주장할 것)

E-2 단독과 E-1 τ=1/60초는 step8에서 base와 **정확히 동일**함이 확인됐으므로 여기서
돌리지 않는다.

표 25  채택 영향 — 지표 동일률과 |Δ| 중앙 (15fps, base 대비)
표 26  채택 영향 — 최종 등급 변화 (15fps, base 대비)
표 27  fps 일관성 — 방식 안에서 60fps 대비 등급이 유지되는 비율
"""
from __future__ import annotations

import numpy as np

from core import RUBRIC_BASEBALL, external_pose_threshold, load_clips
from methods import patched_segment
from supersub_agent import features as F
from supersub_agent import scoring

VARIANTS = [
    ("base (무수정)", "base", 0.0),
    # τ=1/60초 + 공통 60Hz 격자 = 두 축을 **모두** 제대로 고정한 형태.
    # (E-1 단독 τ=1/60초는 base와 동일하므로 병용형만 본다.)
    ("E-1+E-2 τ=1/60초", "E1E2", 1 / 60),
    ("E-1 τ=1/30초", "E1", 1 / 30),
    ("E-1+E-2 τ=1/30초", "E1E2", 1 / 30),
    ("E-1 τ=1/12초", "E1", 1 / 12),
    ("E-1+E-2 τ=1/12초", "E1E2", 1 / 12),
]
KS = (1, 2, 4)                                   # 60 / 30 / 15 fps
FPS = {1: 60, 2: 30, 4: 15}
METRICS = [
    "swing_elbow_angle_at_impact", "plant_knee_angle_at_impact",
    "trunk_forward_lean_deg_at_impact", "hip_shoulder_separation_deg",
    "swing_shoulder_flexion_after_impact_deg",
]


def main() -> None:
    rubric = scoring.load_rubric(RUBRIC_BASEBALL)
    clips = load_clips()

    feats: dict[str, dict[int, dict[str, dict | None]]] = {
        lb: {k: {} for k in KS} for lb, _, _ in VARIANTS
    }
    with external_pose_threshold():
        for lb, method, tau in VARIANTS:
            for k in KS:
                with patched_segment(k, method, tau):
                    for name, kp in clips.items():
                        try:
                            feats[lb][k][name] = F.extract_features(
                                kp[::k], objects=None, impact_limb="arm",
                                impact_event="extension_peak", swing_side="auto",
                            )
                        except Exception:            # noqa: BLE001
                            feats[lb][k][name] = None

    def score_of(f: dict) -> dict:
        judged = {c.id: {"grade": c.grade_for(f), "evidence": "", "metric_ref": ""}
                  for c in rubric.applicable_criteria(f)}
        return scoring.aggregate(judged, rubric)

    base = feats["base (무수정)"]

    print("표 25 — 채택 영향: 15fps에서 base 대비 지표 변화")
    print(f"{'방식':>18} {'n':>4} " + " ".join(f"{m.split('_')[1][:6]:>13}" for m in METRICS))
    print(f"{'':>18} {'':>4} " + " ".join(f"{'동일/|Δ|중앙':>13}" for _ in METRICS))
    for lb, _, _ in VARIANTS[1:]:
        common = [n for n in clips
                  if base[4].get(n) is not None and feats[lb][4].get(n) is not None]
        cells = []
        for m in METRICS:
            pr = [(base[4][n][m], feats[lb][4][n][m]) for n in common
                  if m in base[4][n] and m in feats[lb][4][n]]
            if not pr:
                cells.append("           -")
                continue
            a = np.array([p[0] for p in pr], float)
            b = np.array([p[1] for p in pr], float)
            cells.append(f"{(a == b).mean() * 100:>3.0f}%/{np.median(np.abs(b - a)):>6.1f}")
        print(f"{lb:>18} {len(common):>4} " + " ".join(f"{c:>13}" for c in cells))

    print("\n표 26 — 채택 영향: 15fps에서 base 대비 등급 변화")
    print(f"{'방식':>18} {'n':>4} {'항목 등급 변화':>14} {'최종 등급 변화':>14} "
          f"{'|Δ총점| 중앙':>12}")
    for lb, _, _ in VARIANTS[1:]:
        common = [n for n in clips
                  if base[4].get(n) is not None and feats[lb][4].get(n) is not None]
        chg = tot = 0
        for c in rubric.criteria:
            for n in common:
                f1, f2 = base[4][n], feats[lb][4][n]
                if c.is_applicable(f1) and c.is_applicable(f2):
                    tot += 1
                    chg += c.grade_for(f1) != c.grade_for(f2)
        sc = [(score_of(base[4][n]), score_of(feats[lb][4][n])) for n in common]
        gchg = sum(1 for a, b in sc if a["grade"] != b["grade"])
        d = np.array([b["score"] - a["score"] for a, b in sc])
        print(f"{lb:>18} {len(common):>4} {chg / tot * 100:>13.0f}% "
              f"{gchg / len(sc) * 100:>13.0f}% {np.median(np.abs(d)):>11.0f}점")

    print("\n표 27 — fps 일관성: 방식 안에서 60fps 대비 등급이 유지되는가")
    print("  (주장할 수 있는 것은 이 표뿐이다 — 정확도가 아니라 일관성이다)")
    print(f"{'방식':>18} " + " ".join(
        f"{'60 vs ' + str(FPS[k]) + 'fps':>22}" for k in KS[1:]))
    print(f"{'':>18} " + " ".join(f"{'n / 항목변화 / 최종변화':>22}" for _ in KS[1:]))
    for lb, _, _ in VARIANTS:
        cells = []
        for k in KS[1:]:
            common = [n for n in clips
                      if feats[lb][1].get(n) is not None and feats[lb][k].get(n) is not None]
            chg = tot = 0
            for c in rubric.criteria:
                for n in common:
                    f1, f2 = feats[lb][1][n], feats[lb][k][n]
                    if c.is_applicable(f1) and c.is_applicable(f2):
                        tot += 1
                        chg += c.grade_for(f1) != c.grade_for(f2)
            sc = [(score_of(feats[lb][1][n]), score_of(feats[lb][k][n])) for n in common]
            gchg = sum(1 for a, b in sc if a["grade"] != b["grade"])
            cells.append(f"{len(common):>4} / {chg / tot * 100:>3.0f}% / {gchg / len(sc) * 100:>3.0f}%")
        print(f"{lb:>18} " + " ".join(f"{c:>22}" for c in cells))

    print("\n표 28 — 지표 산출 성공률 (게이트·경계 규칙 반려 포함)")
    print(f"{'방식':>18} " + " ".join(f"{FPS[k]:>8}fps" for k in KS))
    for lb, _, _ in VARIANTS:
        cells = [f"{sum(1 for v in feats[lb][k].values() if v is not None):>4}/400"
                 for k in KS]
        print(f"{lb:>18} " + " ".join(f"{c:>11}" for c in cells))


if __name__ == "__main__":
    main()
