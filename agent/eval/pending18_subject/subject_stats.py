"""라벨이 채워지면 돌린다 — 미결 `ho` 18번 판독 ①.

🔴 **[`AFTER_LABELS.md`](AFTER_LABELS.md) 의 명세를 그대로 구현한다.** 합격선·
분모 규칙·판별 구간은 **라벨을 받기 전에** 굳었고(이 파일은 그 문서와 같은
커밋이다) **라벨을 보고 고치지 않는다.**

🔴 **서식이 비어 있으면 아무것도 계산하지 않고 멈춘다** — 빈 서식으로 0/0 을
내면 그 표가 결과처럼 인용된다.

    cd agent && uv run python eval/pending18_subject/subject_stats.py
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval" / "phaseA"))

import paths  # noqa: E402

HERE = Path(__file__).resolve().parent
META = HERE / "packet_meta.json"

# 🔴 AFTER_LABELS 에서 굳은 값. **결과를 보고 돌리지 않는다.**
BALL_STANDS = 0.70        # 공 근접이 선다
BALL_CLOSED = 0.30        # 공 근접을 닫는다
UNCLEAR_MAX = 0.20        # 넘으면 「판독이 성립하지 않았다」를 먼저 적는다
MIN_DENOM = 10            # 🔴 한 자릿수면 정확도를 내지 않는다


def wilson(k: int, n: int) -> tuple[float, float]:
    """Wilson 95% 구간. 🔴 점추정만 적지 않는다 (AFTER_LABELS 2절)."""
    if n == 0:
        return (float("nan"), float("nan"))
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def report(name: str, k: int, n: int) -> None:
    if n < MIN_DENOM:
        print(f"    {name:26s} 🔴 분모 {n} — 한 자릿수라 **정확도를 내지 않는다**")
        return
    lo, hi = wilson(k, n)
    print(f"    {name:26s} {k/n:6.1%}  ({k}/{n})  [{lo:.1%}, {hi:.1%}]")


def main() -> None:
    form = paths.soccernet_clips_root().parent / "review_packet_18" / "subject_form.csv"
    if not form.exists():
        print(f"🔴 서식이 없다: {form}\n"
              "   make_packet.py 로 먼저 만든다.")
        raise SystemExit(1)
    meta = {m["id"]: m for m in json.loads(META.read_text(encoding="utf-8"))}
    rows = list(csv.DictReader(form.open(encoding="utf-8")))

    filled = [r for r in rows if (r.get("subject") or "").strip()]
    if not filled:
        print(f"🔴 서식이 **비어 있다** ({len(rows)}행 중 0행). 아무것도 계산하지 "
              "않고 멈춘다 — 빈 서식으로 0/0 을 내면 그 표가 결과처럼 인용된다.")
        raise SystemExit(1)
    if len(filled) < len(rows):
        print(f"⚠️ {len(rows)}행 중 {len(filled)}행만 채워져 있다. "
              "**부분 결과임을 결과에 적을 것.**\n")

    # ── 분모 규칙 (AFTER_LABELS 2절) ──────────────────────────────────
    unclear = [r for r in filled if r["subject"].strip().lower() == "unclear"]
    none_ = [r for r in filled if r["subject"].strip().lower() == "none"]
    valid = [r for r in filled
             if r["subject"].strip().lower() not in ("unclear", "none")]

    u_rate = len(unclear) / len(filled)
    print(f"채워진 {len(filled)}장 · unclear {len(unclear)} ({u_rate:.0%}) · "
          f"none {len(none_)} ({len(none_)/len(filled):.0%}) · "
          f"유효 분모 **{len(valid)}**")
    if u_rate > UNCLEAR_MAX:
        print(f"\n🔴 **판독이 성립하지 않았다** — unclear 가 {u_rate:.0%} 로 "
              f"{UNCLEAR_MAX:.0%} 를 넘는다. 아래 수치는 전부 **그 조건부**다.")
    print("\n🔴 `none` 은 「후보 중에 대상이 없다」이고 검출 문제를 가리킨다 — "
          "선택 규칙 문제와 다르다.")

    def block(label: str, rs: list[dict]) -> dict:
        print(f"\n── {label} — 유효 {len(rs)}장")
        if not rs:
            print("    (없음)")
            return {}
        got = {"ball": 0, "r0": 0, "r1": 0, "none_of": 0}
        for r in rs:
            m = meta[r["id"]]
            try:
                pick = int(r["subject"])
            except ValueError:
                continue
            hit = False
            for key, ref in (("ball", "ball_nearest"), ("r0", "r0_area"),
                             ("r1", "r1_height")):
                if pick == m[ref]:
                    got[key] += 1
                    hit = True
            if not hit:
                got["none_of"] += 1
        n = len(rs)
        report("① P_ball 공 최근접", got["ball"], n)
        report("② P_R0  현행(면적)", got["r0"], n)
        report("③ P_R1  높이", got["r1"], n)
        report("④ 셋 다 아님", got["none_of"], n)
        return {"n": n, **got}

    A = block("층 A", [r for r in valid if meta[r["id"]]["layer"] == "A"])
    B = block("층 B", [r for r in valid if meta[r["id"]]["layer"] == "B"])
    ALL = block("전체", valid)

    # ── 판별 (AFTER_LABELS 4절) ───────────────────────────────────────
    print("\n── 판별 (AFTER_LABELS 4절)")
    if not A or not B or A["n"] < MIN_DENOM or B["n"] < MIN_DENOM:
        print("  🔴 층 A·층 B 중 한쪽의 분모가 한 자릿수다 — "
              "**층별 판별을 하지 않는다.** 전체 수치만 보고한다.")
    else:
        pa, pb = A["ball"] / A["n"], B["ball"] / B["n"]
        if pa >= BALL_STANDS and pb >= BALL_STANDS:
            print(f"  ✅ **공 근접이 선다** (층 A {pa:.0%} · 층 B {pb:.0%}) — "
                  "(다) 공 근접을 선택에 넣는 회차를 연다")
        elif pa <= BALL_CLOSED and pb <= BALL_CLOSED:
            print(f"  🔴 **공 근접을 닫는다** (층 A {pa:.0%} · 층 B {pb:.0%}) — "
                  "11~14회차의 M 은 대상 정확도가 아니었다. 로드맵 4절에 올린다")
        else:
            print(f"  🔴 **판별불가** (층 A {pa:.0%} · 층 B {pb:.0%})")

        # 🔴 짝 기준 (AFTER_LABELS 4절)
        if pa >= BALL_STANDS:
            r0a = A["r0"] / A["n"]
            if r0a >= BALL_STANDS:
                print(f"  🔴 **짝 기준 위반** — P_ball {pa:.0%} 인데 "
                      f"P_R0 도 {r0a:.0%} 다. 공 최근접과 argmax(area) 가 같은 "
                      "사람을 가리킨다는 뜻이라 M 이 12~18% 였던 것과 모순이다. "
                      "**표본이 주 층을 대표하는지 의심하고 결론을 내지 않는다**")

    if ALL:
        print(f"\n🔴 **말하지 않는 것** — 제품 성능이 아니고(방송), 채점 정확도가 "
              "아니며(사람이 28~86px), 10회차의 (A) 를 대신하지 않는다.")
        print("🔴 판독자가 한 명이면 **사람끼리의 일치도를 못 낸다** — "
              "그 한계를 결과에 적을 것.")


if __name__ == "__main__":
    main()
