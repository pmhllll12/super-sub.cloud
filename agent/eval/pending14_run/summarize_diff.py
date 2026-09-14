"""재산출과 보존 사본의 어긋남을 **분포로** 요약한다.

`compare_npz.py` 는 건별 판정이고 이쪽은 「얼마나·어디가」다. 🔴 `boxes` 는
프레임별 검출을 이어 붙인 배열이라 한 프레임에서 검출 수가 하나 달라지면
뒤가 통째로 밀린다 — 그래서 **`n` 이 같은 클립에서만 좌표를 비교**한다.
밀린 배열의 최대차(1800 같은 값)는 오차가 아니라 **정렬이 깨진 것**이다.

    uv run python eval/pending14_run/summarize_diff.py <재산출> <보존 사본> [candidates|cache]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


def summarize_candidates(fresh: Path, kept: Path) -> None:
    rows, n_diff_frames, n_frames, same_n = [], 0, 0, 0
    for p in sorted(kept.glob("*.npz")):
        a, b = np.load(fresh / p.name), np.load(p)
        na, nb = a["n"], b["n"]
        if na.shape != nb.shape:
            rows.append((p.stem, "프레임 수가 다르다", float("nan")))
            continue
        n_frames += na.size
        d = int((na != nb).sum())
        n_diff_frames += d
        if d == 0:
            same_n += 1
            mx = float(np.abs(a["boxes"] - b["boxes"]).max()) if a["boxes"].shape == b["boxes"].shape else float("nan")
            rows.append((p.stem, "n 동일", mx))
        else:
            rows.append((p.stem, f"n 다른 프레임 {d}/{na.size}", float("nan")))

    coords = [r[2] for r in rows if r[1] == "n 동일" and np.isfinite(r[2])]
    print(f"클립 {len(rows)} · `n` 이 전 프레임 같은 클립 {same_n}")
    print(f"`n` 이 갈린 프레임 {n_diff_frames}/{n_frames} ({n_diff_frames/max(n_frames,1):.2%})")
    if coords:
        print(
            f"`n` 이 같은 클립의 좌표 최대차: 중앙 {np.median(coords):.4g} px · "
            f"최대 {max(coords):.4g} px · 전부 1px 미만 {sum(c < 1 for c in coords)}/{len(coords)}"
        )
    worst = sorted((r for r in rows if r[1].startswith("n 다른")), key=lambda r: -int(r[1].split()[-1].split("/")[0]))
    for stem, what, _ in worst[:5]:
        print(f"  {stem}: {what}")


def summarize_cache(fresh: Path, kept: Path) -> None:
    shapes_ok, rows = 0, []
    for p in sorted(kept.glob("*.npz")):
        a, b = np.load(fresh / p.name), np.load(p)
        ka, kb = a["keypoints"], b["keypoints"]
        if ka.shape != kb.shape:
            rows.append((p.stem, None, None, "shape 다름"))
            continue
        shapes_ok += 1
        d = np.abs(ka[..., :2] - kb[..., :2])
        # 프레임별 최대 어긋남 — 사람이 바뀐 프레임과 좌표가 떨린 프레임을 가른다
        per_frame = d.reshape(d.shape[0], -1).max(axis=1)
        rows.append((p.stem, float(np.median(per_frame)), float(per_frame.max()),
                     f"10px 초과 프레임 {int((per_frame > 10).sum())}/{per_frame.shape[0]}"))
    med = [r[1] for r in rows if r[1] is not None]
    print(f"클립 {len(rows)} · keypoints shape 일치 {shapes_ok}")
    if med:
        print(f"프레임별 좌표 최대차의 중앙값: 중앙 {np.median(med):.4g} px · 최대 {max(med):.4g} px")
    big = sorted((r for r in rows if r[2] is not None), key=lambda r: -r[2])
    for stem, m, mx, note in big[:5]:
        print(f"  {stem}: 중앙 {m:.3g}px · 최대 {mx:.4g}px · {note}")


def main() -> None:
    fresh, kept = Path(sys.argv[1]), Path(sys.argv[2])
    kind = sys.argv[3] if len(sys.argv) > 3 else "candidates"
    (summarize_candidates if kind == "candidates" else summarize_cache)(fresh, kept)


if __name__ == "__main__":
    main()
