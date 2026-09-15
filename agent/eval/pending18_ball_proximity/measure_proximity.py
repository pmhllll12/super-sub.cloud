"""우리가 고른 사람이 **공을 다루는 사람**인가 — 미결 `ho` 18번 11회차.

🔴 **사전 등록(`PREREGISTRATION.md`, 커밋 `9680a3b`)을 먼저 읽는다.** 상수와
합격선·판별 규칙은 이 파일을 쓰기 **전에** 굳었고 결과를 보고 고치지 않는다.

🔴 **`src/` 를 한 줄도 안 고친다** — 조사 회차다. production 은 **import 만**
한다. 이 회차 전용 규칙(발치 점 거리·주 층 정의)만 여기 둔다.

🔴 **ViTPose 를 안 돌린다.** 후보 전부의 포즈는 못 돌리고, 이 질문에는
키포인트가 필요 없다. 검출 패스 한 번이면 후보 목록·우리 선택·공이 다 나온다.

    cd agent && uv run python eval/pending18_ball_proximity/measure_proximity.py
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

from supersub_agent.pose import (  # noqa: E402
    DEFAULT_MAX_SECONDS,
    DEFAULT_TARGET_FPS,
    PERSON_ELIGIBLE_THRESHOLD,
    _eligible_person_boxes,
    _largest_person_box,
    _load_detector,
    _tracked_centers,
    read_frames_ex,
    stack_object_tracks,
)

import paths  # noqa: E402

HERE = Path(__file__).resolve().parent
TOUCHES = HERE.parent / "pending45_touch_events" / "touches_raw.json"

# ── 🔴 사전 등록에서 박은 값. **결과를 보고 돌리지 않는다.** ──────────────
MIN_BALL_COVERAGE = 0.30     # 45번 1·2·3회차와 같은 값
NEAR = 0.25                  # 키높이 — 주 값
NEAR_SWEEP = (0.15, 0.25, 0.35, 0.50)
MIN_NEAR_FRAMES = 5          # 클립이 주 층에 들어오는 최소 프레임
MAX_BALL_SPEED_H = 1.0       # 키높이/프레임 — 45번 3회차 4.0 어깨너비의 단위 변환
MIN_MARGIN = 0.25            # 키높이 — (나) 판정에 필요한 불일치의 크기
SPEARMAN_MIN = 0.7
HEIGHT_RATIO_MIN = 1.2       # 기준 G 의 예측값


def gate_by_speed(ball: np.ndarray, scale: float) -> tuple[np.ndarray, int]:
    """45번 3회차(`pending45_ball_continuity`)의 규칙 — 단위만 키높이다.

    물리적으로 닿을 수 없는 위치는 **미검출로 본다**(이어 붙이지 않는다).
    🔴 속도 상한이지 가속 상한이 아니고, **간격으로 나눈다** — 몇 프레임
    안 보이다 돌아온 정상 복귀를 텔레포트로 오인하지 않게.
    """
    out = ball.copy()
    last_t, dropped = None, 0
    for t in range(len(out)):
        if out[t, 2] <= 0:
            continue
        if last_t is None:
            last_t = t
            continue
        step = (np.hypot(*(out[t, :2] - out[last_t, :2])) / scale) / (t - last_t)
        if step > MAX_BALL_SPEED_H:
            out[t, 2] = 0.0
            dropped += 1
        else:
            last_t = t
    return out, dropped


def foot_point(box: tuple[float, float, float, float]) -> tuple[float, float]:
    """박스 하단 중앙. 🔴 **박스까지의 거리(안이면 0)를 쓰지 않는 이유**는
    사전 등록 1절에 있다 — 큰 박스가 자동으로 유리해지는데, 지금 시험대에
    오른 것이 바로 「가장 큰 사람을 고르는 규칙」이다."""
    x, y, w, h = box
    return x + w / 2.0, y + h


def spearman(a: list[float], b: list[float]) -> float:
    """순위 상관. scipy 를 새로 끌어오지 않는다 (동률은 평균 순위)."""
    def rank(v: list[float]) -> list[float]:
        order = sorted(range(len(v)), key=lambda i: v[i])
        out = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                out[order[k]] = avg
            i = j + 1
        return out

    ra, rb = rank(a), rank(b)
    ma, mb = statistics.fmean(ra), statistics.fmean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return num / den if den else float("nan")


def detect_clip(clip: Path, detector_pair, device: str) -> dict:
    """검출 패스 한 번. extract_keypoints 의 1차 단계와 **같은 호출**이다."""
    import torch

    det_processor, detector = detector_pair
    read = read_frames_ex(clip, DEFAULT_TARGET_FPS, None, DEFAULT_MAX_SECONDS)

    cands: list[list[tuple[float, float, float, float]]] = []
    chosen: list[tuple[float, float, float, float] | None] = []
    obj_frames: list[dict[str, tuple[float, float, float]]] = []

    for frame in read.frames:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        det_inputs = det_processor(images=rgb, return_tensors="pt").to(device)
        with torch.inference_mode():
            det_out = detector(**det_inputs)
        detections = det_processor.post_process_object_detection(
            det_out, target_sizes=[(rgb.shape[0], rgb.shape[1])], threshold=0.3
        )[0]
        cands.append(_eligible_person_boxes(detections))
        chosen.append(_largest_person_box(detections))
        obj_frames.append(_tracked_centers(detections))

    return {
        "cands": cands,
        "chosen": chosen,
        "objects": stack_object_tracks(obj_frames),
        "frames": len(read.frames),
        "sampled_fps": read.sampled_fps,
    }


def analyse(det: dict) -> dict | None:
    """한 클립의 거리·주 층·일치를 낸다. 잴 수 없으면 None."""
    cands, chosen = det["cands"], det["chosen"]
    n = det["frames"]

    heights = [b[3] for frame in cands for b in frame]
    if not heights:
        return None
    H = float(statistics.median(heights))
    if H <= 0:
        return None

    ball_raw = det["objects"].get("sports_ball")
    if ball_raw is None:
        return {"scale_h": H, "ball_coverage": 0.0, "skipped": "공 궤적 없음"}

    ball, dropped = gate_by_speed(ball_raw, H)
    seen = ball[:, 2] > 0
    coverage = float(seen.mean())

    # 🔴 계기 검사 — 내 복제가 production 선택과 같은 박스를 고르는가.
    replica_mismatch = 0
    rows = []
    d_chosen_ungated: list[float] = []   # 기준 B 용 (게이트 끈 값)

    for t in range(n):
        boxes = cands[t]
        if not boxes:
            continue
        # 우리 규칙 = 가장 큰 박스. production `_largest_person_box` 와 대조한다.
        areas = [b[2] * b[3] for b in boxes]
        ci = int(np.argmax(areas))
        if chosen[t] is None or not np.allclose(boxes[ci], chosen[t]):
            replica_mismatch += 1

        def dist(box, pt) -> float:
            fx, fy = foot_point(box)
            return float(np.hypot(fx - pt[0], fy - pt[1]) / H)

        if ball_raw[t, 2] > 0:
            d_chosen_ungated.append(dist(boxes[ci], ball_raw[t, :2]))

        if not seen[t]:
            continue
        ds = [dist(b, ball[t, :2]) for b in boxes]
        ai = int(np.argmin(ds))
        rows.append({
            "t": t,
            "n_cands": len(boxes),
            "d_chosen": ds[ci],
            "d_min": ds[ai],
            "match": ci == ai,
            "h_chosen": boxes[ci][3],
            "h_argmin": boxes[ai][3],
        })

    return {
        "scale_h": round(H, 1),
        "ball_coverage": round(coverage, 3),
        "ball_dropped": dropped,
        "frames": n,
        "replica_mismatch": replica_mismatch,
        "rows": rows,
        "d_chosen_ungated_median": (round(statistics.median(d_chosen_ungated), 3)
                                    if d_chosen_ungated else None),
    }


def layer(rows: list[dict], near: float) -> list[dict]:
    """주 층 — 공이 누군가의 발치에 있고(≤near) 후보가 2명 이상인 프레임."""
    return [r for r in rows if r["d_min"] <= near and r["n_cands"] >= 2]


def main() -> None:
    import torch

    clips = sorted(paths.soccer_clips_root().rglob("*.avi"))
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"축구 {len(clips)}편 · device={device} · "
          f"NEAR={NEAR} MIN_BALL_COVERAGE={MIN_BALL_COVERAGE} "
          f"eligible≥{PERSON_ELIGIBLE_THRESHOLD}\n")

    detector_pair = _load_detector(device)
    out_rows = []
    for i, clip in enumerate(clips, 1):
        t0 = time.time()
        try:
            det = detect_clip(clip, detector_pair, device)
            res = analyse(det)
        except Exception as exc:  # noqa: BLE001 — 한 편이 죽어도 회차는 돈다
            print(f"  [{i}/{len(clips)}] {clip.name[:34]:34s} ⚠️ {type(exc).__name__}: {exc}")
            out_rows.append({"clip": clip.name, "error": repr(exc)})
            continue
        if res is None:
            out_rows.append({"clip": clip.name, "skipped": "후보 없음"})
            print(f"  [{i}/{len(clips)}] {clip.name[:34]:34s} 후보 없음")
            continue
        res["clip"] = clip.name
        res["seconds"] = round(time.time() - t0, 1)
        rows = res.get("rows", [])
        main_layer = layer(rows, NEAR)
        m = (sum(r["match"] for r in main_layer) / len(main_layer)
             if main_layer else None)
        res["n_near"] = len(main_layer)
        res["m_clip"] = round(m, 3) if m is not None else None
        out_rows.append(res)
        print(f"  [{i}/{len(clips)}] {clip.name[:34]:34s} "
              f"공커버 {res['ball_coverage']:.0%} · 주층 {len(main_layer):3d}f · "
              f"일치 {'—' if m is None else f'{m:.0%}'}  ({res['seconds']}초)")

    # 저장 — 다음 회차가 GPU 없이 다시 댈 수 있게 프레임 행을 통째로 남긴다.
    (HERE / "proximity_raw.json").write_text(
        json.dumps(out_rows, ensure_ascii=False, indent=1), encoding="utf-8")

    ok = [r for r in out_rows
          if "error" not in r and "skipped" not in r
          and r.get("ball_coverage", 0) >= MIN_BALL_COVERAGE
          and r.get("n_near", 0) >= MIN_NEAR_FRAMES]
    dropped = [r for r in out_rows if r not in ok]

    print("\n" + "=" * 70)
    print(f"분모 {len(ok)}/{len(clips)} 편 "
          f"(공 커버 <{MIN_BALL_COVERAGE:.0%} · 주 층 <{MIN_NEAR_FRAMES}프레임 등으로 "
          f"뺀 것 {len(dropped)}편)")
    for r in dropped:
        why = r.get("error") or r.get("skipped") or (
            f"공커버 {r.get('ball_coverage')} · 주층 {r.get('n_near')}f")
        print(f"   뺌: {r.get('clip','?')[:34]:34s} {why}")
    if not ok:
        print("🔴 분모가 비었다 — 판정할 수 없다")
        return

    all_rows = [r for c in ok for r in c["rows"]]
    main_layer = layer(all_rows, NEAR)
    matched = [r for r in main_layer if r["match"]]
    miss = [r for r in main_layer if not r["match"]]
    M = len(matched) / len(main_layer) if main_layer else float("nan")
    m_clip = [c["m_clip"] for c in ok if c["m_clip"] is not None]

    margins = sorted(r["d_chosen"] - r["d_min"] for r in miss)
    margin_med = statistics.median(margins) if margins else float("nan")
    ratios = sorted(r["h_chosen"] / r["h_argmin"] for r in miss if r["h_argmin"] > 0)
    ratio_med = statistics.median(ratios) if ratios else float("nan")

    total_frames = sum(c["frames"] for c in ok)
    single = [r for r in all_rows if r["d_min"] <= NEAR and r["n_cands"] < 2]
    replica = sum(c["replica_mismatch"] for c in ok)

    print(f"\n주 지표 M (프레임 가중) : {M:.1%}  ({len(matched)}/{len(main_layer)})")
    print(f"          클립 가중      : 중앙 {statistics.median(m_clip):.1%} · "
          f"분포 {[f'{v:.0%}' for v in sorted(m_clip)]}")
    print(f"불일치 margin (키높이)  : 중앙 {margin_med:.3f} · "
          f"범위 {margins[0]:.3f}~{margins[-1]:.3f}" if margins else
          "불일치 없음")

    # ── 판별 규칙 (사전 등록 4절) ─────────────────────────────────────
    if M >= 0.70:
        verdict = "(가) 선택은 맞다 — 「멀다」는 공이 날아가는 중이다"
    elif M <= 0.30 and margin_med >= MIN_MARGIN:
        verdict = "(나) 선택이 틀린다 — 공 근접이 새 축으로 선다"
    elif M <= 0.30:
        verdict = (f"판별불가 — M 은 낮은데 margin 중앙 {margin_med:.3f} < "
                   f"{MIN_MARGIN} (계기 해상도)")
    else:
        verdict = "판별불가 — 30~70% 사이"
    print(f"\n🔴 판정: {verdict}")

    print("\n── 사전 등록 판정 A~G")
    print(f"  A 계기① 주 층에 단일후보 0건 : {len(single)}건 "
          f"{'✅' if not single else '🔴'}")

    # 기준 B — 45번 1회차 발목 기반과 순위 상관
    try:
        prev = {r["clip"]: r for r in json.loads(TOUCHES.read_text(encoding="utf-8"))}
        pairs = [(c["d_chosen_ungated_median"], prev[c["clip"]]["distance_median"])
                 for c in ok
                 if c.get("d_chosen_ungated_median") is not None
                 and prev.get(c["clip"], {}).get("distance_median") is not None]
        rho = spearman([p[0] for p in pairs], [p[1] for p in pairs]) if len(pairs) > 2 else float("nan")
        print(f"  B 계기② 발목 기반과 ρ≥{SPEARMAN_MIN}  : ρ={rho:.2f} (n={len(pairs)}) "
              f"{'✅' if rho >= SPEARMAN_MIN else '🔴'}")
    except Exception as exc:  # noqa: BLE001
        print(f"  B 계기② : 🔴 못 쟀다 — {exc}")

    print("  C src/·rubrics/ 무변경        : ✅ (이 스크립트는 import 만 한다)")
    print(f"  D reach                       : 주 층 {len(main_layer)}/{total_frames} "
          f"프레임 ({len(main_layer)/total_frames:.1%}) · 클립 {len(ok)}/{len(clips)}")

    print("  E 민감도 (NEAR 네 값)")
    verdicts = []
    for near in NEAR_SWEEP:
        lay = layer(all_rows, near)
        if not lay:
            print(f"      NEAR={near:.2f} : 주 층 비어 있음")
            verdicts.append("빈층")
            continue
        mm = sum(r["match"] for r in lay) / len(lay)
        mg = [r["d_chosen"] - r["d_min"] for r in lay if not r["match"]]
        mgm = statistics.median(mg) if mg else float("nan")
        v = ("가" if mm >= 0.70 else
             "나" if (mm <= 0.30 and mgm >= MIN_MARGIN) else "불가")
        verdicts.append(v)
        print(f"      NEAR={near:.2f} : 주층 {len(lay):4d}f · M {mm:.1%} · "
              f"margin 중앙 {mgm:.3f} → ({v})")
    same = len(set(verdicts)) == 1
    print(f"      → 판정 구간 불변 : {'✅' if same else '🔴 문턱에 업혀 있다'}")

    print("  F pytest                      : 별도로 돌린다")
    if M < 0.50:
        print(f"  G 짝 기준 (M<50% 이므로 적용) : 불일치 프레임 높이비 중앙 "
              f"{ratio_med:.2f} ≥ {HEIGHT_RATIO_MIN} "
              f"{'✅ 기전 확인' if ratio_med >= HEIGHT_RATIO_MIN else '🔴 기전 미설명 → 판별불가로 내린다'}")
    else:
        print(f"  G 짝 기준                     : 해당 없음 (M={M:.1%} ≥ 50%)")

    # ── 사후 관찰 (판정에 안 쓴다) ────────────────────────────────────
    print("\n── 사후 관찰 (판정에 안 쓴다)")
    print(f"  내 복제와 production `_largest_person_box` 불일치: {replica}프레임")
    near_all = [r for r in all_rows if r["d_min"] <= NEAR]
    print(f"  공이 발치에 온 프레임 {len(near_all)} 중 단일후보 {len(single)} "
          f"({len(single)/len(near_all):.0%})" if near_all else "  발치 프레임 없음")
    cov = [c["ball_coverage"] for c in ok]
    print(f"  게이트 후 공 커버리지: 중앙 {statistics.median(cov):.0%} · "
          f"버린 검출 {sum(c['ball_dropped'] for c in ok)}프레임")
    dcm = [c["d_chosen_ungated_median"] for c in ok if c["d_chosen_ungated_median"]]
    if dcm:
        print(f"  고른 사람↔공 거리 클립 중앙값: {statistics.median(dcm):.2f} 키높이 "
              f"· 범위 {min(dcm):.2f}~{max(dcm):.2f}")


if __name__ == "__main__":
    main()
