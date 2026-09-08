#!/usr/bin/env python3
"""포즈 추출의 **실제 host RSS** 를 잰다 (미결 9번).

    uv run python eval/pending9_rss/measure_rss.py --plan safe    # 로컬(RAM 9GB)
    uv run python eval/pending9_rss/measure_rss.py --plan full    # EC2(RAM 15GB)
    uv run python eval/pending9_rss/measure_rss.py --clip X --frames 300

**왜 재나.** 미결 9번의 처방 후보는 「가드를 장수가 아니라 **바이트**로 둔다」이다.
지금 `DEFAULT_MAX_FRAMES=300` 은 해상도를 안 봐서, 같은 300장이 4K에서 7.46GB고
1080p에서 1.87GB다. 그런데 **예산을 프레임 바이트로만 잡을 수 없다** — 모델과
중간 텐서가 따로 든다. 항목이 「실제 RSS 를 재기 전에는 예산을 옮기지 않는다」고
적어 둔 것이 이 측정이다.

**무엇을 답해야 하나.** 예산을 정하려면 이 형태의 답이 필요하다:

    RSS ≈ base + k × (frames × width × height × 3)

`base`(모델·런타임 상수)와 `k`(프레임 배열이 실제로 차지하는 배수)를 얻으면,
「4K 300장이 지금 쓰는 만큼」을 바이트 예산으로 옮길 수 있다.

🔴 **이것은 측정이지 처방이 아니다.** `DEFAULT_MAX_FRAMES` 를 여기서 바꾸지
않는다 — 바꾸면 `features` 가 달라져 B-6 재실행을 부른다(미결 11번).

🔴 **RSS 는 프로세스 전체 값이다.** 파이썬 인터프리터·torch·CUDA 컨텍스트가
전부 들어 있다. 그래서 `base` 를 따로 재고(모델 적재 직후) 그 위의 증가분을 본다.

조사 스크립트라 `src/` 를 고치지 않는다 — import 만 한다.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

DATA = ROOT / "data"

#: 해상도가 다른 클립 두 편. 4K 는 세로(2160×3840)다.
#:
#: 🔴 **원본이 짧다** — `bball_shot.mp4` 146프레임 · `baseball_pitch_trim.mp4`
#: 92프레임. 이 항목의 핵심 조합인 **4K 300장을 원본으로는 못 잰다.** 그대로
#: 돌리면 92장을 재고 "300장"이라 적는다 — 조용히 틀리는 종류다(2026-09-08에
#: 실제로 그렇게 나왔다). 그래서 `--prepare` 로 이어 붙인 긴 클립을 만든다.
CLIPS = {
    "1080p": DATA / "bball_shot.mp4",
    "4k": DATA / "baseball_pitch_trim.mp4",
    "1080p_long": DATA / "tmp" / "rss_long_1080p.mp4",
    "4k_long": DATA / "tmp" / "rss_long_4k.mp4",
}

#: 원본을 몇 번 이어 붙일 것인가. 4K 92프레임 × 4 = 368 ≥ 300.
REPEAT = 4

#: 로컬(RAM 9GB, 가용 5GB)에서 안전한 범위. 4K 300장은 약 7.46GB라 넣지 않는다.
PLAN_SAFE = [("1080p", 60), ("1080p_long", 150), ("1080p_long", 300),
             ("4k", 30), ("4k", 60)]
#: EC2(RAM 15GB). 🔴 4K 300장이 여기 들어 있다 — 이 조합이 이 항목의 핵심이다.
PLAN_FULL = PLAN_SAFE + [("4k_long", 150), ("4k_long", 300)]


def rss_kb() -> int:
    """현재 프로세스의 RSS(KB). psutil 없이 /proc 로 읽는다."""
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1])
    return 0


def hwm_kb() -> int:
    """프로세스 생애 최고 RSS(KB). 샘플러가 놓친 봉우리도 여기 남는다."""
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmHWM:"):
            return int(line.split()[1])
    return 0


class Sampler:
    """RSS 곡선을 뜬다. 봉우리가 짧으면 표본이 놓치므로 `VmHWM` 과 함께 본다."""

    def __init__(self, period: float = 0.05) -> None:
        self.period = period
        self.samples: list[int] = []
        self._stop = threading.Event()
        self._t: threading.Thread | None = None

    def __enter__(self) -> Sampler:
        def loop() -> None:
            while not self._stop.is_set():
                self.samples.append(rss_kb())
                time.sleep(self.period)

        self._t = threading.Thread(target=loop, daemon=True)
        self._t.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        if self._t:
            self._t.join(timeout=2)

    @property
    def peak_kb(self) -> int:
        return max(self.samples) if self.samples else 0


def prepare_long_clips() -> None:
    """원본을 이어 붙여 긴 클립을 만든다 (`data/tmp/`, gitignore 안이다).

    RSS 는 **프레임 수 × 화소 수**로 정해지지 내용으로 정해지지 않는다. 같은
    클립을 이어 붙여 장수를 늘리는 것은 그래서 이 측정에 타당하다 — 다만
    **정확도 측정에는 쓸 수 없다**(같은 장면이 반복된다).
    """
    import subprocess

    out_dir = DATA / "tmp"
    out_dir.mkdir(parents=True, exist_ok=True)
    for src_key, dst_key in (("1080p", "1080p_long"), ("4k", "4k_long")):
        src, dst = CLIPS[src_key], CLIPS[dst_key]
        if dst.exists():
            print(f"  이미 있음: {dst.name}")
            continue
        listing = out_dir / f"{dst.stem}.txt"
        listing.write_text("".join(f"file '{src.resolve()}'\n" for _ in range(REPEAT)))
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
             "-i", str(listing), "-c", "copy", str(dst)],
            check=True,
        )
        listing.unlink(missing_ok=True)
        print(f"  만듦: {dst.name} ({src.name} × {REPEAT})")


def probe_video(path: Path) -> tuple[int, int]:
    import cv2

    cap = cv2.VideoCapture(str(path))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return w, h


def run_one(label: str, path: Path, frames: int, fps: int) -> dict:
    from supersub_agent.pose import extract_keypoints

    w, h = probe_video(path)
    before = rss_kb()
    with Sampler() as s:
        t0 = time.time()
        # observe=False — 이 실행은 서비스 입력이 아니다.
        pose = extract_keypoints(
            path, target_fps=fps, observe=False, max_frames=frames, max_seconds=1e9
        )
        elapsed = time.time() - t0
    n = len(pose.keypoints)
    theo_mb = n * w * h * 3 / 1e6  # BGR uint8 한 벌
    peak_mb = max(s.peak_kb, hwm_kb()) / 1e3
    return {
        "label": label, "clip": path.name, "w": w, "h": h,
        "requested_frames": frames, "frames": n, "target_fps": fps,
        "rss_before_mb": round(before / 1e3, 1),
        "rss_peak_mb": round(peak_mb, 1),
        "rss_delta_mb": round(peak_mb - before / 1e3, 1),
        "frame_bytes_mb": round(theo_mb, 1),
        "ratio_peak_over_frames": round(peak_mb / theo_mb, 2) if theo_mb else None,
        "seconds": round(elapsed, 1),
    }


def run_child(label: str, frames: int, fps: int) -> dict:
    """조합 하나를 **새 프로세스**에서 재고 결과 JSON 을 받는다.

    `VmHWM` 을 쓰려면 프로세스를 갈라야 한다 — 위 호출부 주석 참고.
    """
    import subprocess

    out = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()),
         "--clip", label, "--frames", str(frames), "--fps", str(fps)],
        capture_output=True, text=True, check=True,
    )
    line = [x for x in out.stdout.splitlines() if x.startswith("{")][-1]
    return json.loads(line)


def fit(rows: list[dict]) -> None:
    """`RSS ≈ base + k × frame_bytes` 를 해상도별로 맞춘다 (최소제곱, 점 2개 이상).

    사전 등록 A·B 가 이 두 값을 본다 — `base` 가 해상도끼리 20% 안에서 일치하는지,
    `k` 가 1.0~3.0 안인지.
    """
    print(f"\n{'='*70}\n적합: RSS_peak ≈ base + k × frame_bytes\n{'='*70}")
    # 🔴 **해상도로 묶는다 — 클립 이름이 아니라.** 같은 1920×1080 인데 원본과
    #    이어 붙인 클립의 이름이 달라 점이 둘로 쪼개진 적이 있다(2026-09-08).
    #    RSS 를 정하는 것은 화소 수지 파일 이름이 아니다.
    fits = {}
    for res in sorted({f"{r['w']}x{r['h']}" for r in rows}):
        pts = [(r["frame_bytes_mb"], r["rss_peak_mb"]) for r in rows
               if f"{r['w']}x{r['h']}" == res]
        if len(pts) < 2:
            print(f"  {res:12s} 점이 {len(pts)}개뿐 — 적합 불가")
            continue
        n = len(pts)
        sx = sum(x for x, _ in pts); sy = sum(y for _, y in pts)
        sxx = sum(x * x for x, _ in pts); sxy = sum(x * y for x, y in pts)
        den = n * sxx - sx * sx
        if den == 0:
            print(f"  {res:12s} 프레임 바이트가 전부 같다 — 적합 불가")
            continue
        k = (n * sxy - sx * sy) / den
        base = (sy - k * sx) / n
        fits[res] = (base, k)
        print(f"  {res:12s} 점 {n}개 · base {base:7.0f}MB · k {k:5.2f}")

    if len(fits) >= 2:
        bases = [b for b, _ in fits.values()]
        spread = (max(bases) - min(bases)) / max(bases) * 100
        print(f"\n  기준 A — base 편차 {spread:.0f}% (합격선 20% 이내): "
              f"{'✅' if spread <= 20 else '🔴'}")
    ks = [k for _, k in fits.values()]
    if ks:
        print(f"  기준 B — k {min(ks):.2f}~{max(ks):.2f} (합격선 1.0~3.0): "
              f"{'✅' if all(1.0 <= k <= 3.0 for k in ks) else '🔴'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", choices=("safe", "full"), default="safe",
                    help="safe=로컬(4K 300장 제외) · full=EC2")
    ap.add_argument("--clip", choices=tuple(CLIPS), help="한 조합만 돌린다")
    ap.add_argument("--frames", type=int, help="--clip 과 함께 쓴다")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--prepare", action="store_true",
                    help="긴 클립을 만들고 끝낸다 (data/tmp/, ffmpeg 필요)")
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "rss.json")
    args = ap.parse_args()

    if args.prepare:
        prepare_long_clips()
        return

    # 한 조합만 요청받은 경우 = **자식 프로세스**다. 재고 JSON 한 줄만 찍는다.
    if args.clip and args.frames:
        print(json.dumps(run_one(args.clip, CLIPS[args.clip], args.frames, args.fps),
                         ensure_ascii=False))
        return

    plan = PLAN_FULL if args.plan == "full" else PLAN_SAFE

    missing = {c for c, _ in plan if not CLIPS[c].exists()}
    if missing:
        raise SystemExit(f"클립이 없다: {[str(CLIPS[c]) for c in missing]}")

    print(f"{'조합':16s}{'프레임':>6s}{'해상도':>12s}{'프레임바이트':>12s}"
          f"{'RSS 피크':>10s}{'증가분':>9s}{'배수':>6s}{'초':>6s}")
    print("-" * 78)
    rows = []
    short = []
    for label, frames in plan:
        # 🔴 **조합마다 새 프로세스로 돈다.** `VmHWM` 은 프로세스 생애 최고라
        #    한 프로세스에서 이어 돌리면 **뒤 회차가 앞 회차의 봉우리를 물려받는다**
        #    — 2026-09-08 에 실제로 그렇게 나왔다(4K 30·60 과 1080p 300 이 전부
        #    같은 3759MB). 프로세스를 갈라야 앞 회차의 잔여 메모리도 안 섞인다.
        r = run_child(label, frames, args.fps)
        # 🔴 요청한 장수에 **도달하지 못한 회차는 쓰지 않는다.** 클립이 짧으면
        #    92장을 재고 "300장"이라 적게 되는데, 그것이 이 항목이 막으려는
        #    바로 그 종류의 오류다 (2026-09-08에 실제로 그렇게 나왔다).
        r["reached"] = r["frames"] == r["requested_frames"]
        if not r["reached"]:
            short.append(r)
        rows.append(r)
        print(f"{label + ' ' + str(frames):16s}{r['frames']:6d}"
              f"{r['w']}x{r['h']:>7}{r['frame_bytes_mb']:11.0f}MB"
              f"{r['rss_peak_mb']:9.0f}MB{r['rss_delta_mb']:8.0f}MB"
              f"{r['ratio_peak_over_frames'] or 0:6.2f}{r['seconds']:6.0f}")

    args.out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n원본 → {args.out}")

    if short:
        print("\n🔴 요청한 장수에 도달하지 못한 회차가 있다 — **이 값들을 쓰지 말 것**")
        for r in short:
            print(f"   {r['label']:12s} 요청 {r['requested_frames']:4d} → 실제 "
                  f"{r['frames']:4d}  ({r['clip']} 이 짧다)")
        print("   `--prepare` 로 이어 붙인 긴 클립을 만든 뒤 다시 돌린다.")
        raise SystemExit(2)

    fit(rows)
    print("\n🔴 여기서 DEFAULT_MAX_FRAMES 를 바꾸지 않는다 — features 가 달라져")
    print("   B-6 재실행을 부른다(미결 11번). 이 회차는 예산을 정할 근거만 만든다.")


if __name__ == "__main__":
    main()
