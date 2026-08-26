"""루브릭 근거 문장 생성기 (EXAONE).

역할은 하나다: 이미 정해진 등급에 대해 **선수에게 보여줄 근거 문장**을 쓴다.

**등급은 이 모듈이 정하지 않는다.** scoring.Criterion.grade_for가 수치 구간으로
판정한다. 루브릭의 등급 정의가 이미 수치 구간이라 추론이 필요 없고, 소형 모델은
경계값 비교를 틀린다 — EXAONE 4.0 1.2B는 141.7이 140~165 안이라는 판단을
재현되게 틀렸다(3회 반복 동일). 측정과 판단의 분리 원칙을 등급 결정에까지
적용한 결과다.

소형 모델 대응:
  - 항목별 분해 호출 — 루브릭 전체가 아니라 항목 하나씩 처리한다.
  - 근거 지표 격리 — 그 항목의 measured_by에 있는 값만 프롬프트에 넣는다.
    전체 측정값을 주면 관련 없는 수치를 근거로 끌어다 쓴다.
  - 앵커 예시 — 등급별 실제 사례를 문장 작성의 본보기로 넣는다.
  - 그리디 디코딩 — do_sample=False로 재현성을 확보한다.
"""

from __future__ import annotations

import gc
import json
from dataclasses import dataclass, field
from typing import Any

# 스키마에 grade가 없는 것은 의도된 것이다 — 등급은 코드가 정한다.
#
# 예전에는 모델이 등급까지 냈고, 그때는 필드 순서가 정확도를 좌우했다.
# EXAONE 4.0 1.2B 실측 기록으로 남겨 둔다:
#
#   grade 우선                        → 오답
#   evidence → grade 로 순서만 변경    → 오답 (evidence가 수치만 되풀이)
#   comparison(대조 추론) 필드 추가    → 정답
#
# 이 튜닝으로도 경계값(141.7 vs 140)은 계속 틀렸다. 등급 결정을
# scoring.Criterion.grade_for로 옮기면서 comparison 필드는 목적을 잃어 제거했다.
CRITERION_SCHEMA = {
    "type": "object",
    "properties": {
        "evidence": {"type": "string"},
        "metric_ref": {"type": "string"},
    },
    "required": ["evidence", "metric_ref"],
    "additionalProperties": False,
}

SYSTEM_TEMPLATE = """당신은 {sport} 기술 평가관입니다. 항목의 등급은 이미 확정되어
주어집니다. 당신의 일은 그 등급이 왜 나왔는지 선수에게 설명하는 문장을 쓰는 것입니다.

- 주어진 등급을 전제로 씁니다. 등급을 다시 판정하거나 반박하지 않습니다.
- **수치는 주어진 것만 씁니다.** 기준 구간은 이미 문장으로 제공되므로, 숫자를
  새로 만들거나 범위를 넓혀 쓰지 않습니다.
- 측정값이 그 기준의 어디에 위치하는지 짚고, 무엇을 고치면 되는지 한 마디 붙입니다.

출력 필드
- evidence: 근거 문장 1~2개. 예: "임팩트 시 무릎각 141.7도로 2등급 기준
  140~165도 범위의 하단에 있다. 조금 더 펴서 차면 발등 속도가 붙는다."
- metric_ref: 근거가 된 측정값의 이름."""

# 종목 이름이 없으면 종목을 특정하지 않는 표현을 쓴다.
SPORT_NAMES = {"football": "축구", "baseball": "야구", "basketball": "농구"}


def system_prompt(sport: str = "") -> str:
    """종목에 맞는 평가관 프롬프트.

    고정 문구로 두면 야구 결과를 축구 평가관이 쓴다 — 실제로 그랬다.
    """
    return SYSTEM_TEMPLATE.format(sport=SPORT_NAMES.get(sport, "생활체육"))


def band_text(criterion, grade: int) -> str:
    """확정된 등급의 수치 구간을 문장으로 만든다.

    모델에게 구간을 **문장으로 확정해 주는** 자리다. 등급 정의만 주면 모델이
    없는 상한을 지어낸다 — 실클립에서 "40도 이상"인 기준을 "40~165도"라고 써
    선수 화면에 환각 수치가 나갔다.
    """
    parts = []
    for lo, hi in criterion.bands.get(grade, ()):
        if lo is None and hi is None:
            continue
        if lo is None:
            parts.append(f"{hi:g} 이하")
        elif hi is None:
            parts.append(f"{lo:g} 이상")
        else:
            parts.append(f"{lo:g}~{hi:g}")
    return " 또는 ".join(parts) if parts else ""

