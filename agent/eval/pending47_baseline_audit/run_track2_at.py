"""워크트리에 체크아웃된 커밋으로 **B-6 Track 2 만** 돌린다 (미결 `ho` 47번).

판정 기준은 [`PREREGISTRATION.md`](PREREGISTRATION.md) 에 **돌리기 전에** 굳혔다.

🔴 **이 스크립트는 아무것도 안 고친다.** 워크트리의 `selector_downstream.py` 를
**그 커밋 그대로** 불러 `track2()` 만 부른다 — 전체 실행(약 430초)에서 Track 1
(약 315초)을 뺀 것이고, 산출은 같아야 한다(기준 A 가 그것을 확인한다).

    uv run python eval/pending47_baseline_audit/run_track2_at.py \
        --worktree <워크트리> --out <csv>

🔴 **워크트리의 `agent/data` 는 심링크다**(`.gitignore` 라 체크아웃에 없다).
치울 때는 `git worktree remove` 로만 치운다 — 심링크를 지우다 원본을 날리지 않게.
"""
from __future__ import annotations

import argparse
import importlib.util
import inspect
import sys
import time
from pathlib import Path


def load_module(worktree: Path):
    """워크트리의 스크립트를 **그 커밋 그대로** 불러온다.

    그 스크립트가 top-level 에서 자기 위치 기준으로 `sys.path` 를 깔기 때문에
    (`AGENT/src` 를 0번에 넣는다) `supersub_agent`·`eval_b2`·`targets`·`paths`
    가 **전부 워크트리 쪽**으로 잡힌다. 🔴 그래서 이 파일은 그 전에
    `supersub_agent` 를 import 하지 않는다 — 먼저 불러 두면 모듈 캐시가 이겨서
    **본 저장소 코드로 재는 셈**이 된다.
    """
    path = worktree / "agent" / "eval" / "phaseA" / "eval_b6" / "selector_downstream.py"
    if not path.exists():
        raise SystemExit(f"없다: {path}")
    spec = importlib.util.spec_from_file_location("b6_at_commit", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["b6_at_commit"] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--worktree", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    wt = Path(args.worktree).resolve()
    assert "supersub_agent" not in sys.modules, "본 저장소 코드가 먼저 잡혔다"
    mod = load_module(wt)

    from transformers import AutoProcessor, RTDetrForObjectDetection, VitPoseForPoseEstimation
    import torch

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    # 🔴 리비전 상수는 `ef59faa`(2026-09-11) 에 생겼다. 그 앞 커밋에는 없으므로
    #    **그 커밋이 하던 대로** 리비전 없이 부른다 — 여기서 채워 넣으면 그
    #    커밋의 동작이 아니라 내가 만든 동작을 재게 된다.
    pose_kw = {"revision": mod.POSE_MODEL_REVISION} if hasattr(mod, "POSE_MODEL_REVISION") else {}
    det_kw = {"revision": mod.PERSON_DETECTOR_REVISION} if hasattr(mod, "PERSON_DETECTOR_REVISION") else {}

    t0 = time.time()
    pproc = AutoProcessor.from_pretrained(mod.POSE_MODEL, **pose_kw)
    pmodel = VitPoseForPoseEstimation.from_pretrained(mod.POSE_MODEL, **pose_kw).to(dev).eval()
    dproc = AutoProcessor.from_pretrained(mod.PERSON_DETECTOR, **det_kw)
    dmodel = RTDetrForObjectDetection.from_pretrained(mod.PERSON_DETECTOR, **det_kw).to(dev).eval()

    rubrics = mod.S.discover_rubrics(mod.AGENT / "rubrics")
    sig = inspect.signature(mod.track2)
    if len(sig.parameters) != 6:
        raise SystemExit(f"track2 서명이 다르다({sig}) — 이 커밋은 손으로 볼 것")

    rows = mod.track2(dproc, dmodel, pproc, pmodel, dev, rubrics)
    mod._write(Path(args.out), rows)
    print(f"{len(rows)}행 · {round(time.time() - t0, 1)}초 → {args.out}")


if __name__ == "__main__":
    main()
