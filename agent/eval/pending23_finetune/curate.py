#!/usr/bin/env python3
"""후보 선별 — 코드가 거른 뒤 남은 것을 **방향으로** 가른다 (사전 등록 1절).

    uv run python eval/pending23_finetune/curate.py sheet
    uv run python eval/pending23_finetune/curate.py apply --picks picks.json

`sheet` 는 자리마다 **코드가 말하는 방향**(`criterion.plain_for`)을 맨 위에 놓고
자동 거르기를 통과한 후보를 번호로 찍는다. 담당자는 그 방향과 **같은 방향인
후보의 번호**만 고른다 — 「어떤 문장이 좋은가」가 아니라 **대조**다.

`apply` 는 고른 결과로 (1) 학습셋 `sft.jsonl` (2) 사람이 볼 `SPOTCHECK.md`
30개를 낸다. 🔴 **30개는 고른 것 20 + 버린 것 10** 이다 — 고른 것만 보여 주면
「버릴 것을 버렸는가」가 안 잡힌다.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

sys.path.insert(0, str(ROOT / "eval/pending23_evidence"))
sys.path.insert(0, str(HERE))

from generate import auto_flags  # noqa: E402

from supersub_agent.judge import build_prompt, system_prompt  # noqa: E402
from supersub_agent.scoring import discover_rubrics  # noqa: E402

CANDS = HERE / "candidates_instep.json"
SPOT_ACCEPTED, SPOT_REJECTED, SPOT_SEED = 20, 10, 20260918


def load() -> dict:
    """저장된 후보를 읽고 **거르개를 다시 계산한다**.

    🔴 생성 때 박힌 `flags` 를 믿지 않는다 — 09:53 에 `metric_ref` 조항을
    걷었고(생성 중이라 그 실행의 flags 는 옛 규칙이다), 문장 자체는 그대로라
    다시 계산하면 된다. **문장을 다시 만들지 않는다.**
    """
    data = json.loads(CANDS.read_text(encoding="utf-8"))
    criteria = {c.id: c for c in
                discover_rubrics(str(ROOT / "rubrics"))["football/instep_shot"].criteria}
    for slot in data["slots"]:
        criterion = criteria[slot["criterion_id"]]
        for c in slot["candidates"]:
            if c["flags"] == ["no_json"]:
                continue
            c["flags"] = auto_flags(c["evidence"], c["metric_ref"], criterion,
                                    slot["grade"], slot["given_metrics"])
    return data


def cmd_sheet() -> None:
    data = load()
    for slot in data["slots"]:
        clean = [(i, c) for i, c in enumerate(slot["candidates"])
                 if not c["flags"]]
        metrics = " · ".join(f"{k}={v}" for k, v in slot["given_metrics"].items())
        print(f"\n### {slot['slot_id']}  ({slot['name']} · {slot['grade']}등급 "
              f"· 값 {slot['value']} · {metrics})")
        print(f"    🎯 코드의 방향: {slot['plain'] or '(없음)'}")
        if not clean:
            print("    (자동 거르기를 통과한 후보 없음)")
            continue
        for i, c in clean:
            print(f"    [{i}] {c['evidence']}")
    print(f"\n자리 {len(data['slots'])}개 · 자동통과 후보 "
          f"{sum(1 for s in data['slots'] for c in s['candidates'] if not c['flags'])}개")


def cmd_apply(picks_path: Path) -> None:
    data = load()
    picks = json.loads(picks_path.read_text(encoding="utf-8"))
    rubric = discover_rubrics(str(ROOT / "rubrics"))["football/instep_shot"]
    criteria = {c.id: c for c in rubric.criteria}

    accepted, rejected, rows = [], [], []
    for slot in data["slots"]:
        chosen = set(picks.get(slot["slot_id"], []))
        for i, c in enumerate(slot["candidates"]):
            if c["flags"]:
                continue  # 코드가 이미 버린 것 — 사람 판정 대상이 아니다
            entry = {"slot_id": slot["slot_id"], "index": i,
                     "evidence": c["evidence"], "metric_ref": c["metric_ref"],
                     "grade": slot["grade"], "value": slot["value"],
                     "name": slot["name"], "plain": slot["plain"]}
            (accepted if i in chosen else rejected).append(entry)

        criterion = criteria[slot["criterion_id"]]
        for i in sorted(chosen):
            c = slot["candidates"][i]
            messages = [
                {"role": "system", "content": system_prompt(rubric.sport)},
                {"role": "user", "content": build_prompt(
                    criterion, slot["given_metrics"], slot["grade"])},
            ]
            answer = json.dumps({"evidence": c["evidence"],
                                 "metric_ref": c["metric_ref"]},
                                ensure_ascii=False)
            rows.append({"messages": messages + [
                {"role": "assistant", "content": answer}]})

    (HERE / "sft.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8")
    (HERE / "labels.json").write_text(json.dumps(
        {"accepted": accepted, "rejected": rejected}, ensure_ascii=False,
        indent=2), encoding="utf-8")

    rng = random.Random(SPOT_SEED)
    sample = ([("고름", e) for e in rng.sample(
                   accepted, min(SPOT_ACCEPTED, len(accepted)))]
              + [("버림", e) for e in rng.sample(
                   rejected, min(SPOT_REJECTED, len(rejected)))])
    rng.shuffle(sample)
    lines = [
        "# 점검 30개 — 제 선별이 맞는지만 봐 주십시오",
        "",
        "각 칸은 **「코드가 말하는 방향」과 문장이 같은 방향인가**만 묻습니다.",
        "문장이 예쁜지·자연스러운지는 여기서 안 봅니다.",
        "",
        "🔴 **동의하지 않는 번호만** 알려 주시면 됩니다 (예: `3, 11, 24`).",
        "",
    ]
    for n, (verdict, e) in enumerate(sample, 1):
        lines += [
            f"### {n}. {e['name']} · {e['grade']}등급 · 값 {e['value']}",
            f"- 코드의 방향: **{e['plain'] or '(없음)'}**",
            f"- 문장: {e['evidence']}",
            f"- 제 판정: **{verdict}**",
            "",
        ]
    (HERE / "SPOTCHECK.md").write_text("\n".join(lines), encoding="utf-8")
    (HERE / "spotcheck_sample.json").write_text(json.dumps(
        [{"n": n, "verdict": v, **e} for n, (v, e) in enumerate(sample, 1)],
        ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"고름 {len(accepted)} · 버림 {len(rejected)} · 학습 예시 {len(rows)}")
    print(f"→ sft.jsonl · labels.json · SPOTCHECK.md ({len(sample)}개)")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sheet")
    a = sub.add_parser("apply")
    a.add_argument("--picks", required=True)
    args = ap.parse_args()
    if args.cmd == "sheet":
        cmd_sheet()
    else:
        cmd_apply(Path(args.picks) if Path(args.picks).is_absolute()
                  else HERE / args.picks)


if __name__ == "__main__":
    main()
