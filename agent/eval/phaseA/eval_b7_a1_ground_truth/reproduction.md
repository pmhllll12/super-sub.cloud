# 재현 가능성 — 무엇이 남아 있고 무엇이 없는가

> **상태 — B-7 미결 5번: CLOSED · A-1: REVERTED · 재검증: 정답 확보까지 보류**
> 아카이브의 성격과 경계는 `README.md`를 먼저 읽을 것.

2026-09-02 조사. **결론부터: A-1 조사의 원본 분석 스크립트는 하나도 복구되지
않았다.** 아래는 어디를 어떻게 찾았는지와, 그럼에도 남아 있는 것들이다.

## 1. 복구 시도와 결과

되돌림 커밋 `1eb76ad`는 문서 전용이었으므로, 스크립트가 다른 경로에 남아
있는지 찾았다. **production code는 건드리지 않았고 새 데이터도 받지 않았다.**

| 찾은 곳 | 방법 | 결과 |
|---|---|---|
| git 객체 | `git fsck --lost-found` | **dangling 객체 0건** |
| git stash | `git stash list` | **비어 있음** |
| git 히스토리 | 커밋되었다 지워진 파일 탐색 | **해당 없음** — 애초에 커밋된 적 없음 |
| 스크래치패드 | `/tmp/claude-1000/…` | **소실.** 오늘(09-02) 세션 디렉터리 하나뿐. tmpfs라 재부팅에 지워졌다 |
| 셸 히스토리 | `~/.bash_history` | **흔적 없음.** 당시 명령은 에이전트가 실행해 bash_history에 남지 않는다 |
| 접촉 참조 도출 | `grep -rlnE "contact_frame\|공-발목\|ball.*ankle"` (eval/, src/) | **없음** |
| 임팩트 분석 | `grep -rln "extension_peak" eval/` | 다른 조사 것만 (아래) |
| `eval/phaseA/soccer_check.py` | 내용 확인 | **무관.** B-1 시기의 다인 프레임 후보 점검이고 RT-DETR/GPU가 필요하다 |
| `eval/phaseA/phaseA_pose.csv` | 컬럼 확인 | **`contact_frame` 컬럼 없음** (`rp_peak_frame`은 다른 지표) |

`grep`에 걸린 `analyze_phaseA.py`, `eval_b6/selector_downstream.py`,
`pending7_fps/step*.py`는 전부 **다른 조사(Phase A, B-6, 미결 7번)의
산출물**이며 A-1 분석 스크립트가 아니다.

### 따라서

`historical_findings.md`에서 ❌로 표시된 모든 수치는
**"역사적 결과 — 원본 스크립트 미보존"** 이다. 값이 틀렸다는 뜻이 아니라,
**지금 이 저장소만으로는 그 값을 다시 만들 수 없다**는 뜻이다.

`scripts/` 디렉터리를 만들지 않은 이유가 이것이다. 없는 계산을 재현한다고
주장하는 스크립트를 새로 지어내면, 다음 사람이 그것을 원본으로 오인한다.

## 2. 그래도 남아 있는 것

### 입력 데이터 (로컬에만 있음)

`agent/data/`는 `.gitignore` 대상이라 **저장소에 없고 이 기계에만 있다.**

| 경로 | 내용 |
|---|---|
| `data/goldenset/pitchermotion/Pitcher_Motion_Data.csv` | PitcherMotion 원본 (3,444클립의 출처) |
| `data/goldenset/soccerkicks_video/*.avi` | 축구 킥 클립 — 축구 참조 16건의 출처 |
| `data/goldenset/soccerkicks/` | 축구 렌더 자산 |
| `data/goldenset/basketball/`, `vru_sample/` | 농구 쪽 입력 |
| `data/pending7_fps/pm_clips.npz` | PitcherMotion → `(T,17,3)` 파생 캐시 |

### 재사용 가능한 코드 (저장소에 있음)

A-1 분석 자체는 아니지만, **재개할 때 바닥부터 짤 필요는 없게 해 주는 것들**이다.

| 파일 | 쓸모 |
|---|---|
| `eval/pending7_fps/core.py` | 경로 상수, `supersub_agent` import 처리, 임계값 임시 변경 컨텍스트 매니저 |
| `eval/pending7_fps/load_pm.py` | PitcherMotion CSV → 클립별 `(T,17,3)` 배열. COCO-17 × (x,y,conf) 매핑이 검증되어 있다 |
| `eval/pending7_fps/methods.py` | 조사용 공통 계산 |
| `eval/phaseA/PRESERVED_ASSETS.md` | 39클립 `candidates/`·`cache/` 보존 자산 명세 |

`core.py`에는 **`LIMB_MIN_CONFIDENCE["arm"]`을 0.6 → 0.5로 임시 변경하는
컨텍스트 매니저**가 있다. PitcherMotion이 KAPAO의 **검열된 신뢰도**(0과 0.5
사이 값이 존재하지 않음)를 주기 때문이다. A-1 조사도 같은 입력을 썼으므로
재개 시 이 함정을 다시 밟지 않도록 `core.py`의 경고 주석을 먼저 읽을 것.

## 3. 재현에 없는 것

정답 부재와는 별개로, 아래가 없어서 ❌ 수치들이 재계산되지 않는다.

- 오염 잔차(85배)·과잉 제거(1.7%)를 계산한 스크립트
- 결측 위치 분포와 이항검정 p=0.0017 / KS 검정을 낸 스크립트
- 손목 최대속도 proxy 거리 분포를 낸 스크립트
- A-1 적용/미적용 두 조건의 임팩트 프레임을 비교한 실행 하네스
- 축구 `contact_frame` 참조를 공-발목 최근접에서 도출한 스크립트와 그 산출 파일
- 위 실행들의 로그·중간 산출물

## 4. 재개할 때 필요한 것

🔭 `README.md`의 재개 조건이 먼저다 — **팔 종목 릴리스 프레임 정답
25\~60클립, 30fps 이상, 릴리스가 화면에 관측 가능.** 확보 경로는 자체 촬영.

그 정답이 생긴 뒤라면 이 저장소만으로 다음이 가능하다.

1. `load_pm.py`로 PitcherMotion을 다시 클립 배열로 만든다 (CSV가 로컬에 있는 한)
2. `core.py`의 임계값 컨텍스트 매니저로 KAPAO 신뢰도 문제를 처리한다
3. 새 정답에 대해 현재 production 경로의 임팩트 오차를 잰다 — **이것이 기준선이다**
4. 그 다음에야 A-1 계열 변경이나 갭 경계 단측 차분을 **정답 대비로** 평가할 수 있다

3번이 먼저다. 정답 없이 A-1을 다시 켜 보는 것은 2026-08-31에 이미 한 일이고,
그때 판정 불가로 끝났다.

## 5. 이 문서가 하지 않는 것

- A-1의 KEEP/NARROW/REVERT 판단을 다시 하지 않는다 — **REVERT로 확정됐다**
- 단측 차분을 구현하지 않는다
- proxy를 정답으로 승격하지 않는다
- 미결 5번을 재개하지 않는다
