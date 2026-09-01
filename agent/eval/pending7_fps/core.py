"""미결 7번(프레임레이트 의존성) 조사 공용 헬퍼.

╔══════════════════════════════════════════════════════════════════════════╗
║ 경고 — 이 모듈은 production 임계값을 **일시적으로** 바꾸는 도구를 제공한다. ║
║                                                                          ║
║ `external_pose_threshold()`는 features.LIMB_MIN_CONFIDENCE["arm"]을      ║
║ 0.6 → 0.5로 바꿨다가 되돌리는 컨텍스트 매니저다. **import만으로는 아무것도 ║
║ 바뀌지 않는다** — 반드시 with 블록 안에서만 효력이 있다.                   ║
║                                                                          ║
║ 이 값을 모듈 최상단에서 대입하면 안 된다. 같은 프로세스에서 이 모듈을      ║
║ import한 다른 코드(서비스·평가·테스트)가 조용히 0.5로 채점하게 된다.       ║
╚══════════════════════════════════════════════════════════════════════════╝

**왜 0.5인가** — 이 조사는 PitcherMotion(KAPAO 추출 포즈)을 입력으로 쓴다.
KAPAO는 이미 0.5에서 잘라 내고 미검출을 0으로 채운 **검열된 점수**를 준다
(신뢰도 255만 개 전수 조사에서 0과 0.5 사이 값이 하나도 없었다, 2026-08-26).
ViTPose의 연속 점수에 맞춰 실측한 0.6을 그대로 적용하면 근거 없이 통과율이
5.8%로 떨어진다. production 값 0.6은 ViTPose 경로에 대해 그대로 유지한다.

production code는 import만 하고 파일은 건드리지 않는다.
"""
from __future__ import annotations

import contextlib
import importlib.util
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
AGENT = HERE.parent.parent                       # agent/
PM_CSV = AGENT / "data" / "goldenset" / "pitchermotion" / "Pitcher_Motion_Data.csv"
WORK = AGENT / "data" / "pending7_fps"           # .gitignore 대상 — 산출물 전부 여기
CLIPS_NPZ = WORK / "pm_clips.npz"
RUBRIC_BASEBALL = AGENT / "rubrics" / "baseball_pitching.yaml"

# uv 환경이면 editable 설치라 그냥 import된다. 아니면 src를 상대경로로 얹는다.
if importlib.util.find_spec("supersub_agent") is None:  # pragma: no cover
    sys.path.insert(0, str(AGENT / "src"))

from supersub_agent import features as F  # noqa: E402

ARM_THRESHOLD_FOR_EXTERNAL_POSE = 0.5

FACTORS = (1, 2, 3, 4, 5)          # 60 / 30 / 20 / 15 / 12 fps
FPS_OF = {1: 60, 2: 30, 3: 20, 4: 15, 5: 12}
SOURCE_FPS = 60.0                  # PitcherMotion 원본


@contextlib.contextmanager
def external_pose_threshold(value: float = ARM_THRESHOLD_FOR_EXTERNAL_POSE):
    """arm 신뢰도 임계값을 외부 포즈용으로 잠시 낮춘다. 블록을 나가면 되돌린다.

    파일(`features.py`)은 바뀌지 않는다. 되돌리기는 예외가 나도 보장된다.
    """
    original = F.LIMB_MIN_CONFIDENCE["arm"]
    F.LIMB_MIN_CONFIDENCE["arm"] = value
    try:
        yield value
    finally:
        F.LIMB_MIN_CONFIDENCE["arm"] = original


def load_clips(path: Path | str | None = None) -> dict[str, np.ndarray]:
    p = Path(path) if path is not None else CLIPS_NPZ
    if not p.exists():
        raise SystemExit(f"클립 캐시가 없다: {p}\n  먼저 `python load_pm.py` 를 실행할 것.")
    z = np.load(p)
    return {k: z[k] for k in z.files}


def side_of(chain) -> str:
    return "left" if chain[0] in (F.L_SHOULDER, F.L_HIP) else "right"


def run_one(kp: np.ndarray, k: int, side: str = "auto") -> dict:
    """한 클립을 k배 데시메이션해 파이프라인을 태운다.

    반환에는 물리 프레임(60fps 인덱스)으로 환산한 임팩트를 함께 담는다.
    호출자가 external_pose_threshold() 안에 있어야 한다.
    """
    sub = kp[::k]
    out: dict = {"k": k, "n": len(sub)}
    try:
        norm = F.normalize(sub)
        swing, _support = F.identify_limb(norm, "arm", side)
        out["swing"] = side_of(swing)
        F.check_quality(sub, limb="arm", side=side)
        phases = F.segment_phases(norm, swing, "arm", "extension_peak")
        t = phases.impact
        out["impact_sub"] = t
        out["impact_phys"] = t * k
        series = F.chain_series(norm, swing)
        out["elbow"] = float(series[t])
        out["elbow_usable"] = bool(
            F.valid_frames(norm, "arm", swing)[t] and np.isfinite(series[t])
        )
        out["ok"] = True
    except F.InsufficientQuality as e:
        out["ok"] = False
        out["err"] = f"InsufficientQuality: {e}"
    except Exception as e:                       # noqa: BLE001 — 원인 분류용
        out["ok"] = False
        out["err"] = f"{type(e).__name__}: {e}"
    return out


def run_features(kp: np.ndarray, k: int, side: str = "auto") -> dict | None:
    try:
        return F.extract_features(
            kp[::k], objects=None, impact_limb="arm",
            impact_event="extension_peak", swing_side=side,
        )
    except Exception:                            # noqa: BLE001
        return None
