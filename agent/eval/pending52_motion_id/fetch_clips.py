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
        "side foot pass soccer technique demonstration",
        "inside of the foot pass coaching point youth soccer",
        "short pass technique football slow motion",
        "push pass soccer fundamentals demonstration",
        "inside kick soccer technique slow motion",
        "how to strike a pass inside of foot side view",
        "soccer passing technique analysis single player",
        "inside foot kick demonstration football coaching",
        "ground pass technique soccer tutorial",
        "basic passing technique football academy inside",
        "inside foot pass coaching demonstration slow",
        "passing technique soccer player demonstration inside foot",
        "soccer inside pass practice wall",
        "football passing technique breakdown inside of foot",
        "learn to pass football inside foot beginner",
        "passing with the inside of the foot youth coaching",
    ],
    "instep_shot": [
        "instep drive shooting technique slow motion",
        "how to shoot with laces football tutorial",
        "instep kick technique individual training",
        "power shot technique football drill",
        "laces shot technique soccer demonstration",
        "instep drive soccer coaching demonstration",
        "shooting technique slow motion football striker",
        "full volley instep strike technique",
    ],
}

# 🔴 **제목으로 거르는 규칙 — 측정 전에 정한다.** 라벨이 제목에서 오므로
#    제목이 두 동작을 함께 말하거나 다른 동작을 말하면 그 클립은 라벨이 없다.
#    이것은 결과를 보고 고르는 것이 아니라 **라벨 규칙 자체**다.
EXCLUDE_WORDS: dict[str, tuple[str, ...]] = {
    # 로프티드·칩·롱패스는 **발등**으로 찬다 — 인사이드가 아니다.
    # 론도·경기 장면은 단독 드릴이 아니라 대상 선택이 흔들린다(미결 45번).
    # 프리킥·슛은 검색이 물어 온 오답이다 — 패스가 아니다.
    "inside_pass": ("lofted", "chip", "long pass", "driven pass", "rondo",
                    "outside", "laces", "volley", "curve", "bend",
                    "freekick", "free kick", "shoot", "shot", "finishing",
                    "goal"),
    # 인사이드를 함께 가르치는 영상, 헤딩은 인스텝 드라이브가 아니다.
    "instep_shot": ("inside of", "inside foot", "side foot", "header", "outside"),
}

# 🔴 **축구가 아닌 종목**이 검색에 섞인다 — 호주식 풋볼 `goalkicking`, 럭비 등.
#    루브릭은 축구 전용이고, 다른 종목 동작을 축구 라벨로 재면 그 자체가 오염이다.
NOT_FOOTBALL = ("goalkicking", "afl", "rugby", "gaelic", "punt")

# 🔴 **제목이 동작을 명시해야 라벨이 있다.** 금지어를 하나씩 늘리는 방식은 끝이
#    없다 — 「Soccer Tricks: The Bicycle Kick」·「detail soccer player kicking
#    ball」처럼 **패스라고 말한 적 없는** 영상이 패스 질의에 걸려 들어왔다.
#    그래서 규칙을 뒤집는다: 있어야 할 말을 요구한다.
REQUIRE_WORDS: dict[str, tuple[str, ...]] = {
    "inside_pass": ("inside", "push pass", "passing", "pass"),
    "instep_shot": ("instep", "laces", "shoot", "shot", "strike", "striking",
                    "drive", "volley", "finishing"),
}


def excluded(label: str, title: str) -> str | None:
    """제외 사유. 없으면 None."""
    low = title.lower()
    for w in NOT_FOOTBALL:
        if w in low:
            return f"{w}(축구 아님)"
    for w in EXCLUDE_WORDS[label]:
        if w in low:
            return w
    if not any(w in low for w in REQUIRE_WORDS[label]):
        return "동작을 밝히지 않음"
    return None

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
                why = excluded(label, c["title"])
                if why:
                    print(f"  ⊘ {c['id']} 제외(제목에 {why!r}): {c['title'][:55]}",
                          flush=True)
                    continue
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

    # 🔴 **두 층에 같은 영상이 들어오면 라벨이 모순이다** — 양쪽에서 뺀다.
    #    (검색이 「laces and inside of the foot」 같은 겸용 강의를 물어 온다.)
    by_id: dict[str, set[str]] = {}
    for m in manifest:
        by_id.setdefault(m["id"], set()).add(m["label"])
    both = {i for i, labels in by_id.items() if len(labels) > 1}
    for i in sorted(both):
        print(f"⊘ {i} 제외 — 두 층에 모두 걸렸다(라벨 모순)", flush=True)
    manifest = [m for m in manifest if m["id"] not in both]

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
