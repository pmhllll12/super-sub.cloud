"""EXAONE 8GB 적재 스파이크.

설계 최대 리스크를 검증한다.
  1. RTX 3050 (8GB)에 EXAONE 3.5가 4bit로 적재되는가 — 실제 VRAM 사용량
  2. 생성 속도가 실용 범위인가 — tok/s
  3. JSON 스키마 강제가 동작하는가 — 루브릭 판정 출력 형식

세 항목은 독립적으로 측정한다. 3번이 실패해도 1·2번 결과는 보고한다.

사용:
    uv run python scripts/spike_exaone.py --model 2.4B
    uv run python scripts/spike_exaone.py --model 7.8B
"""

from __future__ import annotations

import argparse
import gc
import json
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

# transformers 5.15는 EXAONE 4.0/4.5를 네이티브 지원한다(원격 코드 불필요).
# EXAONE 3.5는 trust_remote_code에 의존하는데, 그 원격 코드가
# create_causal_mask(input_embeds=...)를 호출한다 — 현재 시그니처는
# inputs_embeds라 TypeError가 난다. 3.5를 쓰려면 transformers를 특정
# 버전으로 고정해야 하므로, 팀 재현성을 위해 네이티브 모델을 우선한다.
MODELS = {
    "1.2B": "LGAI-EXAONE/EXAONE-4.0-1.2B",          # 네이티브 지원, 8GB 적합
    "2.4B": "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct",  # 원격 코드 — 버전 고정 필요
    "7.8B": "LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct",  # 원격 코드 — 버전 고정 필요
}
NATIVE = {"1.2B"}

# 실제 루브릭 판정과 같은 형태의 스키마 — 스파이크 단계부터 최종 출력 형식으로 검증한다.
#
# ⚠️ 필드 순서가 판정 정확도를 바꾼다. 제약 디코딩은 스키마에 적힌 순서대로
#    토큰을 생성하므로, grade를 먼저 두면 모델이 근거를 따져보기 전에 등급부터
#    확정한다. 실측에서 평문 생성은 "171.3도 > 165도 → 1등급"으로 맞췄는데
#    grade-우선 스키마는 0등급을 냈다. evidence → metric_ref → grade 순으로
#    두어 근거를 먼저 쓰게 한다(생성 과정 자체가 추론 역할을 한다).
CRITERION_SCHEMA = {
    "type": "object",
    "properties": {
        "comparison": {"type": "string"},
        "evidence": {"type": "string"},
        "metric_ref": {"type": "string"},
        "grade": {"type": "integer", "enum": [0, 1, 2]},
    },
    "required": ["comparison", "evidence", "metric_ref", "grade"],
    "additionalProperties": False,
}

SYSTEM = (
    "당신은 축구 기술 평가관입니다. 제공된 채점 기준과 측정값에 근거해 항목을 판정합니다.\n\n"
    "출력 필드는 순서대로 작성합니다.\n"
    "- comparison: 측정값이 각 등급 기준에 해당하는지 하나씩 대조한 문장. "
    "예: 'X는 171.3도다. 2등급 기준 140~165도를 벗어난다. "
    "1등급 기준 165도 초과에 해당한다. 따라서 1등급.'\n"
    "- evidence: 판정 근거 요약\n"
    "- metric_ref: 근거가 된 측정값 이름\n"
    "- grade: comparison에서 도출한 등급 (0/1/2)"
)

USER = """평가 항목: knee_over_ball (임팩트 시 무릎 위치)

채점 기준:
- 2등급: 임팩트 순간 무릎각 140~165도
- 1등급: 무릎각 165도 초과(과신전) 또는 130~140도
- 0등급: 무릎각 130도 미만

측정값 (이 숫자만 신뢰할 것):
{"knee_angle_at_impact": 171.3, "impact_frame": 42}

판정을 JSON으로 출력하세요."""


def vram_mb() -> float:
    return torch.cuda.memory_allocated() / 1024**2