# transformers 5.15는 EXAONE 4.0/4.5를 네이티브 지원한다(원격 코드 불필요).
# EXAONE 3.5는 trust_remote_code에 의존하는데, 그 원격 코드가
# create_causal_mask(input_embeds=...)를 호출한다 — 현재 시그니처는
# inputs_embeds라 TypeError가 난다. 3.5 계열을 쓰려면 transformers를 특정
# 버전으로 고정해야 하므로, 팀 재현성을 위해 네이티브 모델을 기본값으로 둔다.
MODELS = {
    "1.2B": "LGAI-EXAONE/EXAONE-4.0-1.2B",           # 네이티브, 8GB 적합
    "2.4B": "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct",  # 원격 코드 — 버전 고정 필요
    "7.8B": "LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct",  # 원격 코드 — 버전 고정 필요
}
NATIVE = {"1.2B"}


def build_prompt(criterion, metrics: dict[str, Any], grade: int) -> str:
    """항목 하나에 대한 근거 문장 생성 프롬프트.

    metrics는 이미 criterion.measured_by로 걸러진 것이어야 한다.
    grade는 scoring.Criterion.grade_for가 결정한 값이다 — 모델은 이를 전제로 쓴다.
    """
    lines = [f"평가 항목: {criterion.id} ({criterion.name})"]
    if criterion.rationale:
        lines.append(f"\n항목 취지: {criterion.rationale.strip()}")

    lines.append("\n채점 기준:")
    for g in (2, 1, 0):
        mark = "  ← 확정된 등급" if g == grade else ""
        lines.append(f"- {g}등급: {criterion.grades[g]}{mark}")

    if criterion.anchors:
        lines.append("\n근거 문장 예시:")
        for a in criterion.anchors:
            measured = json.dumps(a["measured"], ensure_ascii=False)
            lines.append(f"- 측정값 {measured} → {a['grade']}등급 ({a['evidence']})")

    lines.append("\n측정값 (이 숫자만 신뢰할 것):")
    lines.append(json.dumps(metrics, ensure_ascii=False, indent=2))
    band = band_text(criterion, grade)
    lines.append(
        f"\n확정된 등급은 {grade}등급입니다. "
        f"{criterion.band_metric}={metrics.get(criterion.band_metric)}가 "
        + (f"{grade}등급 구간({band})에 들어가기 때문입니다."
           if band else f"{grade}등급 기준에 해당하기 때문입니다.")
    )
    if band:
        lines.append(f"이 구간({band}) 외의 수치를 기준으로 인용하지 마세요.")
    lines.append("이 등급에 대한 근거 문장을 JSON으로 출력하세요.")
    return "\n".join(lines)


def select_metrics(criterion, features: dict[str, Any]) -> dict[str, Any]:
    """이 항목의 근거 지표만 골라낸다. 없으면 판정하지 않는다."""
    selected = {k: features[k] for k in criterion.measured_by if k in features}
    missing = set(criterion.measured_by) - features.keys()
    if missing:
        raise ValueError(
            f"{criterion.id}: 근거 지표 누락 {sorted(missing)}. "
            "측정되지 않은 항목은 판정할 수 없다."
        )
    return selected


