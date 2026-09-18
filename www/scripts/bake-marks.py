#!/usr/bin/env python3
"""`scripts/marks.html` 을 크롬으로 그려 `public/marks/13~21.png` 을 굽는다.

    python3 scripts/bake-marks.py

🔴 **01~12 는 건드리지 않는다.** 그건 밖에서 받은 그림이고 여기서 나오는 것이
아니다. 이 스크립트는 13 번부터만 덮어쓴다.

의존: Pillow(`pip install pillow`)와 크롬. 둘 다 없으면 안내하고 멈춘다.

──────────────────────────────────────────────────────────────────────────
굽는 규칙 — 왜 이렇게 하는지

🔴 **마스크는 알파만 쓴다.** `CardMark.tsx` 가 `mask-image` 로 먹이고 칠하는
   것은 `currentColor` 라, 색을 구워 넣으면 사용자가 고른 「자국 색」이 죽는다.
   그래서 L 은 0 으로 눕히고 모양은 전부 알파에 담는다(LA 모드).

🔴 **알파 계단을 줄일 때 0 과 255 를 보존해야 한다.** `(v//s)*s + s//2` 로
   만들면 **완전 투명(0)이 s/2 로 떠올라** 자국의 네모난 상자가 카드 배경에
   비친다. 실제로 한 번 그렇게 구웠다가 화면에서 잡았다.

⚠️ **결이 거친 것과 선이 깨끗한 것을 다르게 굽는다.** 노이즈가 많은 그림은
   계단을 16 단까지 줄여도 노이즈가 가려서 안 보이는데, 용량은 1/5 로 준다.
   반대로 선·면이 깨끗한 것은 16 단이면 **띠가 그대로 보인다**. 붓 탭을 열면
   자국이 한꺼번에 받아지므로 용량이 그냥 버려지는 값이 아니다.
"""

import io
import os
import shutil
import subprocess
import sys
import tempfile

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow 가 필요합니다:  pip install pillow")

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "marks.html")
OUT = os.path.join(HERE, "..", "public", "marks")
TILE = 1200

# (마스크 번호, 이름, 긴 변 픽셀, 알파 단계) — marks.html 의 그린 순서와 같아야 한다.
SPEC = [
    (13, "잉크 블룸", 1024, 64),
    (14, "글리치 스펙트럼", 768, 16),
    (15, "홀로그램 레이어", 1024, 64),
    (16, "모래 폭풍", 768, 16),
    (17, "유동 금속", 1024, 64),
    (18, "파티클 플럭스", 1024, 64),
    (19, "디지털 글리치 박스", 1024, 64),
    (20, "거친 숯 번짐", 768, 16),
    (21, "겹치는 사각형", 768, 16),
]

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    shutil.which("google-chrome"),
    shutil.which("chromium"),
    shutil.which("chromium-browser"),
]


def find_chrome() -> str:
    for c in CHROME_CANDIDATES:
        if c and os.path.exists(c):
            return c
    sys.exit("크롬을 못 찾았습니다. 설치하거나 CHROME_CANDIDATES 에 경로를 더하세요.")


def render(chrome: str, dest: str) -> None:
    """9 장을 한 장의 세로 시트로 받는다 — 크롬을 한 번만 띄우면 된다."""
    subprocess.run(
        [
            chrome,
            "--headless",
            "--disable-gpu",
            "--hide-scrollbars",
            "--force-device-scale-factor=1",
            # 🔴 이게 없으면 바탕이 흰색으로 깔려 알파가 통째로 255 가 된다.
            "--default-background-color=00000000",
            "--virtual-time-budget=9000",
            f"--window-size={TILE},{TILE * len(SPEC)}",
            f"--screenshot={dest}",
            f"file://{SRC}",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def quantize_lut(levels: int) -> list[int]:
    """0 과 255 를 보존하는 계단. 위 머리말의 「네모난 상자」가 이것 때문이다."""
    n = levels - 1
    lut = [round(round(v / 255 * n) / n * 255) for v in range(256)]
    assert lut[0] == 0 and lut[255] == 255
    return lut


def main() -> None:
    chrome = find_chrome()
    with tempfile.TemporaryDirectory() as tmp:
        sheet_path = os.path.join(tmp, "sheet.png")
        print(f"크롬으로 그리는 중… ({os.path.basename(chrome)})")
        render(chrome, sheet_path)
        sheet = Image.open(sheet_path)
        if sheet.size != (TILE, TILE * len(SPEC)):
            sys.exit(f"시트 크기가 예상과 다릅니다: {sheet.size}")

        total = 0
        for i, (num, name, longest, levels) in enumerate(SPEC):
            tile = sheet.crop((0, i * TILE, TILE, (i + 1) * TILE))
            box = tile.split()[-1].getbbox()
            if box is None:
                sys.exit(f"{num}.png 이 비었습니다 — marks.html 의 {i + 1} 번째 그림을 보세요.")
            tile = tile.crop(box)
            w, h = tile.size
            k = longest / max(w, h)
            tile = tile.resize((round(w * k), round(h * k)), Image.LANCZOS)
            alpha = tile.split()[-1].point(quantize_lut(levels))
            la = Image.merge("LA", (Image.new("L", alpha.size, 0), alpha))
            path = os.path.join(OUT, f"{num}.png")
            la.save(path, "PNG", optimize=True)
            size = os.path.getsize(path)
            total += size
            print(f"  {num}.png  {la.size[0]:4d}×{la.size[1]:<4d} {levels:3d}단  {size / 1024:6.1f} KB  {name}")
        print(f"합계 {total / 1024:.0f} KB")


if __name__ == "__main__":
    main()