def peak_vram_mb() -> float:
    return torch.cuda.max_memory_allocated() / 1024**2


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=list(MODELS), default="1.2B")
    ap.add_argument("--max-new-tokens", type=int, default=200)
    # 1.2B는 bf16으로도 2.4GB뿐이라 8GB에 여유가 크다. 4bit 양자화는
    # bitsandbytes 역양자화 오버헤드 때문에 작은 모델에서 오히려 느리다.
    ap.add_argument("--dtype", choices=["4bit", "bf16"], default="bf16")
    args = ap.parse_args()

    model_id = MODELS[args.model]
    results: dict[str, object] = {"model": model_id, "dtype": args.dtype}

    if not torch.cuda.is_available():
        raise SystemExit("CUDA를 사용할 수 없습니다. GPU 인식 상태를 먼저 확인하세요.")

    total_vram = torch.cuda.get_device_properties(0).total_memory / 1024**2
    print(f"[GPU] {torch.cuda.get_device_name(0)}  총 VRAM {total_vram:.0f} MiB")
    print(f"[모델] {model_id}  ({args.dtype})\n")

    # --- 1. 적재 -------------------------------------------------------
    torch.cuda.reset_peak_memory_stats()

    load_kwargs: dict = {"device_map": {"": 0}}
    if args.dtype == "4bit":
        load_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
    else:
        load_kwargs["dtype"] = torch.bfloat16

    remote = args.model not in NATIVE
    print(f"[코드 경로] {'원격 코드(trust_remote_code)' if remote else '네이티브 지원'}")

    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=remote)
    model = AutoModelForCausalLM.from_pretrained(
        model_id, trust_remote_code=remote, **load_kwargs
    )
    model.eval()
    load_s = time.time() - t0

    results["load_seconds"] = round(load_s, 1)
    results["weights_vram_mb"] = round(vram_mb())
    print(f"[1] 적재 완료  {load_s:.1f}초,  가중치 VRAM {vram_mb():.0f} MiB")

    # --- 2. 생성 속도 --------------------------------------------------
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": USER},
    ]
    # transformers 5.x는 BatchEncoding을 돌려준다 (4.x의 텐서 반환과 다름).
    enc = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True, return_tensors="pt", return_dict=True
    ).to(model.device)
    prompt_len = enc["input_ids"].shape[-1]

    torch.cuda.synchronize()
    t0 = time.time()
    with torch.inference_mode():
        out = model.generate(
            **enc,
            max_new_tokens=args.max_new_tokens,
            do_sample=False,          # temperature 0 상당 — 재현성 확보
            pad_token_id=tokenizer.eos_token_id,
        )
    torch.cuda.synchronize()
    gen_s = time.time() - t0

    new_tokens = out.shape[-1] - prompt_len
    tok_s = new_tokens / gen_s
    text = tokenizer.decode(out[0][prompt_len:], skip_special_tokens=True)

    results["generated_tokens"] = int(new_tokens)
    results["tokens_per_second"] = round(tok_s, 1)
    results["peak_vram_mb"] = round(peak_vram_mb())
    results["vram_headroom_mb"] = round(total_vram - peak_vram_mb())

    print(f"[2] 생성 {new_tokens} 토큰 / {gen_s:.1f}초 = {tok_s:.1f} tok/s")
    print(f"    피크 VRAM {peak_vram_mb():.0f} MiB  (여유 {total_vram - peak_vram_mb():.0f} MiB)")
    print(f"    ── 평문 출력 ──\n{text.strip()[:400]}\n")

    # 스키마 강제 없이도 JSON이 나오는지 (대조군)
    try:
        json.loads(text.strip())
        results["raw_json_valid"] = True
    except json.JSONDecodeError:
        results["raw_json_valid"] = False
    print(f"    스키마 강제 없이 JSON 파싱: {'성공' if results['raw_json_valid'] else '실패'}")

    # --- 3. 스키마 강제 -------------------------------------------------
    print("\n[3] JSON 스키마 강제 검증")
    try:
        import outlines

        gen_model = outlines.from_transformers(model, tokenizer)
        prompt_text = tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=False
        )
        t0 = time.time()
        constrained = gen_model(
            prompt_text,
            outlines.json_schema(CRITERION_SCHEMA),
            max_new_tokens=args.max_new_tokens,
        )
        schema_s = time.time() - t0
        parsed = json.loads(constrained)

        results["schema_enforced"] = True
        results["schema_seconds"] = round(schema_s, 1)
        results["schema_output"] = parsed
        print(f"    성공 ({schema_s:.1f}초): {parsed}")
    except Exception as exc:  # noqa: BLE001 — 스파이크는 실패해도 1·2 결과를 남긴다
        results["schema_enforced"] = False
        results["schema_error"] = f"{type(exc).__name__}: {exc}"
        print(f"    실패: {type(exc).__name__}: {exc}")
        print("    → outlines API 불일치 가능. lm-format-enforcer 또는 "
              "LogitsProcessor 직접 구현으로 대체 검토.")

    # --- 결과 요약 ------------------------------------------------------
    print("\n" + "=" * 60)
    print(json.dumps(results, ensure_ascii=False, indent=2))

    out_path = f"out/spike_{args.model}_{args.dtype}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {out_path}")

    del model
    gc.collect()
    torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
