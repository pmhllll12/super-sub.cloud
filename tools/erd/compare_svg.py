"""두 SVG 가 **내용상 같은지** 본다 — 그리는 순서만 다른 것을 걸러내려고.

## 왜 필요한가

`gen_erd.py` 를 다시 돌리면 **스키마를 안 바꾼 도메인의 그림도 바이트 diff 가
난다.** ORM 메타데이터 순회 순서가 실행마다 달라서 `<g>` 조각이 **같은 것이
다른 순서로** 나오기 때문이다(2026-09-17 에 실제로 겪었다 — 사용자·팀,
영상·분석 둘이 그랬다). 그대로 커밋하면 **뜻 없는 diff** 가 되어, 나중에
`git log` 로 "이 그림이 왜 바뀌었나" 를 볼 때 진짜 변경이 묻힌다.

## 쓰는 법

    python3 tools/erd/compare_svg.py <옛 파일> <새 파일>

`같음` 이면 되돌린다(`git checkout -- <그 파일>` 또는 백업에서 복사).
`다름` 이면 진짜로 스키마가 바뀐 것이니 올린다.

여러 장을 한 번에 보려면 폴더 둘을 준다:

    python3 tools/erd/compare_svg.py <옛 폴더> <새 폴더>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# `<g` 부터 짝이 되는 `</g>` 까지를 한 조각으로 본다. 중첩이 없는 생성물이라
# 이 단순한 방식으로 충분하다 — 중첩이 생기면 이 가정부터 다시 본다.
PIECE = re.compile(r"<g[ >].*?</g>", re.S)


def pieces(path: Path) -> list[str]:
    return sorted(PIECE.findall(path.read_text(encoding="utf-8")))


def compare(old: Path, new: Path) -> bool:
    """내용이 같으면 True."""
    return pieces(old) == pieces(new)


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    old, new = Path(sys.argv[1]), Path(sys.argv[2])

    if old.is_dir() != new.is_dir():
        print("🔴 한쪽만 폴더다 — 둘 다 파일이거나 둘 다 폴더여야 한다")
        return 2

    targets = (
        sorted(p.name for p in new.glob("*.svg")) if new.is_dir() else [None]
    )
    changed = []
    for name in targets:
        a, b = (old / name, new / name) if name else (old, new)
        if not a.exists():
            print(f"새로 생김  {b.name}")
            changed.append(b.name)
            continue
        same = compare(a, b)
        print(f"{'같음(순서만 다름)' if same else '🔴 다름(내용 변화)':<20} {b.name}")
        if not same:
            changed.append(b.name)

    print()
    if changed:
        print("내용이 바뀐 그림:", " ".join(changed))
        print("→ 이것만 올리고 나머지는 되돌린다.")
    else:
        print("내용 변화 없음 — 전부 되돌린다(뜻 없는 diff 를 안 남긴다).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
