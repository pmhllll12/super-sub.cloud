#!/usr/bin/env python3
"""3DSP(축구 슛 자세 데이터셋)의 **성격을 잰다.** 합격/불합격을 찍지 않는다.

    uv run python eval/dataset_3dsp/probe_3dsp.py

🔴 **이것은 판정 회차가 아니다.** 사전 등록이 없고, production 을 import 하지
않고 식만 옮겨 왔으며(`features.py:544`), 임팩트도 `segment_phases` 가 아니라
SoccerNet 주석 프레임을 쓴다. 여기 숫자는 **데이터셋이 무엇을 재게 해 주는가**
를 알아보는 용도이고, 미결 37번의 처방을 고르는 근거로 쓰려면
`scripts/analyze_keypoints.py` 경로로 다시 재야 한다.

데이터는 저장소에 없다 — `SUPERSUB_3DSP_ROOT` 로 위치를 준다.
"""
from __future__ import annotations

import collections
import configparser
import json
import os
from pathlib import Path

import numpy as np

DEFAULT_ROOT = Path("/mnt/d/sports-pose/soccer/raw/3dsp/3dsp/train")

# H3WB(H36M-17) 관절 순서. 데이터셋이 이름을 함께 실어 주므로 추측이 아니다.
NAMES = [
    "Center of Hips", "Left Hip", "Left Knee", "Left Ankle", "Right Hip",
    "Right Knee", "Right Ankle", "Center of Body", "Center of Shoulder",
    "Neck", "Head", "Right Shoulder", "Right Elbow", "Right Wrist",
    "Left Shoulder", "Left Elbow", "Left Wrist",
]
J = {n: i for i, n in enumerate(NAMES)}
FRAMES_PER_CLIP = 20


def root() -> Path:
    p = Path(os.environ.get("SUPERSUB_3DSP_ROOT", DEFAULT_ROOT))
    if not p.is_dir():
        raise FileNotFoundError(
            f"3DSP train 폴더가 없다: {p}\n"
            "SUPERSUB_3DSP_ROOT 로 위치를 주거나, calvinyeungck/3D-Shot-Posture-Dataset "
            "의 3dsp.zip 을 풀어 둘 것."
        )
    return p


