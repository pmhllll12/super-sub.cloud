"""E-1 / E-2 를 **offline으로만** 계산하기 위한 정의. production에 넣지 않는다.

╔══════════════════════════════════════════════════════════════════════════╗
║ 이 파일은 수정안이 아니다. 영향 산정을 위한 **모형**이다.                  ║
║ features.py의 segment_phases를 컨텍스트 매니저 안에서만 갈아 끼운다.      ║
╚══════════════════════════════════════════════════════════════════════════╝

무엇이 다른가 — 두 축을 직교시킨다 (step2의 2×2 분해와 같은 축이다).

| 방식      | argmax 후보 격자        | 미분 스텐실의 **물리** 반폭 |
|-----------|-------------------------|------------------------------|
| base      | 데시메이션 격자 0,k,2k… | ±k/60초  (fps에 딸려 간다)   |
| E-1       | 데시메이션 격자         | **±τ초 (고정)**              |
| E-2       | **60Hz 공통 격자**      | ±k/60초                      |
| E-1+E-2   | **60Hz 공통 격자**      | **±τ초 (고정)**              |

E-1의 반폭은 프레임 단위로 `max(1, round(τ × fps))`다. **1 아래로 내려갈 수 없다**
— 저 fps에서 τ가 한 프레임 간격보다 짧으면 바닥을 친다(step8이 그 비율을 센다).

E-2의 임팩트는 60Hz 격자 위에 있어 데시메이션 배열의 정수 인덱스가 아닐 수 있다.
지표는 존재하는 프레임에서만 읽히므로 `round(p/k)`로 되돌려 붙인다 — **E-2의
분해능 이득은 지표 단계에서 잘린다.** 이 손실을 step8이 따로 보고한다.
"""
from __future__ import annotations

import contextlib

import numpy as np

from supersub_agent import features as F

SOURCE_FPS = 60.0
# τ = 1/60초는 h = max(1, round((1/60)·(60/k))) = max(1, round(1/k)) = 1 이라
# 모든 fps에서 base와 **정확히 같다**. 확인용으로 함께 돌린다.
TAUS = {"1/60초": 1.0 / 60.0, "1/30초": 1.0 / 30.0, "1/12초": 1.0 / 12.0}
METHODS = ("base", "E1", "E2", "E1E2")


def wide_central(s: np.ndarray, h: int) -> np.ndarray:
    """반폭 h의 중심차분. h=1이면 np.gradient와 정확히 같다 (경계 처리 포함)."""
    n = len(s)
    idx = np.arange(n)
    lo = np.clip(idx - h, 0, n - 1)
    hi = np.clip(idx + h, 0, n - 1)
    return (s[hi] - s[lo]) / np.maximum(hi - lo, 1)


def e1_halfwidth(k: int, tau: float) -> tuple[int, bool]:
    """데시메이션 배수 k에서 E-1의 프레임 반폭과 바닥 여부."""
    raw = tau * (SOURCE_FPS / k)
    h = int(round(raw))
    return max(1, h), h < 1


def resample_60(s_k: np.ndarray, u_k: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    """데시메이션 계열을 60Hz 물리 격자로 선형 보간한다.

    **usable 구간 밖으로는 보간하지 않는다** — 양 끝 표본이 모두 usable인 구간
    안에서만 값을 만든다. 미결 5번이 확인한 "결측이 정답 창에 몰린다"와 충돌하지
    않기 위한 조건이다.
    """
    n = len(s_k)
    T = k * (n - 1) + 1
    p = np.arange(T)
    i = np.minimum(p // k, n - 1)
    j = np.minimum(i + 1, n - 1)
    frac = (p - i * k) / k
    # **표본 위에 정확히 놓인 격자점은 오른쪽 이웃을 요구하지 않는다.** 요구하면
    # k=1(항등 리샘플)에서도 마스크가 좁아져 E-2가 격자와 무관한 손해를 본다.
    exact = frac == 0.0
    fin_i, fin_j = np.isfinite(s_k[i]), np.isfinite(s_k[j])
    ok = np.where(exact, u_k[i] & fin_i, u_k[i] & u_k[j] & fin_i & fin_j)
    out = np.where(exact, s_k[i], s_k[i] * (1.0 - frac) + s_k[j] * frac)
    return out, ok


def impact_of(
    kps: np.ndarray, swing, limb: str, k: int, method: str, tau: float
) -> tuple[int, float, dict]:
    """(데시메이션 인덱스로 스냅한 임팩트, 물리 프레임 임팩트, 진단) 을 돌려준다.

    kps는 **이미 데시메이션된** 정규화 키포인트다.
    """
    series = F.chain_series(kps, swing)
    usable = F.valid_frames(kps, limb, swing) & np.isfinite(series)
    diag: dict = {}

    if method in ("base", "E1"):
        if method == "base":
            h = 1
        else:
            h, diag["floored"] = e1_halfwidth(k, tau)
        diag["halfwidth_frames"] = h
        diag["halfwidth_sec"] = h * k / SOURCE_FPS
        t = F._peak_frame(wide_central(series, h), usable)
        return t, float(t * k), diag

    s60, u60 = resample_60(series, usable, k)
    h60 = k if method == "E2" else max(1, int(round(tau * SOURCE_FPS)))
    diag["halfwidth_frames"] = h60
    diag["halfwidth_sec"] = h60 / SOURCE_FPS
    p = F._peak_frame(wide_central(s60, h60), u60)
    diag["phys_exact"] = p
    snapped = int(round(p / k))
    snapped = min(max(snapped, 0), len(series) - 1)
    diag["snap_loss_frames"] = abs(p - snapped * k)
    return snapped, float(p), diag


@contextlib.contextmanager
def patched_segment(k: int, method: str, tau: float):
    """extract_features가 쓰는 segment_phases를 잠시 갈아 끼운다.

    경계 규칙·first/last 계산은 production과 **글자 그대로 같게** 두고 임팩트
    선택만 바꾼다. 블록을 나가면 원본으로 되돌린다.
    """
    original = F.segment_phases

    def replacement(kps, swing, limb="leg", event="extension_peak"):
        if event != "extension_peak":
            return original(kps, swing, limb, event)
        if isinstance(swing, int):
            swing = F.LIMB_CHAINS["leg"]["left" if swing == F.L_KNEE else "right"]
        series = F.chain_series(kps, swing)
        usable = F.valid_frames(kps, limb, swing) & np.isfinite(series)
        impact, _phys, _diag = impact_of(kps, swing, limb, k, method, tau)
        first = int(np.argmax(usable))
        last = int(len(usable) - 1 - np.argmax(usable[::-1]))
        if impact - first < 2 or last - impact < 2:
            raise F.InsufficientQuality(
                f"임팩트 추정 프레임({impact})이 분석 가능 구간({first}~{last}) 경계에 있음. "
                "동작 전후가 잘린 영상으로 보인다."
            )
        return F.Phases(takeback=(first, impact), impact=impact,
                        follow_through=(impact, last))

    F.segment_phases = replacement
    try:
        yield
    finally:
        F.segment_phases = original
