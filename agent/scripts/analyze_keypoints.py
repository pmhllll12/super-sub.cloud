#!/usr/bin/env python3
"""**영상 없이** 관절 시계열만으로 지표를 낸다.

    uv run python scripts/analyze_keypoints.py \
        --root /mnt/d/sports_dataset/_jhmdb/joint_positions \
        --action kick_ball --rubric rubrics/football_instep_shot.yaml

## 왜 이게 되는가

`extract_features` 가 받는 것은 **영상이 아니라 `(T, 17, 3)` 배열**이다. 영상은
그 배열을 만들려고 있을 뿐이고(RT-DETR → ViTPose), 배열을 이미 들고 있으면
그 단계가 통째로 필요 없다 — **GPU 도 필요 없다.**

`features.py` 가 실제로 읽는 관절은 **12개**다.

    좌우 × (어깨 · 팔꿈치 · 손목 · 엉덩이 · 무릎 · 발목)

`NOSE=0` 은 상수만 있고 쓰이지 않으며, 눈·귀(COCO 1~4)는 아예 안 쓴다.
그래서 12개를 담은 관절 데이터면 어떤 것이든 이 경로로 들어온다.

## JHMDB — 사람이 붙인 15관절, 928클립, 14MB, CC BY 4.0

우리 세 종목이 다 있다: `kick_ball`(축구 36) · `shoot_ball`(농구 40) ·
`swing_baseball`(야구 타격 54). 그 밖에 `golf` 42 · `throw` 46.

관절 순서는 **기하로 확인했다**(928클립 중 200건의 관절별 중앙 y):
face(2)가 가장 위, 그 아래 neck(0) → 어깨(3,4) → 팔(7,8,11,12) → belly(1) →
엉덩이(5,6) → 무릎(9,10) → 발목(13,14). 좌우쌍이 서로 인접하고 y가 거의 같다.

## 🔴 이 경로가 **못 하는 것** 세 가지

**(1) 품질 게이트가 헛돈다.** JHMDB 는 가림 여부를 안 준다 — 가려져도 좌표를
채워 넣는다. 신뢰도 열이 없으므로 여기서 **1.0으로 채운다.** 그러면
`LIMB_MIN_CONFIDENCE` 게이트가 **한 번도 걸리지 않는다.** 영상 경로에서 나온
`features_ok` 와 **같은 뜻이 아니다** — 그 값과 나란히 놓지 말 것.

**(2) 시간을 못 낸다.** 원본 fps 가 주석에 없다. 그래서 `timebase.known=false`
이고 초를 붙이지 않는다 — 모르는 격자에서 시간을 지어내지 않는다(미결 7번 E-3).
`impact_frame` 은 프레임 번호로만 나간다.

**(3) 도구(공) 궤적이 없다.** `plant_foot_to_ball_offset` 처럼 공이 필요한
지표는 산출되지 않는다. 그 지표를 쓰는 항목은 판정에서 빠진다.

## 🔴 좌우 배정은 발표된 순서를 그대로 믿는다

y 좌표로는 좌우를 못 가른다. 다만 우리 지표는 **좌우 전역 교환에 대칭**이라
숫자가 달라지지 않는다 — `identify_limb` 은 이동량이 큰 쪽을 고르고,
몸통 기울기는 좌우 평균이며, 골반 회전은 축 기준(mod 180)이다. 바뀌는 것은
"어느 쪽인가"라는 **표기**뿐이다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.features import (  # noqa: E402
    InsufficientQuality,
    extract_features,
    verify_rubric_coverage,
)
from supersub_agent.scoring import load_rubric  # noqa: E402

# JHMDB 15관절 → COCO-17 인덱스. 위 docstring 의 기하 확인이 근거다.
# 값이 None 인 COCO 자리는 신뢰도 0으로 남는다 — features.py 가 안 읽는 자리다.
JHMDB_TO_COCO = {
    3: 6,    # R_shoulder → COCO R_SHOULDER
    4: 5,    # L_shoulder → COCO L_SHOULDER
    7: 8,    # R_elbow    → COCO R_ELBOW
    8: 7,    # L_elbow    → COCO L_ELBOW
    11: 10,  # R_wrist    → COCO R_WRIST
    12: 9,   # L_wrist    → COCO L_WRIST
    5: 12,   # R_hip      → COCO R_HIP
    6: 11,   # L_hip      → COCO L_HIP
    9: 14,   # R_knee     → COCO R_KNEE
    10: 13,  # L_knee     → COCO L_KNEE
    13: 16,  # R_ankle    → COCO R_ANKLE
    14: 15,  # L_ankle    → COCO L_ANKLE
}


def jhmdb_to_coco(pos_img: np.ndarray) -> np.ndarray:
    """`(2, 15, T)` → `(T, 17, 3)`.

    신뢰도는 옮긴 관절만 1.0 이고 나머지는 0.0 이다. 🔴 **1.0 은 "확실하다"가
    아니라 "가림 정보가 없다"는 뜻이다** — 위 docstring (1) 참고.
    """
    if pos_img.ndim != 3 or pos_img.shape[0] != 2 or pos_img.shape[1] != 15:
        raise ValueError(f"모양이 (2,15,T)가 아니다: {pos_img.shape}")
    T = pos_img.shape[2]
    out = np.zeros((T, 17, 3), dtype=np.float64)
    for src, dst in JHMDB_TO_COCO.items():
        out[:, dst, 0] = pos_img[0, src, :]
        out[:, dst, 1] = pos_img[1, src, :]
        out[:, dst, 2] = 1.0
    return out


def load_jhmdb(root: Path, action: str) -> list[tuple[str, np.ndarray]]:
    import scipy.io as sio

    folder = root / action
    if not folder.exists():
        raise SystemExit(f"동작 폴더가 없다: {folder}")
    clips = []
    for mat in sorted(folder.glob("*/joint_positions.mat")):
        try:
            kps = jhmdb_to_coco(sio.loadmat(mat)["pos_img"])
        except Exception as exc:  # noqa: BLE001 — 한 건이 전체를 막지 않는다
            print(f"  ✗ 못 읽음 {mat.parent.name}: {type(exc).__name__}: {exc}")
            continue
        clips.append((mat.parent.name, kps))
    return clips


def main() -> None:
    ap = argparse.ArgumentParser(description="관절 시계열만으로 지표를 낸다 (영상 불필요)")
    ap.add_argument("--root", type=Path, required=True,
                    help="JHMDB joint_positions 폴더")
    ap.add_argument("--action", required=True, help="kick_ball · shoot_ball · …")
    ap.add_argument("--rubric", required=True,
                    help="🔴 반드시 명시 — 기본값에 기대면 종목이 어긋나도 조용히 채점된다")
    ap.add_argument("--side", default="auto", choices=("auto", "left", "right"))
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    rubric = load_rubric(Path(args.rubric))
    clips = load_jhmdb(args.root, args.action)
    if args.limit:
        clips = clips[: args.limit]
    print(f"{args.action}: {len(clips)}클립 · 루브릭 {rubric.sport}/{rubric.motion}")

    records, ok = [], 0
    for name, kps in clips:
        try:
            feats = extract_features(
                kps, None, rubric.impact_limb, rubric.impact_event, args.side
            )
            verify_rubric_coverage(rubric, feats)
            records.append({"clip": name, "frames": int(len(kps)), "features": feats})
            ok += 1
        except InsufficientQuality as exc:
            records.append({"clip": name, "skipped": f"입력 품질 미달: {exc}"})
        except Exception as exc:  # noqa: BLE001
            records.append({"clip": name, "error": f"{type(exc).__name__}: {exc}"})

    out = args.out or (args.root.parent / f"features_{args.action}.json")
    out.write_text(json.dumps({
        "source": "JHMDB joint_positions (CC BY 4.0) — 사람이 붙인 15관절",
        "action": args.action,
        "rubric": args.rubric,
        "swing_side": args.side,
        # 🔴 이 경로의 한계를 결과에 박아 둔다. 인용할 사람이 함께 보게.
        "caveat": [
            "가림 정보가 없어 신뢰도를 1.0으로 채웠다 — 품질 게이트가 걸리지 않는다."
            " 영상 경로의 features_ok 와 같은 뜻이 아니다",
            "원본 fps 가 없어 프레임을 초로 환산하지 않는다 (미결 7번 E-3)",
            "공 궤적이 없어 도구 의존 지표는 산출되지 않는다",
            "정답은 관절이지 자세 등급이 아니다 — 정확도가 아니라 측정이다",
        ],
        "counted": {"clips": len(clips), "ok": ok},
        "records": records,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  성공 {ok}/{len(clips)} → {out}")


if __name__ == "__main__":
    main()
