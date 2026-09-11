"""재산출 `.npz` 를 보존 사본과 **배열 단위로** 대조한다 (사전 등록 기준 B·C).

🔴 바이트로 비교하지 않는다 — `np.savez_compressed` 는 zip 항목에 쓰는 시각을
넣어서 내용이 같아도 바이트가 다르다. 사전 등록에 그 이유를 적어 두었다.

    uv run python eval/pending14_run/compare_npz.py <재산출 디렉터리> <보존 사본>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


def compare_one(a: Path, b: Path) -> list[str]:
    """두 npz 의 차이를 사람이 읽을 수 있는 줄로 낸다. 같으면 빈 목록."""
    with np.load(a, allow_pickle=False) as za, np.load(b, allow_pickle=False) as zb:
        ka, kb = set(za.files), set(zb.files)
        diffs = []
        if ka != kb:
            if ka - kb:
                diffs.append(f"재산출에만 있는 키: {sorted(ka - kb)}")
            if kb - ka:
                diffs.append(f"사본에만 있는 키: {sorted(kb - ka)}")
        for k in sorted(ka & kb):
            x, y = za[k], zb[k]
            if x.shape != y.shape:
                diffs.append(f"{k}: shape {x.shape} != {y.shape}")
            elif x.dtype != y.dtype:
                diffs.append(f"{k}: dtype {x.dtype} != {y.dtype}")
            elif not np.array_equal(x, y):
                # 어긋난 정도를 함께 낸다 — 「다르다」만으로는 재현성 문제인지
                # 경로가 다른 입력을 읽은 것인지 가를 수 없다.
                if np.issubdtype(x.dtype, np.floating):
                    d = np.abs(x.astype(np.float64) - y.astype(np.float64))
                    diffs.append(
                        f"{k}: 값 다름 (다른 원소 {int((x != y).sum())}/{x.size}, "
                        f"최대차 {np.nanmax(d):.6g})"
                    )
                else:
                    diffs.append(f"{k}: 값 다름 (다른 원소 {int((x != y).sum())}/{x.size})")
        return diffs


def main() -> int:
    fresh, kept = Path(sys.argv[1]), Path(sys.argv[2])
    names = sorted(p.name for p in kept.glob("*.npz"))
    same, differ, missing = 0, [], []
    for name in names:
        f = fresh / name
        if not f.exists():
            missing.append(name)
            continue
        diffs = compare_one(f, kept / name)
        if diffs:
            differ.append((name, diffs))
        else:
            same += 1
    extra = sorted({p.name for p in fresh.glob("*.npz")} - set(names))

    print(f"보존 사본 {len(names)}개 · 동일 {same} · 다름 {len(differ)} · 없음 {len(missing)}")
    if extra:
        print(f"사본에 없는 재산출: {extra}")
    for name, diffs in differ:
        print(f"\n🔴 {name}")
        for d in diffs:
            print(f"   {d}")
    if missing:
        print(f"\n🔴 재산출되지 않음: {missing}")
    return 0 if (same == len(names) and not extra) else 1


if __name__ == "__main__":
    raise SystemExit(main())
