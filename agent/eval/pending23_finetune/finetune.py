#!/usr/bin/env python3
"""LoRA SFT 학습과 그 어댑터로 평가셋 돌리기 (사전 등록 6절).

    uv run python eval/pending23_finetune/finetune.py train
    uv run python eval/pending23_finetune/finetune.py infer --adapter adapter.pt

🔴 **`peft`·`trl` 을 쓰지 않는다 (2026-09-18, 시간 때문에).** 어댑터가 60개
선형층에 rank-16 두 장을 더하는 것뿐이라 순수 torch 로 60줄이고, 에이전트
venv 에 학습 의존성을 들이지 않아도 된다(README 5-2 의 torch 깨짐). **대가**:
저장 형식이 peft 가 아니라 **vLLM 에 그대로 못 붙인다.** 채택되면 그때 peft
형식으로 다시 굽는다 — 이 회차는 배포 회차가 아니다(사전 등록 0절).

🔴 **가중치는 `Judge.load()` 가 적재한 것을 그대로 쓴다** — 커밋 해시 고정
(미결 11번)이 그 안에 있어서, 여기서 다시 부르면 고정이 갈라진다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

from generate import EVAL, run_base  # noqa: E402

from supersub_agent.judge import Judge  # noqa: E402
from supersub_agent.scoring import discover_rubrics  # noqa: E402

RANK, LR, EPOCHS, BATCH = 16, 1e-4, 3, 4
TARGETS = ("q_proj", "v_proj")
SEED = 20260918


class LoRALinear(torch.nn.Module):
    """base(x) + B(A(x)) — peft 의 LoRA 와 같은 자리·같은 랭크."""

    def __init__(self, base: torch.nn.Linear, r: int = RANK):
        super().__init__()
        self.base = base
        dev, dt = base.weight.device, base.weight.dtype
        self.A = torch.nn.Parameter(torch.zeros(r, base.in_features,
                                                dtype=dt, device=dev))
        self.B = torch.nn.Parameter(torch.zeros(base.out_features, r,
                                                dtype=dt, device=dev))
        torch.nn.init.normal_(self.A, std=0.02)

    def forward(self, x):  # noqa: D102
        return self.base(x) + torch.nn.functional.linear(
            torch.nn.functional.linear(x, self.A), self.B)


def attach(model) -> dict[str, LoRALinear]:
    """모든 층의 `TARGETS` 를 LoRA 로 감싼다. 이름 → 모듈을 돌려준다."""
    out = {}
    for i, layer in enumerate(model.model.layers):
        for name in TARGETS:
            base = getattr(layer.self_attn, name)
            if isinstance(base, LoRALinear):
                continue
            wrapped = LoRALinear(base)
            setattr(layer.self_attn, name, wrapped)
            out[f"layers.{i}.self_attn.{name}"] = wrapped
    return out


def encode(tokenizer, messages: list[dict]) -> tuple[list[int], list[int]]:
    """프롬프트는 -100 으로 가린다 — **답 부분만** 학습한다."""
    prompt = tokenizer.apply_chat_template(
        messages[:-1], add_generation_prompt=True, tokenize=True)
    full = tokenizer.apply_chat_template(
        messages, add_generation_prompt=False, tokenize=True)
    labels = [-100] * len(prompt) + full[len(prompt):]
    return full, labels


def cmd_train(args) -> None:
    torch.manual_seed(SEED)
    rows = [json.loads(line) for line in
            (HERE / "sft.jsonl").read_text(encoding="utf-8").splitlines() if line]
    judge = Judge()
    judge.load()
    model, tok = judge._model, judge._tokenizer
    for p in model.parameters():
        p.requires_grad_(False)
    adapters = attach(model)
    trainable = [p for m in adapters.values() for p in (m.A, m.B)]
    print(f"예시 {len(rows)}개 · 어댑터 {len(adapters)}개 · "
          f"학습 파라미터 {sum(p.numel() for p in trainable) / 1e6:.1f}M", flush=True)

    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    model.train()
    opt = torch.optim.AdamW(trainable, lr=LR)
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id

    encoded = [encode(tok, r["messages"]) for r in rows]
    step = 0
    for epoch in range(EPOCHS):
        order = torch.randperm(len(encoded)).tolist()
        total = 0.0
        for start in range(0, len(order), BATCH):
            batch = [encoded[i] for i in order[start:start + BATCH]]
            width = max(len(ids) for ids, _ in batch)
            ids = torch.full((len(batch), width), pad, dtype=torch.long)
            lab = torch.full((len(batch), width), -100, dtype=torch.long)
            att = torch.zeros((len(batch), width), dtype=torch.long)
            for r, (seq, labels) in enumerate(batch):
                ids[r, :len(seq)] = torch.tensor(seq)
                lab[r, :len(labels)] = torch.tensor(labels)
                att[r, :len(seq)] = 1
            out = model(input_ids=ids.cuda(), attention_mask=att.cuda(),
                        labels=lab.cuda())
            out.loss.backward()
            opt.step()
            opt.zero_grad(set_to_none=True)
            total += out.loss.item()
            step += 1
        print(f"epoch {epoch + 1}/{EPOCHS} · 평균 손실 "
              f"{total / max(1, (len(order) + BATCH - 1) // BATCH):.4f}", flush=True)

    state = {name: {"A": m.A.detach().cpu(), "B": m.B.detach().cpu()}
             for name, m in adapters.items()}
    dest = HERE / args.out
    torch.save({"base_model": judge.model_id, "rank": RANK,
                "targets": TARGETS, "epochs": EPOCHS, "lr": LR,
                "n_examples": len(rows), "steps": step, "state": state}, dest)
    print(f"→ {dest.relative_to(ROOT)}")


def cmd_infer(args) -> None:
    blob = torch.load(HERE / args.adapter, weights_only=False)
    judge = Judge()
    judge.load()
    if blob["base_model"] != judge.model_id:
        raise SystemExit(f"베이스가 다르다: {blob['base_model']} vs {judge.model_id}")
    adapters = attach(judge._model)
    missing = set(adapters) ^ set(blob["state"])
    if missing:
        raise SystemExit(f"어댑터 자리가 안 맞는다: {sorted(missing)[:3]}")
    for name, m in adapters.items():
        m.A.data.copy_(blob["state"][name]["A"].to(m.A.device, m.A.dtype))
        m.B.data.copy_(blob["state"][name]["B"].to(m.B.device, m.B.dtype))
    judge._model.eval()
    rubric = discover_rubrics(str(ROOT / "rubrics"))[EVAL]
    try:
        payload = run_base(judge, rubric)
    finally:
        judge.unload()
    payload["tag"] = "finetuned_inside_pass"
    payload["adapter"] = args.adapter
    dest = HERE / args.out
    dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    print(f"→ {dest.relative_to(ROOT)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("train")
    t.add_argument("--out", default="adapter.pt")
    i = sub.add_parser("infer")
    i.add_argument("--adapter", default="adapter.pt")
    i.add_argument("--out", default="evidence_finetuned.json")
    args = ap.parse_args()
    (cmd_train if args.cmd == "train" else cmd_infer)(args)


if __name__ == "__main__":
    main()
