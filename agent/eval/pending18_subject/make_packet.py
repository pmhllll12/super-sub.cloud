"""미결 `ho` 18번 판독 ① — 「이 프레임의 분석 대상은 누구인가」 판독 자료.

🔴 **[`AFTER_LABELS.md`](AFTER_LABELS.md) 를 먼저 읽는다.** 표본 추출·번호
매기기·안 넣은 것이 거기서 굳었고 **결과를 보고 고치지 않는다.**

**라벨을 만들지 않는다.** 사람이 보고 채울 자료만 낸다 — 🔴 **AI 가 채우면
정답이 아니다**(로드맵 2절, B-3~B-5 선례).

🔴 **이미지는 저장소에 안 들어간다** — SoccerNet 방송 프레임이다.
`<SoccerNet 루트>/../review_packet_18/` 에 쓴다.

    cd agent && uv run python eval/pending18_subject/make_packet.py

설계에서 정한 것들
------------------

**(1) 공을 그리지 않는다.** 판정하려는 신호가 공 근접인데 공을 표시하면
   「공 옆 사람」을 고르게 만든다. 그대로 앵커링이다.

**(2) 박스는 전부 같은 색·같은 굵기다.** 우리가 고른 것을 강조하지 않는다
   (B-4 검수 패킷이 후보 상자를 전부 같은 색으로 그린 것과 같은 이유).

**(3) 번호는 화면 왼쪽부터 붙인다** — 면적 순도 공 거리 순도 아니다.
   그러면 번호 자체가 힌트가 된다.

**(4) 앞뒤 프레임을 함께 준다.** 224p 정지 화면 하나로는 누가 공을 다루는지
   보기 어렵다. **앞뒤에는 박스를 안 그린다** — 가운데 한 프레임만 판정 대상이다.

**(5) 후보 크롭을 따로 붙인다.** 번호와 사람을 맞추는 데 쓴다. 크롭도
   같은 배율로 키워 **큰 사람이 더 또렷해 보이지 않게** 한다.
"""
from __future__ import annotations

import csv
import json
import sys
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
    _load_detector,
    read_frames_ex,
)

import paths  # noqa: E402

HERE = Path(__file__).resolve().parent
RULE_RAW = HERE.parent / "pending18_rule" / "rule_raw.json"

N_FRAMES = 70          # 🔴 AFTER_LABELS 6절에서 굳혔다
CONTEXT = 3            # 앞뒤 몇 프레임을 함께 보여줄 것인가
SCALE = 3              # 224p 는 그대로 보면 안 보인다
BOX_COLOR = (60, 220, 60)   # 🔴 전부 같은 색. 강조 없음
CROP_H = 150


