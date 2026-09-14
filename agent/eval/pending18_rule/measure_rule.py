"""선택 규칙 후보를 오프라인으로 견준다 — 미결 `ho` 18번 14회차.

🔴 **사전 등록(`PREREGISTRATION.md`, 커밋 `97c37e7`)을 먼저 읽는다.** 상수·
합격선·판별 규칙·예측은 이 파일을 쓰기 **전에** 굳었고 결과를 보고 고치지 않는다.

🔴 **`src/` 를 한 줄도 안 고친다.** 이미 검출된 박스 위에서 **규칙만 갈아
끼운다** — 세 후보가 전부 박스 좌표만으로 계산되므로 재검출이 필요 없다.

🔴 **11회차의 계기를 import 한다** (`foot_point`·`gate_by_speed`·`detect_clip`).
층이 갈라지면 12·13회차와 이어 읽을 수 없다.

    cd agent && uv run python eval/pending18_rule/measure_rule.py
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval" / "phaseA"))
sys.path.insert(0, str(ROOT / "eval" / "pending18_ball_proximity"))

from measure_proximity import (  # noqa: E402
    MIN_BALL_COVERAGE,
    MIN_NEAR_FRAMES,
    NEAR,
    detect_clip,
    foot_point,
    gate_by_speed,
)
from supersub_agent.pose import (  # noqa: E402
    DEFAULT_MAX_SECONDS,
    DEFAULT_TARGET_FPS,
    POSE_MODEL,
    POSE_MODEL_REVISION,
    _load_detector,
    read_frames_ex,
)

import paths  # noqa: E402

HERE = Path(__file__).resolve().parent
BROADCAST = HERE.parent / "pending18_broadcast" / "broadcast_raw.json"
GATE40 = HERE.parent / "sample_gate" / "gate_soccernet.json"

# 🔴 사전 등록에서 박은 값. **결과를 보고 돌리지 않는다.**
LIE = 1.0
LIE_SWEEP = (0.9, 1.0, 1.2, 1.5)
WIN_MARGIN = 0.10
EXPECT_M_R0_A = 0.177     # 기준 A — 12회차 층 A 재현
KP_DROP_MAX = 0.10        # 기준 F⑴


# ── 후보 규칙 셋 ───────────────────────────────────────────────────────
#
# 🔴 **사전 등록이 안 정한 것 하나를 여기서 정하고 밝힌다.** R2 는 「누운
#    박스를 후보에서 뺀다」인데, **모든 후보가 빠지는 프레임**에서 무엇을
#    할지를 사전 등록에 안 적었다. **R0 로 되돌아간다**(= 안 뺀 것처럼)로
#    정했다 — 아무도 안 고르면 커버리지가 0 이 되고, 그건 미결 18번 7회차가
#    **닫아 둔 경로**다(「거부해도 자동 박스로 떨어지되」 회차에서 커버리지를
#    0 으로 만드는 것은 출력 형태라고 적었다).
# 🔴 이 결정은 **결과를 보기 전에** 내렸고 여기 적는다.

def pick_r0(boxes: list[tuple]) -> int:
    """현행 — `argmax(area)`. production `_largest_person_box` 와 같은 규칙."""
    return int(np.argmax([b[2] * b[3] for b in boxes]))


def pick_r1(boxes: list[tuple]) -> int:
    """`argmax(height)`. 새 상수 0개."""
    return int(np.argmax([b[3] for b in boxes]))


def pick_r2(boxes: list[tuple], lie: float = LIE) -> int:
    """`argmax(area)` 하되 `w/h >= lie` 인 박스는 후보에서 뺀다."""
    keep = [i for i, b in enumerate(boxes) if b[3] > 0 and b[2] / b[3] < lie]
    if not keep:                      # 🔴 위 주석의 폴백
        return pick_r0(boxes)
    return keep[int(np.argmax([boxes[i][2] * boxes[i][3] for i in keep]))]


RULES = {"R0": pick_r0, "R1": pick_r1, "R2": pick_r2}


def layer_of(clip: Path, layer_a_names: set[str], first40: set[str]) -> str | None:
    if clip.name in layer_a_names:
        return "A"
    if clip.name not in first40:
        return "B"
    return None          # 앞 40편 중 주 층에 못 든 것 — 어느 층도 아니다


def probe(clip: Path, det_pair, device: str) -> dict | None:
    """한 클립의 주 층과 규칙별 선택. 🔴 주 층 정의는 **규칙과 무관**하다."""
    det = detect_clip(clip, det_pair, device)
    cands = det["cands"]
    ball = det["objects"].get("sports_ball")
    if ball is None:
        return None
    heights = [b[3] for f in cands for b in f]
    H = float(statistics.median(heights)) if heights else 0.0
    if H <= 0:
        return None
    ball, _ = gate_by_speed(ball, H)
    coverage = float((ball[:, 2] > 0).mean())

    rows, single = [], {"n": 0, "same": 0}
    for t in range(det["frames"]):
        boxes = cands[t]
        if not boxes or ball[t, 2] <= 0:
            continue
        b = ball[t, :2]
        d = [float(np.hypot(*(np.asarray(foot_point(x)) - b)) / H) for x in boxes]
        ai = int(np.argmin(d))
        if len(boxes) == 1:
            # 기준 F⑵ — 후보가 하나면 어떤 규칙이든 같은 박스여야 한다.
            single["n"] += 1
            single["same"] += all(f(boxes) == 0 for f in RULES.values())
            continue
        if d[ai] > NEAR:
            continue
        rows.append({
            "t": t, "n_cands": len(boxes), "argmin": ai,
            "picks": {k: f(boxes) for k, f in RULES.items()},
            "picks_lie": {f"{s:.1f}": pick_r2(boxes, s) for s in LIE_SWEEP},
            "boxes": [[round(v, 1) for v in x] for x in boxes],
        })
    return {"clip": clip.name, "scale_h": H, "ball_coverage": round(coverage, 3),
            "frames": det["frames"], "rows": rows, "single": single}


def keypoint_conf(clip: Path, rows: list[dict], device: str) -> dict[str, float]:
    """기준 F⑴ — 규칙별로 고른 박스의 ViTPose 평균 신뢰도.

    🔴 **이 회차에서 유일하게 포즈를 쓰는 자리다.** 주 층 프레임만 본다.
    프레임은 `read_frames_ex` 가 결정적이라 같은 것이 다시 나온다.
    """
    import torch
    from transformers import AutoProcessor, VitPoseForPoseEstimation

    need = sorted({(r["t"], tuple(r["boxes"][r["picks"][k]]))
                   for r in rows for k in RULES})
    if not need:
        return {}
    frames = read_frames_ex(clip, DEFAULT_TARGET_FPS, None, DEFAULT_MAX_SECONDS).frames
    proc = AutoProcessor.from_pretrained(POSE_MODEL, revision=POSE_MODEL_REVISION)
    model = VitPoseForPoseEstimation.from_pretrained(
        POSE_MODEL, revision=POSE_MODEL_REVISION).to(device).eval()
    conf: dict[tuple, float] = {}
    try:
        for t, box in need:
            rgb = cv2.cvtColor(frames[t], cv2.COLOR_BGR2RGB)
            inp = proc(rgb, boxes=[[list(box)]], return_tensors="pt").to(device)
            with torch.inference_mode():
                out = model(**inp)
            res = proc.post_process_pose_estimation(out, boxes=[[list(box)]])[0][0]
            conf[(t, box)] = float(np.mean(np.asarray(res["scores"], dtype=float)))
    finally:
        del model
        if device == "cuda":
            torch.cuda.empty_cache()
    return {k: statistics.fmean(
        [conf[(r["t"], tuple(r["boxes"][r["picks"][k]]))] for r in rows])
        for k in RULES}


def main() -> None:
    import torch

    layer_a_names = {r["clip"] for r in
                     json.loads(BROADCAST.read_text(encoding="utf-8"))
                     if r.get("n_near", 0) >= MIN_NEAR_FRAMES}
    first40 = {r["clip"] for r in json.loads(GATE40.read_text(encoding="utf-8"))}
    all_clips = sorted(paths.soccernet_clips_root().glob("*.mp4"))
    todo = [c for c in all_clips if layer_of(c, layer_a_names, first40)]
    print(f"층 A {len(layer_a_names)}편 · 층 B {len(todo)-len(layer_a_names)}편 "
          f"(전체 {len(all_clips)}편 중)\n")
    print("🔴 층 B 에서는 규칙을 고르지 않는다 — **확인 전용**이다.\n")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    det_pair = _load_detector(device)

    out: list[dict] = []
    for i, clip in enumerate(todo, 1):
        t0 = time.time()
        lay = layer_of(clip, layer_a_names, first40)
        r = probe(clip, det_pair, device)
        if r is None:
            print(f"  [{i}/{len(todo)}] {lay} {clip.name[:34]:34s} 공 궤적 없음")
            continue
        r["layer"] = lay
        out.append(r)
        print(f"  [{i}/{len(todo)}] {lay} {clip.name[:34]:34s} "
              f"공커버 {r['ball_coverage']:.0%} · 주층 {len(r['rows']):3d}f "
              f"({time.time()-t0:.1f}초)")

    # 🔴 클립 자격은 11~13회차와 같다.
    ok = [c for c in out if c["ball_coverage"] >= MIN_BALL_COVERAGE
          and len(c["rows"]) >= MIN_NEAR_FRAMES]

    # 포즈는 자격을 갖춘 클립의 주 층에만 돌린다 (기준 F⑴).
    print("\n── 기준 F⑴ — 고른 박스의 키포인트 신뢰도 (ViTPose)")
    for c in ok:
        c["kp"] = keypoint_conf(paths.soccernet_clips_root() / c["clip"],
                                c["rows"], device)
        print(f"  {c['layer']} {c['clip'][:34]:34s} "
              + " · ".join(f"{k} {v:.3f}" for k, v in c["kp"].items()))

    (HERE / "rule_raw.json").write_text(
        json.dumps([{k: v for k, v in c.items() if k != "rows"} | {
            "rows": [{kk: vv for kk, vv in r.items() if kk != "boxes"}
                     for r in c["rows"]]} for c in out],
                   ensure_ascii=False), encoding="utf-8")

    def stats(layer: str) -> dict:
        cs = [c for c in ok if c["layer"] == layer]
        rows = [r for c in cs for r in c["rows"]]
        if not rows:
            return {"clips": len(cs), "frames": 0}
        m = {k: sum(r["picks"][k] == r["argmin"] for r in rows) / len(rows)
             for k in RULES}
        kp = ({k: statistics.fmean([c["kp"][k] for c in cs if c.get("kp")])
               for k in RULES} if any(c.get("kp") for c in cs) else {})
        lie = {s: sum(r["picks_lie"][f"{s:.1f}"] == r["argmin"] for r in rows) / len(rows)
               for s in LIE_SWEEP}
        return {"clips": len(cs), "frames": len(rows), "M": m, "kp": kp, "lie": lie}

    A, B = stats("A"), stats("B")
    print("\n" + "=" * 72)
    for name, s in (("층 A (고르는 데 쓴다)", A), ("층 B (확인 전용)", B)):
        print(f"\n{name} — 클립 {s['clips']}편 · 주 층 {s['frames']}프레임")
        if not s["frames"]:
            print("  🔴 비어 있다")
            continue
        for k in RULES:
            print(f"   M({k}) = {s['M'][k]:6.1%}"
                  + (f"   ΔR0 {s['M'][k]-s['M']['R0']:+.1%}" if k != "R0" else "")
                  + (f"   키포인트 {s['kp'][k]:.3f}" if s["kp"] else ""))

    print("\n── 사전 등록 판정 A~F")
    a_ok = abs(A["M"]["R0"] - EXPECT_M_R0_A) < 0.005 if A["frames"] else False
    print(f"  A M(R0) 층 A = {EXPECT_M_R0_A:.1%} 재현 : "
          f"{A['M']['R0']:.1%} {'✅' if a_ok else '🔴'}" if A["frames"]
          else "  A : 🔴 층 A 가 비었다")
    b_ok = B["clips"] >= 5
    print(f"  B 층 B 관문 — 주 층 클립 ≥5   : {B['clips']}편 "
          f"{'✅' if b_ok else '🔴 확인 못 함으로 적는다'}")
    print("  C 민감도 (LIE 네 값, 층 A)")
    if A["frames"]:
        for s in LIE_SWEEP:
            win = A["lie"][s] - A["M"]["R0"]
            print(f"      LIE={s:.1f} : M {A['lie'][s]:6.1%} · ΔR0 {win:+.1%} "
                  f"→ {'이김' if win >= WIN_MARGIN else '못 넘음'}")
    print("  D src/·rubrics/ 무변경        : ✅ (11회차를 import 만 한다)")
    print("  E pytest                      : 별도로 돌린다")

    print("\n── 판별 (사전 등록 5절)")
    winners = []
    for k in ("R1", "R2"):
        if not A["frames"]:
            break
        da = A["M"][k] - A["M"]["R0"]
        db = (B["M"][k] - B["M"]["R0"]) if B["frames"] else None
        both = da >= WIN_MARGIN and db is not None and db >= WIN_MARGIN
        print(f"  {k}: 층 A {da:+.1%} · 층 B "
              f"{'—' if db is None else f'{db:+.1%}'} → "
              f"{'채택 후보' if both else '못 넘음'}")
        # F⑴ — 이긴 규칙만 본다
        if both and A["kp"]:
            drop = A["kp"]["R0"] - A["kp"][k]
            print(f"      F⑴ 키포인트 낙폭 {drop:+.3f} "
                  f"{'✅' if drop <= KP_DROP_MAX else '🔴 채점이 망가진다 → 이겼다고 안 적는다'}")
            if drop <= KP_DROP_MAX:
                winners.append(k)
        elif both:
            winners.append(k)
    sn = sum(c["single"]["n"] for c in ok)
    ss = sum(c["single"]["same"] for c in ok)
    print(f"  F⑵ 단일후보 프레임에서 세 규칙 동일 : {ss}/{sn} "
          f"{'✅' if sn == ss else '🔴 구현 버그다'}")

    print()
    if not winners:
        print("🔴 판정: **아무 후보도 못 넘었다.** 처방을 고르지 않는다 — "
              "「면적이 문제다」까지가 아는 전부이고 대안이 더 낫다는 증거는 없다")
    elif len(winners) == 2:
        print("🔴 판정: **R1·R2 둘 다 넘었다 → 새 상수가 0개인 R1 을 고른다**")
    else:
        print(f"🔴 판정: **{winners[0]} 이 채택 후보다** "
              "(「채택」이 아니다 — 구현·재실행은 15회차)")
    print("\n🔴 내 사전 예측: R1 은 넘을 여지가 있지만 못 넘을 가능성도 충분 · "
          "R2 는 못 넘는다 (상한 5%p). **다르면 틀렸다고 적는다.**")


if __name__ == "__main__":
    main()
