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
import os
import urllib.error
import urllib.request
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

# vLLM(OpenAI 호환) 서버 주소를 담는 환경변수.
#
# **비어 있으면 지금까지와 똑같이 로컬 transformers로 적재한다.** 이 값이 있을
# 때만 판정이 HTTP로 나간다 — 그래서 api.py·analyze.py를 고치지 않아도 EC2에서만
# vLLM을 쓰고 로컬 WSL 개발은 그대로다.
#
# **인증이 없다.** vLLM OpenAI 서버는 기본적으로 인증을 걸지 않으므로 이 주소는
# 127.0.0.1로 묶어 두고 보안 그룹에서도 열지 않는다 (deploy/README.md 참고).
VLLM_URL_ENV = "SUPERSUB_VLLM_URL"


def extract_json(text: str) -> dict[str, Any] | None:
    """생성 결과에서 첫 JSON 객체를 꺼낸다. 못 꺼내면 None.

    스키마 강제를 못 쓰는 경로(로컬 대체 경로, vLLM guided_json 거부)가 모두
    이 함수를 쓴다 — 두 백엔드가 같은 규약으로 파싱해야 한쪽만 고쳐지지 않는다.
    """
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


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
    """EXAONE 판정기. 8GB에서는 포즈 모델 해제 후 적재한다.

    백엔드가 둘이다. **기본은 로컬 적재**이고, base_url이 있으면 이미 떠 있는
    vLLM 서버로 HTTP 호출한다. 둘의 차이는 문장을 만드는 방법뿐이고 등급은
    어느 쪽에서도 모델이 정하지 않는다 — scoring.Criterion.grade_for가 정한
    값을 _validate가 그대로 싣는다.

    **왜 백엔드를 나눴는가.** T4 16GB EC2에서는 vLLM이 GPU 일부를 상주로 잡고
    있어야 하는데, 그러면 판정 때마다 EXAONE을 적재·해제하는 로컬 경로와
    메모리가 겹친다. vLLM에 맡기면 판정 쪽 GPU 사용이 상수가 되고 남는 자리를
    포즈 모델이 쓴다. 로컬 WSL 개발에서는 vLLM이 없으므로 기존 경로가 기본이다.
    """

    model_size: str = "1.2B"
    max_new_tokens: int = 256
    # 8GB에서 1.2B는 양자화가 불필요하다(bf16 2.4GB). 큰 모델을 쓸 때만 켠다.
    quantize: bool = False
    # vLLM OpenAI 호환 서버 주소 (예: "http://127.0.0.1:8000"). None이면 로컬 적재.
    base_url: str | None = field(
        default_factory=lambda: os.environ.get(VLLM_URL_ENV, "").strip() or None
    )
    # 포즈 추출이 끝난 뒤 항목 수만큼 순차 호출한다. 첫 호출에 모델 워밍업이
    # 겹칠 수 있어 넉넉히 준다.
    request_timeout_s: float = 120.0
    _model: Any = field(default=None, repr=False)
    _tokenizer: Any = field(default=None, repr=False)
    _constrained: Any = field(default=None, repr=False)
    _remote_ready: bool = field(default=False, repr=False)

    @property
    def model_id(self) -> str:
        return MODELS[self.model_size]

    @property
    def backend(self) -> str:
        """실제로 쓰는 백엔드 이름 — 로그·리포트에 남길 값."""
        return "vllm" if self.base_url else "transformers"

    def load(self) -> None:
        if self.base_url:
            self._load_remote()
            return

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

    def _load_remote(self) -> None:
        """vLLM 서버가 살아 있고 **같은 모델을 서빙하는지** 확인한다.

        GPU에는 아무것도 올리지 않는다. 그런데도 load() 시점에 확인하는 이유는,
        여기서 안 하면 연결 실패가 첫 판정 호출에서야 드러나기 때문이다 — 그때는
        이미 포즈 추출에 수십 초를 쓴 뒤다.

        모델 이름까지 보는 것은 vLLM이 로컬 경로로 서빙되기 때문이다. S3에서
        받은 디렉터리로 띄우면 서빙 이름이 그 경로가 되므로, 기동 스크립트가
        --served-model-name으로 MODELS의 값과 맞춰야 한다. 어긋나면 판정 요청이
        404로 떨어지는데, 그 메시지만으로는 원인을 알기 어렵다.
        """
        served = self._served_models()
        if self.model_id not in served:
            raise RuntimeError(
                f"vLLM({self.base_url})이 {self.model_id}를 서빙하지 않는다. "
                f"서빙 중인 이름: {sorted(served) or '없음'}. "
                "기동 스크립트의 --served-model-name을 확인할 것."
            )
        self._remote_ready = True

    def _served_models(self) -> set[str]:
        url = f"{self.base_url.rstrip('/')}/v1/models"
        try:
            with urllib.request.urlopen(url, timeout=10.0) as resp:
                payload = json.loads(resp.read())
        except (urllib.error.URLError, OSError) as exc:
            raise RuntimeError(
                f"vLLM 서버에 연결할 수 없다 ({url}): {exc}. "
                "systemctl status supersub-vllm 으로 기동 상태를 확인할 것."
            ) from exc
        return {str(m.get("id", "")) for m in payload.get("data", [])}

    def unload(self) -> None:
        if self._remote_ready:
            # 서버는 우리 것이 아니다 — 내리지 않는다. 로컬 경로와 호출 규약만
            # 맞춘다(analyze.py가 finally에서 부른다).
            self._remote_ready = False
            return

        import torch

        self._model = self._tokenizer = self._constrained = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def judge_criterion(
        self, criterion, features: dict[str, Any], sport: str = ""
    ) -> dict[str, Any]:
        if self._model is None and not self._remote_ready:
            raise RuntimeError("load()를 먼저 호출하세요.")

        metrics = select_metrics(criterion, features)
        # 등급은 코드가 정한다. 모델은 이 등급을 전제로 근거 문장만 쓴다.
        grade = criterion.grade_for(features)
        messages = [
            {"role": "system", "content": system_prompt(sport)},
            {"role": "user", "content": build_prompt(criterion, metrics, grade)},
        ]

        if self._remote_ready:
            return self._validate(self._generate_remote(messages), criterion, grade)

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

    # -- 내부 (vLLM) ----------------------------------------------------
    def _generate_remote(self, messages) -> dict[str, Any]:
        """vLLM OpenAI 호환 엔드포인트로 근거 문장을 받는다.

        스키마 강제는 guided_json으로 건다 — 로컬 경로가 outlines로 하는 것과
        같은 목적이다. 서버가 그 필드를 모르면(vLLM 버전마다 이름이 다르다)
        **로컬 경로와 같은 규약으로** 평문 파싱에 내려간다.

        temperature=0은 로컬의 do_sample=False에 대응한다. 판정은 재현되어야
        하고, 같은 측정값이 다른 문장을 내면 재현성 확인(analyze.py --repeat)이
        의미를 잃는다.
        """
        body = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": self.max_new_tokens,
            "temperature": 0.0,
        }
        attempts = ({"guided_json": CRITERION_SCHEMA}, {})
        last_error: Exception | None = None
        for extra in attempts:
            try:
                text = self._post_chat({**body, **extra})
            except urllib.error.HTTPError as exc:
                # 스키마 강제를 거부한 것이면 없이 한 번 더 — 그 외에는 그대로 올린다.
                last_error = exc
                if extra and exc.code in (400, 404, 422):
                    continue
                raise RuntimeError(
                    f"vLLM 판정 요청 실패 ({exc.code}): {exc.reason}"
                ) from exc
            parsed = extract_json(text)
            if parsed is not None:
                return parsed
            last_error = ValueError(f"JSON을 찾지 못했다: {text[:200]!r}")
        raise ValueError(f"vLLM 응답 파싱 실패: {last_error}")

    def _post_chat(self, body: dict[str, Any]) -> str:
        req = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.request_timeout_s) as resp:
            payload = json.loads(resp.read())
        return str(payload["choices"][0]["message"]["content"])

    # -- 내부 (로컬) ----------------------------------------------------
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
            parsed = extract_json(text)
            if parsed is not None:
                return parsed
            last_error = ValueError(f"JSON을 찾지 못했다: {text[:200]!r}")
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
