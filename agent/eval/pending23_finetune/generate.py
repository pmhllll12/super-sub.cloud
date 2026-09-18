#!/usr/bin/env python3
"""파인튜닝 1회차의 **문장 만들기** — 기준선과 후보를 같은 자리 규칙으로 낸다.

    uv run python eval/pending23_finetune/generate.py --mode base
    uv run python eval/pending23_finetune/generate.py --mode candidates

`base` 는 파인튜닝 **전** 모델로 평가셋(`inside_pass` 38자리)을 그리디로 돌린다
— 사전 등록 3절의 `BASE`. `candidates` 는 학습셋(`instep_shot` 42자리)에서
자리당 12개를 표집한다 (사전 등록 2절).

🔴 **자리 규칙을 다시 쓰지 않는다.** `pending23_evidence/football_evidence.py`
의 `FRACTIONS`·`value_in_band`·`filler` 를 **import 해서** 쓴다. 베껴 놓으면
한쪽만 고쳐져 「같은 자리」가 아니게 된다.

🔴 **`src/` 를 고치지 않는다** — production 을 import 만 한다. 표집
(`do_sample=True`)은 `Judge` 가 열어 주지 않으므로 여기서 모델을 직접 부른다.
그리디 경로(`base`)는 `judge.judge_criterion` 을 **그대로** 쓴다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval/pending23_evidence"))

from football_evidence import FRACTIONS, filler, value_in_band  # noqa: E402

from supersub_agent.judge import (  # noqa: E402
    Judge, build_prompt, extract_json, select_metrics, system_prompt,
)
from supersub_agent.scoring import discover_rubrics  # noqa: E402

TRAIN = "football/instep_shot"
EVAL = "football/inside_pass"

#: 자리당 후보 수 (사전 등록 2절).
N_CANDIDATES = 12
TEMPERATURE = 0.9
TOP_P = 0.95
SEED = 20260918

# 사전 등록된 R1·R2·R3 를 그대로 쓴다 — 여기서 새로 짜지 않는다.
sys.path.insert(0, str(ROOT / "eval/pending23_evidence"))
from check_evidence import RANGE, hallucinated_numbers  # noqa: E402


def slots(rubric):
    """`football_evidence.py` 와 **같은** 자리를 낸다."""
    for criterion in rubric.criteria:
        for grade in (2, 1, 0):
            for seg in range(len(criterion.bands[grade])):
                for frac in FRACTIONS:
                    value = value_in_band(criterion, grade, frac, seg)
                    features = {criterion.band_metric: value}
                    features.update(filler(criterion, grade, value, features))
                    if criterion.grade_for(features) != grade:
                        continue
                    yield criterion, grade, seg, value, features


def auto_flags(text: str, metric_ref: str, criterion, grade: int,
               given: dict) -> list[str]:
    """코드가 가를 수 있는 것만 가른다 (사전 등록 1절 「코드」 줄).

    🔴 **`metric_ref` 를 거르지 않는다 (09:53 정정).** 사전 등록 1절에
    「`metric_ref` 유효」를 적었는데, production 의 `Judge._validate` 는 무효한
    값을 **조용히 `band_metric` 으로 떨어뜨린다.** 그러니 그것으로 후보를
    버리면 **제품이 버리지 않는 것을 버리는** 거르개다 — 실제로 첫 실행에서
    42자리 전부가 여기 걸려 자동통과 0 이 나왔다. **재는 자가 재려는 것을
    재는지부터** 본다(I 회차에서 배운 자리).
    """
    flags = []
    if "등급" in text:
        flags.append("R1")
    if RANGE.search(text):
        flags.append("R2")
    if hallucinated_numbers(text, given):
        flags.append("R3")
    if len(text.strip()) < 12:
        flags.append("too_short")
    for anchor in criterion.anchors:
        body = str(anchor.get("evidence", "")).strip()
        if body and body in text:
            flags.append("anchor_copy")
            break
    return flags


def run_base(judge, rubric) -> dict:
    """파인튜닝 전 기준선 — 제품 경로(그리디) 그대로."""
    items = []
    for criterion, grade, seg, value, features in slots(rubric):
        judged = judge.judge_criterion(criterion, features, rubric.sport)
        items.append({
            "criterion_id": criterion.id, "name": criterion.name,
            "grade": grade, "stored_grade": grade, "segment": seg,
            "value": value,
            "evidence": judged.get("evidence", ""),
            "metric_ref": judged.get("metric_ref", ""),
            "plain": criterion.plain_for(grade, value),
            "given_metrics": select_metrics(criterion, features),
        })
        print(f"  {criterion.id} g{grade} s{seg} {value}: "
              f"{items[-1]['evidence'][:60]}", flush=True)
    return {"tag": "base_inside_pass", "backend": judge.backend,
            "model": judge.model_id, "clips": {EVAL: {
                "score": None, "grade": None, "items": items}}}


def run_candidates(judge, rubric) -> dict:
    import torch

    torch.manual_seed(SEED)
    out_slots = []
    for i, (criterion, grade, seg, value, features) in enumerate(slots(rubric)):
        metrics = select_metrics(criterion, features)
        messages = [
            {"role": "system", "content": system_prompt(rubric.sport)},
            {"role": "user", "content": build_prompt(criterion, metrics, grade)},
        ]
        enc = judge._tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, return_tensors="pt",
            return_dict=True).to(judge._model.device)
        prompt_len = enc["input_ids"].shape[-1]
        with torch.inference_mode():
            gen = judge._model.generate(
                **enc, max_new_tokens=judge.max_new_tokens, do_sample=True,
                temperature=TEMPERATURE, top_p=TOP_P,
                num_return_sequences=N_CANDIDATES,
                pad_token_id=judge._tokenizer.eos_token_id)
        cands = []
        for row in gen:
            raw = judge._tokenizer.decode(row[prompt_len:],
                                          skip_special_tokens=True)
            parsed = extract_json(raw)
            if parsed is None:
                cands.append({"evidence": "", "metric_ref": "",
                              "flags": ["no_json"]})
                continue
            text = str(parsed.get("evidence", "")).strip()
            ref = str(parsed.get("metric_ref", "")) or criterion.band_metric
            cands.append({
                "evidence": text, "metric_ref": ref,
                "flags": auto_flags(text, ref, criterion, grade, metrics)})
        # 같은 문장이 여러 벌 나오면 하나로 — 고를 것이 줄지 않게 중복만 접는다.
        seen, uniq = set(), []
        for c in cands:
            key = re.sub(r"\s+", " ", c["evidence"])
            if key in seen:
                continue
            seen.add(key)
            uniq.append(c)
        clean = [c for c in uniq if not c["flags"]]
        out_slots.append({
            "slot_id": f"{criterion.id}|g{grade}|s{seg}",
            "criterion_id": criterion.id, "name": criterion.name,
            "grade": grade, "segment": seg, "value": value,
            "plain": criterion.plain_for(grade, value),
            "plain_all": criterion.plain_all(grade),
            "given_metrics": metrics,
            "candidates": uniq,
        })
        print(f"  [{i + 1}] {criterion.id} g{grade} s{seg} {value}: "
              f"{len(uniq)}가지 · 자동통과 {len(clean)}", flush=True)
    return {"tag": "candidates_instep", "model": judge.model_id,
            "n_requested": N_CANDIDATES, "temperature": TEMPERATURE,
            "top_p": TOP_P, "seed": SEED, "slots": out_slots}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=("base", "candidates"))
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    rubrics = discover_rubrics(str(ROOT / "rubrics"))
    rubric = rubrics[EVAL if args.mode == "base" else TRAIN]
    judge = Judge()
    print(f"백엔드: {judge.backend} · 모델: {judge.model_id} · "
          f"루브릭: {rubric.sport}", flush=True)
    judge.load()
    try:
        payload = (run_base if args.mode == "base" else run_candidates)(
            judge, rubric)
    finally:
        judge.unload()

    dest = HERE / (args.out or (
        "base_inside_pass.json" if args.mode == "base"
        else "candidates_instep.json"))
    dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    print(f"\n→ {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