@dataclass
class Judge:
    """EXAONE 판정기. 8GB에서는 포즈 모델 해제 후 적재한다."""

    model_size: str = "1.2B"
    max_new_tokens: int = 256
    # 8GB에서 1.2B는 양자화가 불필요하다(bf16 2.4GB). 큰 모델을 쓸 때만 켠다.
    quantize: bool = False
    _model: Any = field(default=None, repr=False)
    _tokenizer: Any = field(default=None, repr=False)
    _constrained: Any = field(default=None, repr=False)

    @property
    def model_id(self) -> str:
        return MODELS[self.model_size]

    def load(self) -> None:
        import torch
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
        )

        # 1.2B는 bf16으로도 2.4GB뿐이라 8GB에 여유가 크다. 4bit 양자화는
        # bitsandbytes 역양자화 오버헤드 때문에 작은 모델에서 오히려 손해다.
        # 실측: 4bit는 적재 44.2초/11.5 tok/s, bf16은 7.5초/24.4 tok/s.
        load_kwargs: dict = {
            "device_map": {"": 0} if torch.cuda.is_available() else "cpu"
        }
        if self.quantize:
            load_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
        else:
            load_kwargs["dtype"] = torch.bfloat16

        remote = self.model_size not in NATIVE
        self._tokenizer = AutoTokenizer.from_pretrained(
            self.model_id, trust_remote_code=remote
        )
        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_id, trust_remote_code=remote, **load_kwargs
        )
        self._model.eval()

        # 스키마 강제 백엔드. 실패하면 평문 생성 + 파싱으로 내려간다.
        try:
            import outlines

            self._constrained = outlines.from_transformers(self._model, self._tokenizer)
        except Exception:  # noqa: BLE001
            self._constrained = None

    def unload(self) -> None:
        import torch

        self._model = self._tokenizer = self._constrained = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def judge_criterion(
        self, criterion, features: dict[str, Any], sport: str = ""
    ) -> dict[str, Any]:
        if self._model is None:
            raise RuntimeError("load()를 먼저 호출하세요.")

        metrics = select_metrics(criterion, features)
        # 등급은 코드가 정한다. 모델은 이 등급을 전제로 근거 문장만 쓴다.
        grade = criterion.grade_for(features)
        messages = [
            {"role": "system", "content": system_prompt(sport)},
            {"role": "user", "content": build_prompt(criterion, metrics, grade)},
        ]

        if self._constrained is not None:
            import outlines

            prompt = self._tokenizer.apply_chat_template(
                messages, add_generation_prompt=True, tokenize=False
            )
            raw = self._constrained(
                prompt,
                outlines.json_schema(CRITERION_SCHEMA),
                max_new_tokens=self.max_new_tokens,
            )
            return self._validate(json.loads(raw), criterion, grade)

        return self._validate(self._generate_and_parse(messages), criterion, grade)

    def judge_all(self, rubric, features: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """판정 가능한 항목만 처리한다.

        도구가 검출되지 않으면 그 항목은 빠진다 — aggregate가 남은 항목으로
        가중치를 재정규화한다.
        """
        return {
            c.id: self.judge_criterion(c, features, rubric.sport)
            for c in rubric.applicable_criteria(features)
        }

    # -- 내부 -----------------------------------------------------------
    def _generate_and_parse(self, messages) -> dict[str, Any]:
        """스키마 강제를 못 쓸 때의 대체 경로. 최대 3회 재시도."""
        import torch

        # transformers 5.x는 BatchEncoding을 돌려준다 (4.x의 텐서 반환과 다름).
        enc = self._tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, return_tensors="pt", return_dict=True
        ).to(self._model.device)
        prompt_len = enc["input_ids"].shape[-1]

        last_error = None
        for _ in range(3):
            with torch.inference_mode():
                out = self._model.generate(
                    **enc,
                    max_new_tokens=self.max_new_tokens,
                    do_sample=False,
                    pad_token_id=self._tokenizer.eos_token_id,
                )
            text = self._tokenizer.decode(
                out[0][prompt_len:], skip_special_tokens=True
            )
            start, end = text.find("{"), text.rfind("}")
            if start != -1 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError as exc:
                    last_error = exc
        raise ValueError(f"JSON 파싱 실패: {last_error}")

    @staticmethod
    def _validate(payload: dict[str, Any], criterion, grade: int) -> dict[str, Any]:
        """모델 출력에서 문장만 취한다. 등급은 인자로 받은 값을 그대로 쓴다."""
        metric_ref = str(payload.get("metric_ref", "")) or criterion.band_metric
        if metric_ref not in criterion.measured_by:
            # 모델이 없는 지표 이름을 지어내면 판정 근거로 쓸 수 없다.
            metric_ref = criterion.band_metric
        return {
            "grade": int(grade),
            "evidence": str(payload.get("evidence", "")),
            "metric_ref": metric_ref,
        }
