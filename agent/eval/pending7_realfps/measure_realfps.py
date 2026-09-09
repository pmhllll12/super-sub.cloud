#!/usr/bin/env python3
"""실영상 fps 불변성 — 다시 인코딩해 전 구간을 태운다 (미결 `ho` 7·34번).

    uv run python eval/pending7_realfps/measure_realfps.py

판정 기준은 [`PREREGISTRATION.md`](PREREGISTRATION.md) 에 **코드보다 먼저**
고정했다(`edb6520`). 🔴 **합격선을 여기서 정하지 않는다** — 기준선 수립이다.

🔴 `eval/pending7_fps/` 와 **다른 것을 잰다.** 그쪽은 외부 포즈 시계열을 솎은
모의이고(디코딩·포즈 추정 없음), 여기는 파일을 다시 만들어 디코딩부터 돈다.
둘 다 남긴다.

🔴 **하향만 한다.** 프레임을 복제해 fps 를 올리면 「같은 장면을 더 높은 fps 로
찍은 것」이 아니다 — 없는 정보를 지어내게 된다.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

SOCCER = ROOT / "data" / "goldenset" / "soccerkicks_video"

# 🔴 `pending34_repro` 와 **같은 표본**이다. 「가만두면 0.00, fps 바꾸면 얼마」를
#    나란히 말하려면 같은 클립이어야 한다.
CLIPS = [
    (SOCCER / "10_penalty1.avi", "football_instep_shot.yaml"),
    (SOCCER / "11_freekick.avi", "football_instep_shot.yaml"),
    (SOCCER / "12_penalty.avi", "football_instep_shot.yaml"),
    (ROOT / "data" / "bball_shot.mp4", "basketball_jump_shot.yaml"),
]
DIVISORS = (1, 2, 3)  # 원본 · 1/2 · 1/3 (사전 등록 3절)


def source_fps(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True).stdout.strip()
    return float(Fraction(out))


def reencode(src: Path, dst: Path, fps: float) -> None:
    """🔴 `-r` 만 쓴다. 보간 필터를 걸면 없던 중간 자세를 만들어 낸다."""
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
         "-r", f"{fps:.6f}", "-an", str(dst)],
        check=True)


def child(video: Path, rubric_name: str) -> None:
    """한 변형. 회차마다 새 프로세스로 돈다(전역 상태를 물려받지 않게)."""
    from supersub_agent.features import extract_features
    from supersub_agent.pose import extract_keypoints
    from supersub_agent.scoring import aggregate, load_rubric

    rubric = load_rubric(ROOT / "rubrics" / rubric_name)
    try:
        pose = extract_keypoints(str(video), observe=False)
        features = extract_features(
            pose.keypoints, impact_limb=rubric.impact_limb,
            impact_event=rubric.impact_event, objects=pose.objects,
        )
    except Exception as exc:  # noqa: BLE001 — 품질 게이트 포함. 결과로 센다.
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"},
                         ensure_ascii=False))
        return

    applicable = rubric.applicable_criteria(features)
    judgments = {c.id: {"grade": c.grade_for(features), "evidence": ""}
                 for c in applicable}
    result = aggregate(judgments, rubric, features=features)
    print(json.dumps({
        "ok": True, "score": result["score"], "grade": result["grade"],
        "grades": {c.id: judgments[c.id]["grade"] for c in applicable},
        "sampled_fps": round(float(pose.sampled_fps), 2),
        "frames": int(len(pose.keypoints)),
    }, ensure_ascii=False, sort_keys=True))


def run(video: Path, rubric_name: str) -> dict:
    p = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--child", str(video),
         "--rubric", rubric_name],
        capture_output=True, text=True, cwd=ROOT)
    line = next((l for l in reversed(p.stdout.splitlines()) if l.startswith("{")), "")
    return json.loads(line) if line else {
        "ok": False, "error": f"자식이 결과를 안 냈다 ({p.returncode})"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--child", type=Path)
    ap.add_argument("--rubric", default="football_instep_shot.yaml")
    args = ap.parse_args()
    if args.child:
        child(args.child, args.rubric)
        return

    score_deltas: list[int] = []
    band_changes = grade_changes = gate_splits = total_variants = 0

    for video, rubric_name in CLIPS:
        if not video.exists():
            print(f"⚠ 없는 클립: {video}")
            continue
        src = source_fps(video)
        print(f"=== {video.name} · 원본 {src:.2f}fps ({rubric_name}) ===")

        with tempfile.TemporaryDirectory(prefix="realfps-") as tmp:
            base = None
            for d in DIVISORS:
                fps = src / d
                if d == 1:
                    target, label = video, f"원본 {fps:.2f}fps"
                else:
                    target = Path(tmp) / f"{video.stem}_1over{d}.mp4"
                    reencode(video, target, fps)
                    label = f"1/{d} → {fps:.2f}fps"

                r = run(target, rubric_name)
                if not r["ok"]:
                    print(f"  {label:22} 🔴 실패 — {r['error'][:70]}")
                    if base is not None:
                        gate_splits += 1
                        total_variants += 1
                    continue
                if d == 1:
                    base = r
                    print(f"  {label:22} {r['score']:3}점 ({r['grade']}) "
                          f"· 실효 {r['sampled_fps']}fps · {r['frames']}프레임")
                    continue

                total_variants += 1
                # 🔴 **부호를 지우지 않는다.** 처음엔 abs 를 취한 뒤 `+` 형식으로
                #    찍어서 전부 양수처럼 보였다 — 그러면 「편향인가 산포인가」를
                #    말할 수 없다. 방향이 결론을 바꾸는 자리다.
                ds = r["score"] - base["score"]
                score_deltas.append(ds)
                moved = [k for k in base["grades"]
                         if r["grades"].get(k) != base["grades"][k]]
                band = r["grade"] != base["grade"]
                band_changes += band
                grade_changes += bool(moved)
                mark = " 🔴" if band else ""
                print(f"  {label:22} {r['score']:3}점 ({r['grade']}) "
                      f"· 실효 {r['sampled_fps']}fps · {r['frames']}프레임"
                      f"  Δ{ds:+3d}점{mark}")
                if moved:
                    print(f"  {'':22} 등급 바뀐 항목 {len(moved)}개: {moved}")
        print()

    print("=" * 66)
    if not total_variants:
        raise SystemExit("변형을 하나도 못 돌렸다")
    n = len(score_deltas)
    worst = max((abs(d) for d in score_deltas), default=0)
    mean_abs = sum(abs(d) for d in score_deltas) / n if n else 0.0
    mean_signed = sum(score_deltas) / n if n else 0.0
    ups = sum(1 for d in score_deltas if d > 0)
    downs = sum(1 for d in score_deltas if d < 0)
    print(f"변형 {total_variants}개 (클립 {len(CLIPS)} × 하향 {len(DIVISORS) - 1})"
          f" — 그중 게이트 반려 {gate_splits}개")
    # 🔴 분모를 섞지 않는다. 점수 통계는 **성공한 변형** 기준이고, 게이트에
    #    반려된 것은 점수가 없어서 들어갈 수 없다.
    print(f"  [성공 {n}개 기준] 총점 |Δ| 평균 {mean_abs:.1f}점 · 최악 {worst}점")
    print(f"                   부호 있는 평균 {mean_signed:+.1f}점"
          f"  (올라간 것 {ups} · 내려간 것 {downs})")
    if n and (ups == 0 or downs == 0):
        print("  🔴 한쪽으로만 움직였다 — 산포가 아니라 **편향**으로 보인다."
              " 표본이 작으니 단정하지 않는다")
    print(f"  최종 등급 변경 {band_changes}/{n}"
          + (f" ({band_changes / n:.0%})" if n else ""))
    print(f"  항목 등급 변경 {grade_changes}/{n}"
          + (f" ({grade_changes / n:.0%})" if n else ""))
    print("\n🔴 합격선은 여기서 정하지 않는다 — 기준선이다(사전 등록 2절).")
    print("🔴 pending7_fps 의 37% 를 대체하지 않는다 — 다른 것을 잰다.")


if __name__ == "__main__":
    main()
