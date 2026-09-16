"""슛·패스 두 층의 드릴 클립을 받는다 (미결 `ho` 52번 1회차).

🔴 **사전 등록(`PREREGISTRATION.md`, 커밋 `d82550a`)을 먼저 읽는다.**

🔴 **영상은 각 업로더의 저작물이다 — 저장소에 커밋하지 않는다.** `/mnt/d` 에
둔다(골든셋 `fetch.sh` 와 같은 관행). 여기 커밋하는 것은 **출처 표**뿐이다.

🔴 **두 층을 같은 성격으로 맞춘다** — 한쪽만 중계 영상이면 분류기가 동작이
아니라 촬영 방식을 배운다. 그래서 양쪽 다 「단독 선수 드릴」로 검색한다.

    cd agent && uv run python eval/pending52_motion_id/fetch_clips.py
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEST = Path("/mnt/d/sports-pose/soccer/motion_id")

# 층마다 여러 질의를 쓴다 — 한 채널의 촬영 습관만 배우지 않게.
QUERIES: dict[str, list[str]] = {
    "inside_pass": [
        "inside foot pass technique slow motion",
        "how to pass a soccer ball inside of foot tutorial",
        "push pass technique football coaching",
        "inside foot passing drill individual",
    ],
    "instep_shot": [
        "instep drive shooting technique slow motion",
        "how to shoot with laces football tutorial",
        "instep kick technique individual training",
        "power shot technique football drill",
    ],
}

PER_QUERY = 8          # 질의당 후보
MIN_SEC, MAX_SEC = 4, 90
TARGET_PER_CLASS = 24  # 사전 등록 하한 15 + 품질 탈락 여유


def search(query: str, n: int) -> list[dict]:
    """제목·길이만 먼저 받는다 (내려받지 않는다)."""
    out = subprocess.run(
        ["yt-dlp", "--quiet", "--no-warnings", "--skip-download",
         "--dump-json", "--flat-playlist", f"ytsearch{n}:{query}"],
        capture_output=True, text=True, timeout=180,
    )
    rows = []
    for line in out.stdout.splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        dur = d.get("duration")
        if dur is None or not (MIN_SEC <= dur <= MAX_SEC):
            continue
        rows.append({"id": d["id"], "title": (d.get("title") or "").strip(),
                     "duration": dur, "query": query})
    return rows


def download(vid: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return True
    # 720p 이하로 묶는다 — 4K 를 받아 봐야 포즈 단계에서 줄인다.
    r = subprocess.run(
        ["yt-dlp", "--quiet", "--no-warnings",
         "-f", "bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]/b[height<=720]",
         "--merge-output-format", "mp4", "-o", str(dest),
         f"https://www.youtube.com/watch?v={vid}"],
        capture_output=True, text=True, timeout=600,
    )
    return r.returncode == 0 and dest.exists() and dest.stat().st_size > 0


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []

    for label, queries in QUERIES.items():
        outdir = DEST / label
        outdir.mkdir(parents=True, exist_ok=True)
        seen: set[str] = set()
        got = 0
        for q in queries:
            if got >= TARGET_PER_CLASS:
                break
            print(f"[{label}] 검색: {q}", flush=True)
            try:
                cands = search(q, PER_QUERY)
            except subprocess.TimeoutExpired:
                print("  ⏱ 검색 시간 초과 — 건너뛴다", flush=True)
                continue
            for c in cands:
                if got >= TARGET_PER_CLASS or c["id"] in seen:
                    continue
                seen.add(c["id"])
                path = outdir / f"{c['id']}.mp4"
                ok = False
                try:
                    ok = download(c["id"], path)
                except subprocess.TimeoutExpired:
                    ok = False
                print(f"  {'✅' if ok else '❌'} {c['id']} ({c['duration']}s) {c['title'][:60]}",
                      flush=True)
                if ok:
                    manifest.append({"label": label, **c,
                                     "path": str(path.relative_to(DEST))})
                    got += 1
        print(f"[{label}] 받은 것 {got}편", flush=True)

    out = HERE / "clips_manifest.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["label", "id", "title", "duration",
                                           "query", "path"])
        w.writeheader()
        w.writerows(manifest)
    print(f"\n출처 표: {out} ({len(manifest)}편)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
