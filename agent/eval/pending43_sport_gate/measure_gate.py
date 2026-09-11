"""도구 신호로 축구 아닌 영상을 거를 수 있는가 — 1회차 측정 (미결 `ho` 43번 ㉮).

🔴 **사전 등록(`PREREGISTRATION.md`)을 먼저 읽는다.** 규칙과 합격선은 이 파일을
쓰기 전에 굳혔고(커밋 `8969ce3`), 결과를 보고 고치지 않는다.

**production 을 import 만 한다.** 규칙(`_tracked_centers` · `stack_object_tracks`
· `TRACKED_LABELS` · 문턱 상수)을 여기 복제하지 않는다 — 복제하면 서비스가
바뀔 때 이 측정이 조용히 옛 규칙을 재게 된다.

포즈 단계만 건너뛴다. 도구 궤적은 **검출 결과만으로** 정해지므로 ViTPose 는
이 질문에 아무것도 보태지 않고, 58편 × 300프레임을 두 모델에 통과시킬 이유가
없다. 🔴 **검출기·전처리·문턱은 production 과 같은 것을 쓴다** — 그래야 여기서
나온 수가 서비스의 동작을 설명한다.

    cd agent && uv run python eval/pending43_sport_gate/measure_gate.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import cv2
import torch
from transformers import AutoProcessor, RTDetrForObjectDetection

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval" / "phaseA"))

from supersub_agent.pose import (  # noqa: E402
    PERSON_DETECTOR,
    PERSON_DETECTOR_REVISION,
    TRACKED_LABELS,
    _tracked_centers,
    read_frames_ex,
    stack_object_tracks,
)

import paths  # noqa: E402  — 기계별 경로는 여기 한 곳에서만 (미결 14번)

HERE = Path(__file__).resolve().parent

#: 거절 근거가 되는 도구. 🔴 `sports_ball` 은 **없다** — COCO 에서 축구공·
#: 농구공·야구공이 한 클래스라 종목을 못 가른다(사전 등록 「못 하는 것」).
COUNTER_EVIDENCE = ("baseball_bat", "tennis_racket")


def soccer_clips() -> list[Path]:
    """축구 층 — 기계별 경로는 `paths.py` 한 곳에서만 정한다 (미결 14번)."""
    return sorted(paths.soccer_clips_root().rglob("*.avi"))


def baseball_clips() -> list[Path]:
    """야구 층 — Kinetics `hitting baseball` 전수 39편."""
    return sorted((paths.external_root() / "clips").glob("*.mp4"))


def tools_in(video: Path, detector, processor, device: str) -> tuple[dict, int]:
    """이 영상에서 살아남은 도구 궤적 — production 규칙 그대로."""
    read = read_frames_ex(video)
    obj_frames = []
    for frame in read.frames:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        inputs = processor(images=rgb, return_tensors="pt").to(device)
        with torch.inference_mode():
            out = detector(**inputs)
        det = processor.post_process_object_detection(
            out, target_sizes=[(rgb.shape[0], rgb.shape[1])], threshold=0.3
        )[0]
        obj_frames.append(_tracked_centers(det))
    return stack_object_tracks(obj_frames), len(read.frames)


def main() -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"장치 {device} · 검출기 {PERSON_DETECTOR}@{PERSON_DETECTOR_REVISION[:8]}")
    print(f"🔴 거절 근거 도구: {COUNTER_EVIDENCE}  (sports_ball 은 쓰지 않는다)\n")

    processor = AutoProcessor.from_pretrained(
        PERSON_DETECTOR, revision=PERSON_DETECTOR_REVISION)
    detector = RTDetrForObjectDetection.from_pretrained(
        PERSON_DETECTOR, revision=PERSON_DETECTOR_REVISION).to(device).eval()

    layers = {"baseball(음성·거절 기대)": baseball_clips(),
              "soccer(양성·통과 기대)": soccer_clips()}
    rows = []
    for layer, clips in layers.items():
        print(f"── {layer}: {len(clips)}편")
        for i, clip in enumerate(clips, 1):
            t0 = time.time()
            try:
                tracks, n = tools_in(clip, detector, processor, device)
            except Exception as exc:  # noqa: BLE001 — 한 편이 죽어도 회차는 돈다
                print(f"  [{i}/{len(clips)}] {clip.name[:40]:40s} ⚠️ {type(exc).__name__}")
                rows.append({"layer": layer, "clip": clip.name, "error": repr(exc)})
                continue
            hit = [t for t in COUNTER_EVIDENCE if t in tracks]
            rows.append({
                "layer": layer,
                "clip": clip.name,
                "frames": n,
                # 🔴 「궤적이 남았는가」다 — 「화면에 있었는가」가 아니다
                #    (사전 등록 계기 검사 1).
                "tools": sorted(tracks),
                "ball": "sports_ball" in tracks,
                "rejected": bool(hit),
                "why": hit,
                "seconds": round(time.time() - t0, 1),
            })
            mark = "거절" if hit else "통과"
            print(f"  [{i}/{len(clips)}] {clip.name[:40]:40s} {mark}"
                  f"  도구={sorted(tracks) or '없음'}  ({rows[-1]['seconds']}초)")

    (HERE / "gate_raw.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n" + "=" * 66)
    for layer in layers:
        got = [r for r in rows if r["layer"] == layer and "error" not in r]
        if not got:
            continue
        rej = sum(r["rejected"] for r in got)
        ball = sum(r["ball"] for r in got)
        print(f"{layer}: {len(got)}편 · 거절 {rej} ({rej / len(got):.0%})"
              f" · 공 검출 {ball} ({ball / len(got):.0%})")

    base = [r for r in rows if r["layer"].startswith("baseball") and "error" not in r]
    soc = [r for r in rows if r["layer"].startswith("soccer") and "error" not in r]
    false_rej = [r for r in soc if r["rejected"]]
    print("\n── 사전 등록 판정")
    print(f"  A 축구 오거절 0건        : {len(false_rej)}건 "
          f"{'✅' if not false_rej else '🔴'}")
    if base:
        r = sum(x["rejected"] for x in base) / len(base)
        print(f"  B 야구 거절 ≥50%        : {r:.0%} {'✅' if r >= 0.5 else '🔴'}")
    print("  C 점수 비트 동일         : 별도 — 게이트는 features 를 안 건드린다")
    print(f"  D 오거절 사유            : {[ (r['clip'], r['why']) for r in false_rej ] or '해당 없음'}")


if __name__ == "__main__":
    main()
