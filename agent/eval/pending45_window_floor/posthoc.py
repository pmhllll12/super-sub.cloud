"""사후 관찰 — 미결 `ho` 45번 5회차. **판정 밖이다.**

`RESULTS.md` 의 「사후 관찰」 절 숫자를 내는 자리다. 🔴 **여기 나온 값으로
`PREREGISTRATION.md` 의 합격·불합격을 고쳐 쓰지 않는다** — 9회차가 8회차의
사전 판정을 안 고치고 옆에 붙여 둔 것이 옳았다.

    uv run python eval/pending45_window_floor/posthoc.py
"""
from __future__ import annotations

import collections
import gzip
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
LENGTHS = (60, 40, 30, 20, 15, 12, 10, 8, 6, 5)


def main() -> int:
    with gzip.open(HERE / "rows.json.gz", "rt", encoding="utf-8") as fh:
        rows = json.load(fh)["rows"]

    print("⑴ 가장자리 쏠림 — 관측 boundary율 / 산수 4/L")
    print(f"{'L':>4} | {'층':>2} | {'n':>5} | {'관측':>6} | {'산수':>6} | {'배율':>5} | {'z':>6}")
    for L in LENGTHS:
        for layer in ("E", "N"):
            sub = [r for r in rows if r["L"] == L and r["layer"] == layer]
            n = len(sub)
            b = sum(r["reason"] == "boundary" for r in sub)
            p = 4 / L
            z = (b - n * p) / math.sqrt(n * p * (1 - p))
            print(f"{L:>4} | {layer:>2} | {n:>5} | {b / n:6.1%} | {p:6.1%} | "
                  f"{b / n / p:5.2f} | {z:+6.2f}")

    print("\n⑵ 성립한 것의 창 안 자리 — L=20 (가장자리 네 자리는 정의상 0)")
    for layer in ("E", "N"):
        pos = [r["pos"] for r in rows
               if r["L"] == 20 and r["layer"] == layer and r["pos"] is not None]
        h = collections.Counter(pos)
        print(f"  층 {layer} n={len(pos):>4}: {[h.get(i, 0) for i in range(20)]}")

    print("\n⑶ 층 × 사유")
    c = collections.Counter((r["layer"], r["reason"].split(":")[0]) for r in rows)
    for k, v in sorted(c.items()):
        print(f"    {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
