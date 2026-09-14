"""종목 게이트가 진짜 축구를 오거절하는가 — 미결 `ho` 43번 ㉮ 2회차.

🔴 **사전 등록(`PREREGISTRATION.md`, 커밋 `cb00f2d`)을 먼저 읽는다.** 상수·
합격선·판별 규칙·예측은 이 파일을 쓰기 **전에** 굳었고 결과를 보고 고치지 않는다.

🔴 **게이트 규칙을 복제하지 않는다** — `sport_conflict` 와 `stack_object_tracks`
를 production 에서 **import** 한다. 문턱도 production 상수 그대로다.

🔴 **`src/` 를 한 줄도 안 고친다** — 조사 회차다. ViTPose 는 안 돌린다.

    cd agent && uv run python eval/pending43_sport_gate2/measure_gate2.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval" / "phaseA"))

from supersub_agent.scoring import load_rubric  # noqa: E402
from supersub_agent.pose import (  # noqa: E402
    COUNTER_EVIDENCE_TOOLS,
    DEFAULT_MAX_SECONDS,
    DEFAULT_TARGET_FPS,
    MIN_CONFIDENT_FRAMES,
    MIN_TOOL_CONFIDENCE,
    _load_detector,
    _tracked_centers,
    read_frames_ex,
    sport_conflict,
    stack_object_tracks,
)

import paths  # noqa: E402

HERE = Path(__file__).resolve().parent

# 🔴 사전 등록에서 박은 값. **결과를 보고 돌리지 않는다.**
MAX_FALSE_REJECT = 0.05
RACKET_DROP_MIN = 3
EXPECT_BASEBALL_REJECT = 27   # 1회차 실측 27/39 = 69%

# 🔴 **종목 키를 손으로 적지 않는다.** production 이 `rubric.sport` 를 넘기므로
#    루브릭에서 읽어 온다. 처음에 `"soccer"` 라고 박았다가 `KeyError` 로 죽었는데,
#    그 실수가 **진짜 함정 하나를 드러냈다** — `sport_conflict` 은
#    `COUNTER_EVIDENCE_TOOLS.get(sport, ())` 라 **모르는 키를 받으면 조용히
#    빈 튜플**을 돌려주고 **게이트가 통째로 무력화된다.** 경고도 예외도 없다.
#    (내 스크립트는 딕셔너리를 직접 찍다 죽어서 알았을 뿐이다.)
SPORT = load_rubric(ROOT / "rubrics" / "football_instep_shot.yaml").sport


def scan(clip: Path, det_pair, device: str) -> dict:
    """검출 한 번 → production 게이트. 🔴 **규칙을 복제하지 않는다.**"""
    import torch

    det_processor, detector = det_pair
    read = read_frames_ex(clip, DEFAULT_TARGET_FPS, None, DEFAULT_MAX_SECONDS)
    per_frame = []
    for frame in read.frames:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        inp = det_processor(images=rgb, return_tensors="pt").to(device)
        with torch.inference_mode():
            out = detector(**inp)
        det = det_processor.post_process_object_detection(
            out, target_sizes=[(rgb.shape[0], rgb.shape[1])], threshold=0.3
        )[0]
        per_frame.append(_tracked_centers(det))

    objects = stack_object_tracks(per_frame)          # production 문턱 그대로
    tool = sport_conflict(objects, SPORT)

    # 🔴 기준 B — 「거절됐다」만 세면 무엇을 배트로 봤는지 모른다.
    seen = {}
    for name in ("baseball_bat", "tennis_racket", "sports_ball"):
        conf = [f[name][2] for f in per_frame if name in f]
        if conf:
            seen[name] = {
                "frames": len(conf),
                "confident_frames": sum(c >= MIN_TOOL_CONFIDENCE for c in conf),
                "max_conf": round(max(conf), 3),
                "in_tracks": name in objects,
            }
    return {"clip": clip.name, "frames": len(read.frames),
            "conflict": tool, "tools": seen}


def run_layer(name: str, clips: list[Path], det_pair, device: str) -> list[dict]:
    print(f"\n{name} — {len(clips)}편")
    rows = []
    for i, clip in enumerate(clips, 1):
        t0 = time.time()
        try:
            r = scan(clip, det_pair, device)
        except Exception as exc:  # noqa: BLE001 — 한 편이 죽어도 회차는 돈다
            print(f"  [{i}/{len(clips)}] {clip.name[:38]:38s} ⚠️ {type(exc).__name__}")
            rows.append({"clip": clip.name, "error": repr(exc)})
            continue
        r["layer"] = name
        rows.append(r)
        mark = f"🔴 거절({r['conflict']})" if r["conflict"] else "통과"
        print(f"  [{i}/{len(clips)}] {clip.name[:38]:38s} {mark:18s} "
              f"({time.time()-t0:.1f}초)")
    return rows


def main() -> None:
    import torch

    soccer = sorted(paths.soccernet_clips_root().glob("*.mp4"))
    baseball = sorted((paths.require_external("clips/") / "clips").glob("*.mp4"))
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"게이트 근거 도구({SPORT}): {COUNTER_EVIDENCE_TOOLS[SPORT]}")
    print(f"문턱: 신뢰도 ≥{MIN_TOOL_CONFIDENCE} 가 {MIN_CONFIDENT_FRAMES}프레임 이상 "
          f"· device={device}")
    print("🔴 이 표본은 **방송**이지 실사용자(휴대폰) 영상이 아니다.")

    det_pair = _load_detector(device)
    rows = (run_layer("축구(음성 층)", soccer, det_pair, device)
            + run_layer("야구(재현 확인)", baseball, det_pair, device))
    (HERE / "gate2_raw.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

    soc = [r for r in rows if r.get("layer", "").startswith("축구") and "error" not in r]
    bas = [r for r in rows if r.get("layer", "").startswith("야구") and "error" not in r]
    soc_rej = [r for r in soc if r["conflict"]]
    bas_rej = [r for r in bas if r["conflict"]]
    by_tool = {t: [r for r in soc_rej if r["conflict"] == t]
               for t in COUNTER_EVIDENCE_TOOLS[SPORT]}
    FR = len(soc_rej) / len(soc) if soc else float("nan")

    print("\n" + "=" * 72)
    print(f"축구 {len(soc)}편 중 거절 **{len(soc_rej)}편 ({FR:.1%})** "
          f"— 🔴 전부 오거절이다")
    for t, rs in by_tool.items():
        print(f"    {t:15s} {len(rs)}편 " +
              (", ".join(r["clip"][:26] for r in rs) if rs else ""))
    print(f"야구 {len(bas)}편 중 거절 {len(bas_rej)}편 "
          f"({len(bas_rej)/len(bas):.0%})" if bas else "야구 층 없음")

    print("\n── 사전 등록 판정 A~F")
    a_ok = len(bas_rej) == EXPECT_BASEBALL_REJECT
    print(f"  A 재현 — 야구 거절 {EXPECT_BASEBALL_REJECT}/39 : "
          f"{len(bas_rej)}/{len(bas)} {'✅' if a_ok else '🔴 재현 안 됨'}")
    print(f"  B 계기 — 거절 클립의 도구 근거 기록 : "
          f"{'✅ gate2_raw.json' if soc_rej else '거절 0편이라 기록할 것이 없다'}")
    print("  C src/·rubrics/ 무변경             : ✅ (production 을 import 만 한다)")
    print(f"  D 분모 — 축구 {len(soc)}/{len(soccer)} · 야구 {len(bas)}/{len(baseball)}")
    print("  E pytest                           : 별도로 돌린다")

    print("\n── 판별 ⑴ 게이트가 축구에서 안전한가")
    if FR <= MAX_FALSE_REJECT:
        print(f"  ✅ **안전하다** — 오거절 {FR:.1%} ≤ {MAX_FALSE_REJECT:.0%}")
    else:
        print(f"  🔴 **안전하지 않다** — 오거절 {FR:.1%} > {MAX_FALSE_REJECT:.0%}. "
              "게이트를 손봐야 한다")

    print("\n── 판별 ⑵ tennis_racket 을 뺄 것인가")
    nr = len(by_tool.get("tennis_racket", []))
    if nr >= RACKET_DROP_MIN:
        print(f"  🔴 **뺀다** — 축구에서 {nr}편 발화 (≥{RACKET_DROP_MIN}). "
              "대가는 야구에서 라켓만 잡아낸 1편이다")
    elif nr <= 1:
        print(f"  ✅ **안 뺀다** — 축구에서 {nr}편 발화 (≤1). "
              "대가(야구 1편)와 비슷하거나 작다")
    else:
        print(f"  **유지(기본값)** — {nr}편. 애매하면 production 규칙을 안 바꾼다")
    print("  🔴 이 판정은 「뺀다」까지다. 빼는 것은 3회차(처방)다.")

    print(f"\n🔴 내 사전 예측: 오거절 0~5편. 다르면 **틀렸다고 적는다.**")

    # ── 사후 관찰 (판정에 안 쓴다) ────────────────────────────────────
    print("\n── 사후 관찰 (판정에 안 쓴다)")
    for t in ("baseball_bat", "tennis_racket"):
        hit = [r for r in soc if t in r["tools"]]
        conf = [r["tools"][t]["max_conf"] for r in hit]
        gated = [r for r in hit if r["tools"][t]["in_tracks"]]
        print(f"  축구에서 {t} 가 **한 프레임이라도** 잡힌 클립: {len(hit)}/{len(soc)}"
              + (f" · 최고신뢰도 중앙 {np.median(conf):.2f}" if conf else "")
              + f" · 문턱 통과 {len(gated)}편")
    ball = [r for r in soc if r["tools"].get("sports_ball", {}).get("in_tracks")]
    print(f"  축구에서 공 궤적이 남은 클립: {len(ball)}/{len(soc)} "
          f"({len(ball)/len(soc):.0%})" if soc else "")


if __name__ == "__main__":
    main()
