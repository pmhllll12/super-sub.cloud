"""보존 자산 사본이 **매니페스트와 같은지** 확인한다 (미결 `ho` 11번).

    uv run python eval/phaseA/verify_preserved.py                 # 기본 루트
    uv run python eval/phaseA/verify_preserved.py --root <경로>   # 두 번째 사본

🔴 **왜 있는가.** `clips/`(130MB)·`labeling/`(31MB)은 저장소에 넣을 성질이
아니라 **바깥에** 산다. 그러면 「그 사본이 그때 그 바이트인가」를 물을 방법이
필요하다 — 미결 47번이 그 질문에 **일주일**을 썼다. 그때 없던 것이 바로
이 매니페스트다.

정본은 `preserved_manifest.csv`(path·bytes·md5, 198개). **파일이 아니라 내용을**
본다 — mtime 은 복사 방법에 따라 달라지므로 아무것도 보장하지 않는다.

종료 코드 0 = 일치 · 1 = 어긋남. 🔴 **어긋나면 사본을 덮어쓰기 전에 어느 쪽이
맞는지부터 정한다** — 다른 사본이 틀렸을 수도 있고, 매니페스트가 낡았을 수도 있다.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "preserved_manifest.csv"

sys.path.insert(0, str(HERE))
from paths import external_root  # noqa: E402


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(root: Path, quick: bool = False) -> int:
    with open(MANIFEST, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    missing, wrong_size, wrong_hash = [], [], []
    for row in rows:
        target = root / row["path"]
        if not target.is_file():
            missing.append(row["path"])
            continue
        if target.stat().st_size != int(row["bytes"]):
            wrong_size.append(row["path"])
            continue
        if not quick and md5(target) != row["md5"]:
            wrong_hash.append(row["path"])

    bad = len(missing) + len(wrong_size) + len(wrong_hash)
    print(f"루트 {root}")
    print(f"  매니페스트 {len(rows)}개 · 없음 {len(missing)} · 크기 다름 "
          f"{len(wrong_size)} · 내용 다름 {len(wrong_hash)}"
          f"{' (크기만 봤다)' if quick else ''}")
    for label, items in (("없음", missing), ("크기", wrong_size), ("내용", wrong_hash)):
        for path in items[:5]:
            print(f"    [{label}] {path}")
        if len(items) > 5:
            print(f"    [{label}] … 외 {len(items) - 5}개")
    print("판정:", "✅ 일치" if bad == 0 else f"🔴 {bad}개 어긋남")
    return 0 if bad == 0 else 1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=None,
                    help="확인할 사본의 뿌리 (기본: SUPERSUB_PHASEA_ROOT 또는 그 기본값)")
    ap.add_argument("--quick", action="store_true",
                    help="크기만 본다. 🔴 내용 변조는 못 잡는다 — 평소엔 쓰지 않는다")
    args = ap.parse_args()
    raise SystemExit(verify(args.root or external_root(), args.quick))


if __name__ == "__main__":
    main()