def pick_frames(clip_rows: dict[str, list[dict]]) -> list[tuple[str, int]]:
    """🔴 클립 라운드로빈. **난수를 안 쓴다** (AFTER_LABELS 6절).

    클립마다 시간상 가장 멀리 떨어진 순서로 후보를 세워 두고, 클립을 돌아가며
    하나씩 뽑는다. 무작위로 뽑으면 **연속 프레임이 한 클립에 몰린다**.
    """
    ordered: dict[str, list[int]] = {}
    for clip, rows in clip_rows.items():
        ts = sorted(r["t"] for r in rows)
        picked: list[int] = []
        remaining = list(ts)
        while remaining:
            if not picked:                       # 첫 장은 가운데
                nxt = remaining[len(remaining) // 2]
            else:                                # 이미 뽑은 것에서 가장 먼 것
                nxt = max(remaining, key=lambda t: min(abs(t - p) for p in picked))
            picked.append(nxt)
            remaining.remove(nxt)
        ordered[clip] = picked

    out: list[tuple[str, int]] = []
    i = 0
    while len(out) < N_FRAMES:
        added = False
        for clip in sorted(ordered):
            if i < len(ordered[clip]):
                out.append((clip, ordered[clip][i]))
                added = True
                if len(out) == N_FRAMES:
                    break
        if not added:
            break                                 # 모든 클립을 다 썼다
        i += 1
    return out


def render(frames, t: int, boxes: list[tuple]) -> np.ndarray:
    """가운데 프레임(번호 붙은 박스) + 앞뒤 문맥 + 후보 크롭."""
    h, w = frames[t].shape[:2]
    main = cv2.resize(frames[t], (w * SCALE, h * SCALE),
                      interpolation=cv2.INTER_CUBIC)
    for i, b in enumerate(boxes, 1):
        x, y, bw, bh = [int(v * SCALE) for v in b]
        cv2.rectangle(main, (x, y), (x + bw, y + bh), BOX_COLOR, 2)
        cv2.putText(main, str(i), (x, max(14, y - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, BOX_COLOR, 2)
    # 🔴 **이미지 안에 한글을 쓰지 않는다.** OpenCV 의 Hershey 폰트는 한글을
    #    못 그려 전부 두부 상자가 된다(첫 판에서 실제로 그렇게 나왔다).
    #    설명은 INSTRUCTIONS.md 가 하고, 그림에는 **숫자와 ASCII 만** 남긴다.
    cv2.putText(main, "[ JUDGE THIS FRAME ]", (8, main.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    # 문맥 — 🔴 박스를 안 그린다
    ctx = []
    for dt in (-CONTEXT, CONTEXT):
        tt = min(max(t + dt, 0), len(frames) - 1)
        c = cv2.resize(frames[tt], (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
        cv2.putText(c, f"{dt:+d} (context, no boxes)", (6, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        ctx.append(c)
    ctx_row = np.hstack(ctx)
    if ctx_row.shape[1] != main.shape[1]:
        ctx_row = cv2.resize(ctx_row, (main.shape[1],
                                       int(ctx_row.shape[0] * main.shape[1]
                                           / ctx_row.shape[1])))

    # 후보 크롭 — 🔴 전부 같은 배율로 키운다
    crops = []
    for i, b in enumerate(boxes, 1):
        x, y, bw, bh = [int(v) for v in b]
        pad = 4
        sub = frames[t][max(0, y - pad):y + bh + pad, max(0, x - pad):x + bw + pad]
        if sub.size == 0:
            sub = np.zeros((10, 10, 3), np.uint8)
        s = CROP_H / max(1, sub.shape[0])
        sub = cv2.resize(sub, (max(1, int(sub.shape[1] * s)), CROP_H),
                         interpolation=cv2.INTER_CUBIC)
        tile = np.zeros((CROP_H + 22, max(44, sub.shape[1]), 3), np.uint8)
        tile[22:, : sub.shape[1]] = sub
        cv2.putText(tile, str(i), (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    BOX_COLOR, 2)
        crops.append(tile)
    crop_row = np.hstack(crops) if crops else np.zeros((CROP_H + 22, 10, 3), np.uint8)
    if crop_row.shape[1] > main.shape[1]:
        s = main.shape[1] / crop_row.shape[1]
        crop_row = cv2.resize(crop_row, (main.shape[1], int(crop_row.shape[0] * s)))
    else:
        pad = np.zeros((crop_row.shape[0], main.shape[1] - crop_row.shape[1], 3),
                       np.uint8)
        crop_row = np.hstack([crop_row, pad])

    return np.vstack([main, ctx_row, crop_row])


def main() -> None:
    import torch

    raw = json.loads(RULE_RAW.read_text(encoding="utf-8"))
    ok = [c for c in raw if c.get("ball_coverage", 0) >= MIN_BALL_COVERAGE
          and len(c.get("rows", [])) >= MIN_NEAR_FRAMES]
    clip_rows = {c["clip"]: c["rows"] for c in ok}
    layer = {c["clip"]: c["layer"] for c in ok}
    print(f"모집단: {len(ok)}클립 · "
          f"{sum(len(r) for r in clip_rows.values())}프레임 → {N_FRAMES}장 뽑는다\n")

    chosen = pick_frames(clip_rows)
    by_clip: dict[str, list[int]] = {}
    for clip, t in chosen:
        by_clip.setdefault(clip, []).append(t)

    out_dir = paths.soccernet_clips_root().parent / "review_packet_18"
    (out_dir / "images").mkdir(parents=True, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    det_pair = _load_detector(device)

    rows_csv, meta = [], []
    n = 0
    for clip_name in sorted(by_clip):
        clip = paths.soccernet_clips_root() / clip_name
        det = detect_clip(clip, det_pair, device)
        cands = det["cands"]
        ball = det["objects"].get("sports_ball")
        heights = [b[3] for f in cands for b in f]
        H = float(np.median(heights))
        ball, _ = gate_by_speed(ball, H)
        frames = read_frames_ex(clip, DEFAULT_TARGET_FPS, None,
                                DEFAULT_MAX_SECONDS).frames

        for t in sorted(by_clip[clip_name]):
            # 🔴 번호는 **화면 왼쪽부터**. 면적 순도 공 거리 순도 아니다.
            boxes = sorted(cands[t], key=lambda b: b[0])
            n += 1
            fid = f"f{n:02d}"
            cv2.imwrite(str(out_dir / "images" / f"{fid}.jpg"),
                        render(frames, t, boxes),
                        [cv2.IMWRITE_JPEG_QUALITY, 92])

            b = ball[t, :2]
            d = [float(np.hypot(*(np.asarray(foot_point(x)) - b)) / H) for x in boxes]
            meta.append({
                "id": fid, "clip": clip_name, "layer": layer[clip_name], "t": t,
                "n_cands": len(boxes), "scale_h": round(H, 1),
                # 🔴 **정답이 아니다.** 채점용 참조값이고 판독자에게 안 보인다.
                "ball_nearest": int(np.argmin(d)) + 1,
                "r0_area": int(np.argmax([x[2] * x[3] for x in boxes])) + 1,
                "r1_height": int(np.argmax([x[3] for x in boxes])) + 1,
                "boxes": [[round(v, 1) for v in x] for x in boxes],
            })
            rows_csv.append({"id": fid, "n_cands": len(boxes),
                             "subject": "", "confidence": "", "note": ""})
            print(f"  {fid}  {clip_name[:38]:38s} f{t:3d} · 후보 {len(boxes)}")

    with (out_dir / "subject_form.csv").open("w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=["id", "n_cands", "subject",
                                            "confidence", "note"])
        wr.writeheader()
        wr.writerows(rows_csv)

    # 🔴 참조값은 **판독 폴더가 아니라 저장소**에 둔다 — 판독자가 안 보게.
    (HERE / "packet_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "INSTRUCTIONS.md").write_text(
        (HERE / "INSTRUCTIONS.md").read_text(encoding="utf-8"), encoding="utf-8")

    print(f"\n{n}장 · {out_dir}")
    print("  images/ · subject_form.csv · INSTRUCTIONS.md")
    print(f"  참조값(판독자 비공개): {HERE / 'packet_meta.json'}")
    print("\n🔴 AI 가 채우면 정답이 아니다. 사람이 채운 것만 쓴다.")


if __name__ == "__main__":
    main()
