# Super-Sub 자세 분석 에이전트

[시스템 설계 3)·4)절](https://github.com/pmhllll12/supersub.parkminho.cloud)의 구현체.
설계 원칙은 **측정과 판단의 분리**다.

| 단계 | 담당 | 모듈 |
|---|---|---|
| 측정 | 결정론적 코드 | `pose.py` → `features.py` |
| 등급 판정 | 결정론적 코드 | `scoring.Criterion.grade_for` |
| 근거 문장 | EXAONE (언어 모델) | `judge.py` |
| 합산 | 결정론적 코드 | `scoring.aggregate` |

언어 모델은 수치를 **생성하지 않고 등급도 정하지 않는다.** 루브릭의 등급 정의가
이미 수치 구간(`bands`)이므로 판정에 추론이 필요 없다. 모델의 몫은 확정된 등급에
대해 선수에게 보여줄 근거 문장을 쓰는 것뿐이다.

등급 판정을 코드로 내린 것은 실측 때문이다. EXAONE 4.0 1.2B는 무릎각 141.7도가
2등급 기준 140~165도 **안**이라는 비교를 틀렸고, 3회 반복 모두 같은 오답이었다.
스키마 필드 순서를 조정해 추론 필드(`comparison`)를 넣는 튜닝으로도 경계값은
고쳐지지 않았다. 소형 모델에 맡길 수 없는 종류의 판단이다.

## 환경

시스템에 Python 3.14만 있고 MediaPipe·Ollama는 투입자원 목록에 없어,
`uv`로 Python 3.12 환경을 잡고 **OpenCV + Transformers**로만 구성한다.

```bash
cd agent
uv sync
uv run pytest tests/ -q
```

### scipy는 선택 의존성이 아니다

transformers의 ViTPose 전처리기는 히트맵을 원본 좌표로 되돌릴 때
`scipy.ndimage.affine_transform`을 쓴다. 그런데 이 임포트가
`is_scipy_available()`로 감싸져 있어, scipy가 없으면 임포트는 조용히 넘어가고
**실행 시점에** `NameError: name 'affine_transform' is not defined`가 난다.
합성 키포인트만 쓰는 테스트로는 잡히지 않고 실제 영상을 넣어야 드러난다.

### torch는 cu126 빌드로 고정

WSL2 GPU 드라이버가 CUDA 12.6(560.94)이라 기본 PyPI 휠(cu130)은
`CUDA initialization: The NVIDIA driver on your system is too old`로 GPU를
인식하지 못한다. `pyproject.toml`의 `[tool.uv.index]`가 cu126 휠을 가리킨다.
드라이버를 올릴 수 없는 환경(WSL2는 Windows 호스트 드라이버를 따름)에서는
이쪽을 고정하는 것이 맞다.

### 판정 모델은 EXAONE 4.0 1.2B (네이티브)

EXAONE 3.5는 `trust_remote_code`로 자체 모델링 코드를 싣는데, 그 코드가 특정
transformers 버전 창에만 맞는다 — 4.x에서는 `RopeParameters` import 실패,
5.15에서는 `create_causal_mask()`의 인자명이 `input_embeds`→`inputs_embeds`로
바뀌어 `TypeError`가 난다. 팀 전원이 재현해야 하는 환경에서 상류 변경에 깨지는
경로는 피한다.

**EXAONE 4.0/4.5는 transformers에 네이티브 통합**되어 원격 코드가 필요 없다.
8GB에 들어가면서 네이티브인 것은 4.0 1.2B뿐이라 이것을 기본값으로 둔다
(`judge.MODELS`). 3.5 계열은 항목으로 남겨 두었으나 쓰려면 버전 고정이 필요하다.

## 지원 범위

채점 기준은 **(종목, 동작) 단위**로만 쓸 수 있다. 같은 지표가 동작에 따라
반대로 채점되기 때문이다 — 임팩트 시 무릎각 176도는 인스텝 슈팅에서 1등급,
인사이드 패스에서는 0등급("패스가 아니라 슈팅 궤적")이다. 농구는 더 분명해서
점프슛은 `extension_peak`, 레이업은 `distal_apex`로 임팩트로 삼는 프레임
자체가 다르다. "축구용 루브릭 하나"는 성립하지 않는다.

지금 여는 범위는 **종목당 한 동작**이다. 동작을 하나 여는 실제 비용은 YAML
작성이 아니라 임계값 실측·지도자 검수·검증 클립 확보이며, 열린 동작이 늘면
검수 대상이 그만큼 늘어난다.

| 루브릭 | status | 검수 | 실클립 |
|---|---|---|---|
| 축구 인스텝 슈팅 | active | 전 | 통과 |
| 야구 투구 | active | 전 | 미확인 |
| 농구 점프슛 | active | 전 | 미확인 |
| 축구 인사이드 패스 | draft | 전 | 미확인 |
| 농구 레이업 | draft | 전 | 통과 |

`status`는 **범위**(지금 여는 동작인가), `review_required`는 **검수**(임계값이
확정됐는가)로 축이 다르다. 위 표처럼 열려 있으면서 검수 전일 수 있다(결과에
`provisional`로 표기된다). draft는 `/api/rubrics` 목록에서 빠지지만 키를 직접
주면 분석은 되므로, 검수·실측은 UI를 열지 않고도 돌릴 수 있다. 계약 테스트는
draft도 포함해 돌기 때문에, 닫혀 있는 동안 파이프라인이 바뀌어 지표가 어긋나면
여는 시점이 아니라 그때 걸린다.

## 구성

```
agent/
├── rubrics/                        # 채점 기준 + bands(등급 구간) + titles(칭호)
│   ├── football_instep_shot.yaml   # active — 종목당 한 동작만 연다
│   ├── baseball_pitching.yaml      # active
│   ├── basketball_jump_shot.yaml   # active
│   ├── football_inside_pass.yaml   # draft — 검수 대기, 선택지에 안 뜬다
│   └── basketball_layup.yaml       # draft
├── src/supersub_agent/
│   ├── pose.py       # OpenCV 디코딩 + RT-DETR 검출 + ViTPose 추정
│   ├── features.py   # 정규화 → 구간 분할 → 채점 지표 산출
│   ├── judge.py      # EXAONE 근거 문장 생성 (bf16, 스키마 강제)
│   ├── scoring.py    # 루브릭 적재 + 등급 구간 판정 + 가중합
│   └── api.py        # 로컬 확인용 FastAPI + 웹 UI
├── scripts/
│   ├── spike_exaone.py  # 8GB 적재·속도·스키마 강제 검증
│   ├── analyze.py       # CLI 단건 분석
│   └── demo.py          # 재현성 반복 실행
└── tests/
```

### 로컬 확인용 웹 UI

```bash
uv run uvicorn supersub_agent.api:app --host 0.0.0.0 --port 8000
```

합성 데이터 실행([B]~[D] 구간)과 영상 업로드 실행([A] 포함) 두 경로를 제공한다.
화면에는 **칭호와 장단점만** 보인다 — 루브릭이 검수 전이라 점수가 provisional이고,
칭호가 선수 카드에 쓸 산출물이기 때문이다. 총점·배점·측정값은 접힌 영역에 둔다.

인증·동시성·작업 큐가 없으므로 확인용으로만 쓴다 — 정식 구성은 비동기 잡
(`analysis_job`) + WebSocket 진행률이다.

## 8GB VRAM 제약

RTX 3050(8192 MiB, 실사용 가능 약 7.4GB)에서 동작시키기 위한 제약:

- **비전 모델을 쓰지 않는다.** EXAONE 계열 VL은 4.5의 33B뿐이라 적재 불가.
  판정은 수치만으로 한다 — 그래서 `features.py`가 뽑는 지표 범위가 중요하다.
- **포즈 모델과 판정 모델을 동시에 올리지 않는다.** `pose.py`는 추출이 끝나면
  모델을 해제하고 `torch.cuda.empty_cache()`를 호출한다.
- **판정 모델은 양자화하지 않는다.** 1.2B는 bf16으로도 2.4GB뿐이고, 4bit는
  bitsandbytes 역양자화 오버헤드로 적재 44.2초/11.5 tok/s — bf16의 7.5초/24.4
  tok/s보다 느리다. `Judge(quantize=True)`는 더 큰 모델을 쓸 때만 켠다.

두 모델이 겹치지 않으므로 최대 점유는 판정 모델 쪽 2.4GB다. 8GB에 5GB 이상
여유가 남아 모델 규모를 올릴 여지가 있다 (미결 항목 4번).

## 설계상 중요한 계약

**루브릭의 `measured_by`와 `features.py`의 출력 키는 일치해야 한다.**
불일치하면 판정 단계에서 근거 지표를 찾지 못한다.
`test_pipeline_covers_every_rubric_metric`이 이 계약을 검사한다
(실제로 초안 작성 중 `swing_knee_angular_velocity_peak` 오타를 이 테스트가 잡았다.
그 지표 자체는 이후 제거됐다 — 아래 참고).

**측정되지 않은 항목은 판정하지 않는다.** `judge.select_metrics`가 해당 항목의
`measured_by` 값만 골라 프롬프트에 넣는다. 전체 측정값을 주면 모델이 관련 없는
수치를 근거로 끌어다 쓴다.

**모든 항목에 `bands`가 있어야 하고, `bands.metric`은 `measured_by`에 속해야
한다.** 등급을 코드가 판정하므로 구간 정의가 없으면 채점 자체가 불가능하다.
`load_rubric`이 적재 시점에 막는다. 구간은 양끝을 포함하며 2 → 1 → 0 순으로
먼저 맞는 등급을 취한다 — 경계값(150 등)은 높은 등급으로 간다. 산문 기준만
있을 때 모호했던 지점이라 코드로 내리면서 규칙을 명시했다.

**검출 실패 프레임은 지표 계산에서 배제한다.** `pose.py`는 사람이 검출되지 않은
프레임을 `zeros((17,3))`으로 채우고, 그 프레임의 관절각은 `joint_angle`이 NaN을
낸다. `np.argmax`는 NaN을 최대값으로 취급하므로 마스킹하지 않으면 임팩트가 항상
첫 검출 실패 프레임으로 잡힌다 — 실클립(앞 11프레임 미검출)에서 실제로 발생해
"동작 전후가 잘린 영상"이라는 오진을 냈다. `features._peak_frame`이 후보를
유효 프레임으로 한정한다.

## 현재 상태

- [x] 점수 합산 + 등급 구간 판정 (`scoring.py`)
- [x] 특징 추출 (`features.py`)
- [x] 루브릭 초안 (축구 인스텝 슈팅, 5개 항목 + bands + titles)
- [x] EXAONE 적재·속도 실측 (4bit vs bf16 → bf16 채택)
- [x] 등급 판정을 코드로 이관 — 경계값 오판(141.7 → 0등급) 해소
- [x] FastAPI 래핑 (`api.py`) — 합성/영상 두 경로, 로컬 확인용 UI
- [x] **실클립 전 구간 통과** — 4K 25fps 10.2초 클립 (2026-08-25)
- [ ] 지도자 라벨링 골든셋 (QWK 측정용)
- [ ] MySQL 적재 (`analysis_metric_value`)

테스트 30개 (`uv run pytest tests/ -q`).

### 측정 실적

RTX 3050(8192 MiB), 실클립 3840×2160 25fps 10.2초(255프레임) → 128프레임.

`read_frames`는 `step = round(src_fps / target_fps)`로 정수 간격을 잡으므로
25fps에 target 15를 주면 `round(1.67) = 2`, 즉 실효 **12.5fps**가 된다.
`PoseResult.sampled_fps`에는 목표값이 아니라 이 실효값이 담긴다 — 프레임 인덱스를
시각으로 환산할 때 쓰는 값이므로(`frame_to_seconds`) 목표값을 담으면 20% 어긋난다.
이 클립의 임팩트 44번 프레임은 3.52초 지점이다.

| 단계 | 시간 | 비고 |
|---|---|---|
| [A] 포즈 추출 | 33.1초 | 128프레임, peak VRAM 643MB |
| [B] 특징 추출 | 0.00초 | |
| [C] 모델 적재 | 4.6초 | 적재 후 VRAM 2449MB (2.4GB) |
| [C] 판정 5항목 | 18.7초 | 항목당 3.7초. 첫 회는 22.0초 |
| [D] 합산 | 0.0000초 | |

3회 반복 모두 55점 C로 동일하다(결정론). 등급 판정을 코드로 옮기고 `comparison`
필드를 없애면서 판정 시간이 27.0초 → 18.7초로 줄었다 — 모델이 쓸 토큰이 줄어든
결과다. 포즈 추출이 이제 전 구간의 절반 이상을 차지하며, 4K 프레임을 그대로
RT-DETR에 넣는 구조라 해상도를 낮추면 더 줄어들 여지가 있다.

가중치를 지운 상태에서 처음 실행하면 모델 다운로드(약 2.4G)가 추가된다.

## 정의상 측정 불가라 제거한 지표

`swing_knee_angular_velocity_peak_frame_offset`(각속도 피크와 임팩트의 시간차)은
**항상 0이었다.** `segment_phases`가 임팩트를 "무릎 신전 각속도가 최대인 프레임"으로
정의하므로, 같은 시계열에서 잰 피크 시점은 정의상 임팩트와 일치한다. 그런데도
판정 근거로 넘어가 모델이 이 0을 "가속 구간 확보 실패"로 읽었고, 실클립에서
25점 항목이 그 이유로 0점 처리됐다.

지표를 `measured_by`와 `features.py` 산출에서 빼고 루브릭 `deferred`의
`swing_acceleration_timing`으로 옮겼다. 공 검출기가 붙어 임팩트를 발-공 접촉
시점으로 **독립 정의**해야 측정 가능해진다.

## 주의

`rubrics/football_instep_shot.yaml`의 각도 임계값은 **지도자 검수 전 임시값**이다.
`review_required: true`인 동안 `aggregate()`는 결과에 `provisional: true`를 붙인다.
검수 전 점수를 대외에 노출하지 않는다. `titles`(칭호)도 선수에게 보이는 문구이므로
임계값과 함께 검수 대상이다.

EXAONE은 **EXAONE AI Model License 1.2 - NC**로 비상업 라이선스다.
상업적 이용에는 LG AI Research와 별도 계약이 필요하다 (미결 항목 1번).