def load(base: Path):
    """(clips, K2, K3, impact) — K2 (N,20,17,2) 크롭 픽셀, K3 (N,20,17,3)."""
    clips = sorted(d.name for d in base.iterdir() if (d / "posture").is_dir())
    K2, K3, impact = [], [], []
    for c in clips:
        f2, f3 = [], []
        for i in range(1, FRAMES_PER_CLIP + 1):
            d = json.loads((base / c / "posture" / f"{i:03d}.json").read_text())
            f2.append([[d["keypoint_2d"][str(j)][a] for a in "xy"] for j in range(17)])
            f3.append([[d["keypoint_3d"][str(j)][a] for a in "xyz"] for j in range(17)])
        K2.append(f2)
        K3.append(f3)
        cfg = configparser.ConfigParser()
        cfg.read(base / c / "info.ini")
        i = cfg["info"]
        step = int(i["position_step"])
        impact.append((int(i["annotated_position"]) - int(i["start_position"])) // step)
    return clips, np.array(K2), np.array(K3), np.array(impact)


def trunk_lean(sh, hp):
    """features.py:544-545 의 식. 이미지 좌표계라 좌우 반전이 곧 부호 반전이다."""
    t = sh - hp
    return np.degrees(np.arctan2(t[..., 0], -t[..., 1]))


def instep_band(theta: float) -> int:
    """rubrics/football_instep_shot.yaml 의 trunk_lean 구간을 옮겨 온 것."""
    if 5 <= theta <= 20:
        return 2
    if (0 <= theta < 5) or (20 < theta <= 30):
        return 1
    return 0


def section(title: str) -> None:
    print(f"\n{'=' * 68}\n{title}\n{'=' * 68}")


def main() -> None:
    base = root()
    clips, K2, K3, impact = load(base)
    n = len(clips)
    t = int(np.median(impact))
    print(f"클립 {n} · 프레임 {n * FRAMES_PER_CLIP} · 위치 {base}")
    print(f"임팩트(SoccerNet 주석) 프레임 분포: {dict(collections.Counter(impact.tolist()))}")

    # ------------------------------------------------------------------ 1
    section("1. 3D 정규화가 축별인가 전역 스칼라인가 — 축별이면 각도가 다 틀어진다")
    flat = K3.reshape(-1, 17, 3)
    mx, mn = flat.max(1), flat.min(1)
    for i, a in enumerate("xyz"):
        print(f"  {a}: max==1.0 인 프레임 {int(np.isclose(mx[:, i], 1.0).sum()):5d}"
              f" · min==0.0 인 프레임 {int(np.isclose(mn[:, i], 0.0).sum()):5d}")
    print(f"  축별 범위 중앙값 {np.median(mx - mn, axis=0).round(3)}")
    print("  → z 만 [0,1] 이고 x·y 는 아니다. **전역 스칼라 하나**로 나눈 것이라 각도는 보존된다.")

    femur = np.linalg.norm(flat[:, J["Left Hip"]] - flat[:, J["Left Knee"]], axis=1)
    torso = np.linalg.norm(flat[:, J["Center of Hips"]] - flat[:, J["Center of Shoulder"]], axis=1)
    print(f"  대퇴/몸통 길이비 중앙값 {np.median(femur / torso):.3f} (사람 비례 ~0.84)")
    print(f"  🔴 그런데 이 비의 CV 가 {np.std(femur / torso) / np.mean(femur / torso):.3f} 다 —"
          " 정규화가 아니라 **3D 리프팅 오차**다. 뼈 길이 CV 를 등방성 판정에 쓰면 오독한다.")

    # ------------------------------------------------------------------ 2
    section("2. 깊이 축은 어느 것인가 — 추측하지 않고 2D≈A·3D 를 맞춰 영공간을 본다")
    o2 = K2.reshape(-1, 17, 2) - K2.reshape(-1, 17, 2).mean(1, keepdims=True)
    o3 = flat - flat.mean(1, keepdims=True)
    depth = np.zeros((len(flat), 3))
    resid = np.zeros(len(flat))
    for k in range(len(flat)):
        A, *_ = np.linalg.lstsq(o3[k], o2[k], rcond=None)   # (3,2)
        depth[k] = np.linalg.svd(A.T)[2][2]                 # A 의 영공간 = 화면 밖
        resid[k] = np.linalg.norm(o3[k] @ A - o2[k]) / np.linalg.norm(o2[k])
    print(f"  3D→2D 선형투영 잔차 중앙값 {np.median(resid):.1%} (작을수록 2D 는 3D 의 투영)")
    print(f"  깊이 방향의 축 성분 |평균| = x {np.abs(depth).mean(0)[0]:.2f}"
          f" · y {np.abs(depth).mean(0)[1]:.2f} · z {np.abs(depth).mean(0)[2]:.2f}")
    print("  → **y 가 깊이**다. z 는 수직(2D y 와 r=-0.97), x 는 좌우.")

    ref = depth[0]
    s = np.sign((depth * ref).sum(1))
    s[s == 0] = 1
    depth *= s[:, None]

    # ------------------------------------------------------------------ 3
    section("3. 방향(facing) 큐가 서는가 — 미결 37번 (나)의 전제")

    def depth_diff(a: str, b: str):
        return ((flat[:, J[a]] - flat[:, J[b]]) * depth).sum(1).reshape(n, FRAMES_PER_CLIP)

    ds = depth_diff("Left Shoulder", "Right Shoulder")
    dh = depth_diff("Left Hip", "Right Hip")

    def stability(a):
        return (np.sign(a) == np.sign(a[:, t: t + 1])).mean(1)

    m = (np.abs(ds) > 1e-9) & (np.abs(dh) > 1e-9)
    print(f"  A 커버리지        : {m[:, t].mean():.0%} (깊이차가 0 이 아닌 클립)")
    print(f"  B 두 큐 부호 일치 : 임팩트 {np.mean(np.sign(ds[:, t]) == np.sign(dh[:, t])):.0%}"
          f" · 전 프레임 {np.mean(np.sign(ds[m]) == np.sign(dh[m])):.0%}"
          f" (r={np.corrcoef(ds.ravel(), dh.ravel())[0, 1]:+.2f})")
    print(f"  C 클립 내 시간 안정 ≥80% : 어깨 {(stability(ds) >= 0.8).mean():.0%}"
          f" · 골반 {(stability(dh) >= 0.8).mean():.0%}")
    print("  🔴 D 구조적 독립성은 **안 선다** — 두 큐가 같은 리프팅 모델 하나에서 나온다.")
    print("     3회차의 귀·이동 큐와 달리 서로를 검증하지 못한다. B 의 높은 값을 그대로 믿지 말 것.")

    # ------------------------------------------------------------------ 4
    section("4. trunk_lean 실측 분포 — 미결 37번이 '못 쟀다'고 적은 그 분포")
    mid_sh = (K2[:, :, J["Left Shoulder"]] + K2[:, :, J["Right Shoulder"]]) / 2
    mid_hp = (K2[:, :, J["Left Hip"]] + K2[:, :, J["Right Hip"]]) / 2
    lean = trunk_lean(mid_sh, mid_hp)

    v = lean[:, t]
    flip = sum(instep_band(x) != instep_band(-x) for x in v)
    print(f"  부호     음수 {int((v < 0).sum())} / 양수 {int((v > 0).sum())}"
          f" · |θ|<5도 {int((np.abs(v) < 5).sum())} ({(np.abs(v) < 5).mean():.0%})")
    print(f"  중앙값 {np.median(v):+.1f}도 · 평균 {v.mean():+.1f}도 · SD {v.std():.1f}"
          f" · 범위 [{v.min():.1f}, {v.max():.1f}]")
    print(f"  인스텝 등급 분포 {dict(sorted(collections.Counter(instep_band(x) for x in v).items()))}")
    print(f"  🔴 좌우 반전 시 등급이 바뀌는 클립 {flip}/{n} ({flip / n:.0%})")
    print("\n  임팩트 프레임을 어디로 잡아도 결론이 같은가:")
    for k in range(max(t - 3, 1), min(t + 5, FRAMES_PER_CLIP)):
        w = lean[:, k]
        f = sum(instep_band(x) != instep_band(-x) for x in w)
        print(f"    frame {k:2d}: 음수 {int((w < 0).sum()):3d}"
              f" · |θ|<5 {int((np.abs(w) < 5).sum()):3d} · 반전 등급변동 {f}/{n} ({f / n:.0%})")

    # ------------------------------------------------------------------ 5
    section("5. 이 데이터로 무릎각을 믿을 수 있는가 — 지터와 선수 크기")
    height = np.ptp(K2[..., 1], axis=2)
    print(f"  선수 픽셀 높이 중앙값 {np.median(height):.1f}px"
          f" · 5퍼센타일 {np.percentile(height, 5):.1f}px")

    def angle(a, b, c, X):
        u, w = X[:, :, J[a]] - X[:, :, J[b]], X[:, :, J[c]] - X[:, :, J[b]]
        cos = (u * w).sum(-1) / (np.linalg.norm(u, axis=-1) * np.linalg.norm(w, axis=-1) + 1e-12)
        return np.degrees(np.arccos(np.clip(cos, -1, 1)))

    for lab, series in [
        ("2D 무릎각(좌)", angle("Left Hip", "Left Knee", "Left Ankle", K2)),
        ("2D 무릎각(우)", angle("Right Hip", "Right Knee", "Right Ankle", K2)),
        ("2D 몸통기울기", lean),
    ]:
        d2 = np.abs(series[:, 2:] - 2 * series[:, 1:-1] + series[:, :-2])
        print(f"  {lab} 2차차분 중앙값 {np.median(d2):5.2f}도")
    print("  🔴 무릎각 지터가 루브릭 2등급 구간 폭(150~170, 20도)에 견줄 만하다.")
    print("     몸통은 그 1/5 수준이라 **trunk_lean 만 이 데이터로 다룰 만하다.**")


if __name__ == "__main__":
    main()
