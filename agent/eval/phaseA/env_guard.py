"""기준선을 낸 **환경**과 지금 환경이 갈렸으면 **돌기 전에 멈춘다** (미결 47번).

47번은 이렇게 났다 — `uv sync` 가 extra 없이 한 번 돌아 `torchvision` 이
조용히 빠졌고, transformers 5.x 가 **그것이 있느냐로 이미지 전처리기를 다르게
고르는** 바람에 같은 코드·같은 입력이 다른 포즈를 냈다. 알아채는 데 **다섯
회차**가 걸렸고, 그동안 나온 숫자가 무엇 위에서 산출된 것인지 사후에 가려야
했다.

5회차가 계기를 심어 **그때의 환경을 적기는** 한다(`run_meta.json` 의 `env`·
`packages`). 🔴 **그런데 적는 것은 사고를 막지 못한다** — 틀린 환경에서도
그대로 돌아가 숫자를 내놓고, 그 숫자는 다른 숫자와 **생김새가 같다.** 그래서
이 모듈은 적는 대신 **막는다.**

    from env_guard import preflight
    preflight("B-6 Track 2")        # 어긋나면 SystemExit

일부러 다른 환경에서 재고 싶으면(비교 회차) 막지 않는다 — 다만 **말로 밝혀야**
한다:

    SUPERSUB_ALLOW_ENV_DRIFT=1 uv run python ... # 경고만 찍고 진행

🔴 **이 파일은 「무엇이 맞는가」를 정하지 않는다.** 평가와 제품이 어느 전처리
경로로 통일할지는 미결 49번에서 정한다. 여기 적힌 것은 **기준선이 실제로 어느
환경에서 나왔는가**라는 사실뿐이다.
"""
from __future__ import annotations

import os
import sys

#: 되돌릴 수 없는 사실 — B-2~B-6 자산은 **`torchvision` 이 있는** 환경에서
#: 산출됐다. 근거: 미결 47번 5회차(`eval/pending47_baseline_audit/RESULTS_5.md`)
#: — 되살려 돌린 Track 2 가 2026-09-08 기준선과 **95행 × 40열 불일치 0**,
#: 빼고 돌린 것은 **85행 불일치**(네 번 재현).
BASELINE_ENV = {"transformers_sees_torchvision": True}

DRIFT_ENV_VAR = "SUPERSUB_ALLOW_ENV_DRIFT"


def current_env() -> dict:
    """기준선과 맞춰 볼 값만 읽는다 — 무겁지 않아야 preflight 로 쓸 수 있다."""
    from transformers.utils.import_utils import is_torchvision_available

    return {"transformers_sees_torchvision": is_torchvision_available()}


def drifted(baseline: dict, current: dict) -> list[str]:
    """어긋난 항목을 사람이 읽을 문장으로 돌려준다. 같으면 빈 목록."""
    out = []
    for key, want in baseline.items():
        got = current.get(key)
        if got != want:
            out.append(f"{key}: 기준선 {want!r} · 지금 {got!r}")
    return out


def explain(mismatches: list[str], what: str) -> str:
    lines = [
        f"🔴 {what} 을(를) **기준선과 다른 환경**에서 돌리려 하고 있습니다.",
        "",
        *(f"  - {m}" for m in mismatches),
        "",
        "이대로 돌리면 숫자는 나오지만 **기준선과 비교할 수 없습니다** —",
        "미결 47번이 정확히 이 형태였고, 알아채는 데 다섯 회차가 걸렸습니다.",
        "",
        "고치기: `uv sync --all-extras` (빠진 것은 대개 `tracking` extra 가",
        "끌고 오던 `torchvision` 입니다. `pyproject.toml` 에 직접 적혀 있지",
        "않아 눈에 안 띕니다.)",
        "",
        f"일부러 다른 환경에서 재는 회차라면: {DRIFT_ENV_VAR}=1 을 붙이십시오.",
    ]
    return "\n".join(lines)


def preflight(what: str = "이 평가", *, baseline: dict | None = None) -> list[str]:
    """어긋나면 멈춘다. 어긋난 목록을 돌려준다(맞으면 빈 목록)."""
    mismatches = drifted(baseline or BASELINE_ENV, current_env())
    if not mismatches:
        return []
    message = explain(mismatches, what)
    if os.environ.get(DRIFT_ENV_VAR):
        print(message, file=sys.stderr)
        print(f"\n[{DRIFT_ENV_VAR}] 밝히고 진행합니다.\n", file=sys.stderr)
        return mismatches
    raise SystemExit(message)
