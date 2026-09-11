# agent/ — 자세 분석 에이전트 (소유: 정상호)

**여기는 진입점이다.** 이 폴더에서만 통하는 관례와 값비싼 실수만 적는다.
저장소 전체 규칙은 루트 `CLAUDE.md`, 설계·환경은 `README.md`에 있다.
**같은 내용을 여기 옮겨 적지 않는다** — 사본은 한쪽만 고쳐진다.

## 시작할 때 — 이 순서로 세 가지

```bash
# 저장소 루트에서
grep -n '담당.*정상호' jekyll/pages/pending.markdown   # 나에게 온 요청
cd agent && uv sync && uv run pytest tests/ -q         # 지금 초록인지
```

🔴 **첫 작업: 미결 `jin` 23번**(`metric_definition` 시드용 지표 코드 목록) —
사용자가 "세션 시작하면 착수" 로 지시했다. `POST /analyses`·`paik` 7번이 이것에
막혀 있다. `## jin` 구역의 23번이다(`## ho` 23번은 근거 문장 표기로 별개).

그리고 **[남은 작업 로드맵](../jekyll/pages/roadmap.markdown)** — 남은 작업의
순서, 재조사하면 안 되는 **닫힌 경로**, 함정, 현재 상수값이 한 장에 있다.
로드맵은 진입점일 뿐이고 **정본은 미결 항목**이다. 둘이 어긋나면 미결 항목이 이긴다.

## 🔴 이 폴더의 일하는 방식 — 정답이 거의 없는 영역이다

아래는 "고쳤다"고 잘못 말하지 않으려고 생긴 규칙이다. 전부 실제로 한 번씩
틀린 뒤에 생겼다.

| | |
|---|---|
| **구현 전 사전 등록** | 합격/불합격을 **수치로 먼저 고정**하고 결과를 보고 바꾸지 않는다. 본보기: `eval/pending7_fps/PREREGISTRATION.md`, `eval/pending23_evidence/PREREGISTRATION.md` |
| **조사와 구현의 분리** | 조사 회차에는 `src/`를 고치지 않는다. 평가 스크립트는 production을 **import만** 한다 |
| **AI 단독 판독은 정답이 아니다** | 부정적 결론("갈리지 않는다")의 근거로는 쓰고, 정답으로는 승격하지 않는다 |
| **"정확해졌다"고 쓰지 않는다** | 정답이 없으면 **달라진 것이지 나아진 것이 아니다.** 동작점을 옮겨 놓고 정확해졌다고 적은 적이 있다(target 30 전환) |
| **닫힌 경로는 재조사하지 않는다** | 로드맵 4절. 이유가 남아 있으면 같은 벽에 다시 부딪히지 않는다 |
| **push는 사람이 시킬 때만** | commit은 자유 |

## 🔴 값비싼 실수 — 여기서만 나는 것들

**(1) `features`를 바꾸면 B-6 재실행을 부른다.** 판정 입력이 달라지므로 그때까지의
평가 결과가 전부 무효가 된다. 형제 블록을 더하는 것(예: `timebase`)은 해당하지
않는다 — 그 구분을 지키면 값싸게 고칠 수 있다.

**(2) 보존 자산을 건드리면 B-2~B-5가 통째로 무효다.** 착수 전에
`eval/phaseA/PRESERVED_ASSETS.md`와 `eval/phaseA/README.md`의 **「수정 금지」**
표를 읽는다. 특히 `eval_b2/eval_b2.py`의 selector 가중치.

**(3) 캐시 이름에 동작점이 들어 있다.** `cache_target15/`와 `cache_target30/`.
그냥 `cache/`로 부르면 섞어 쓰게 되고, 그게 미결 10번의 형태다.

**(4) 코드는 저장소, 데이터는 `/mnt/d`.** 스크립트가 `/mnt/d`의 낡은 모듈을
import해 재매핑이 빠진 채 평가가 돈 적이 있다 — **예외도 경고도 없이 숫자만
달랐다.** 경로는 `eval/phaseA/paths.py`로 모으는 중이다(아직 14곳이 하드코딩이다,
미결 14번).

## 무엇이 무엇을 정하는가

**설계 원칙은 측정과 판단의 분리다.** 언어 모델은 수치를 생성하지 않고 등급도
정하지 않는다 (근거는 `README.md` 첫 절 — 경계값 141.7 vs 140을 재현되게 틀렸다).

| 하는 일 | 누가 | 어디 |
|---|---|---|
| 측정 | 결정론적 코드 | `pose.py` → `features.py` |
| 등급 판정 | 결정론적 코드 | `scoring.Criterion.grade_for` |
| 근거 문장 | EXAONE | `judge.py` |
| 합산·등급 표기 | 결정론적 코드 | `scoring.aggregate` |

- 🔴 **등급 결정을 모델로 되돌리지 않는다.** 닫힌 경로다.
- 🔴 **근거 문장에는 등급이 없다** (2026.09.07~). `evidence`는 자세 서술만 담고
  등급 맥락은 `breakdown[]`의 `title`(칭호)·`band`(구간)가 싣는다. **붙이는
  자리는 `aggregate` 한 곳뿐**이다 — `api.py`에서 또 붙이지 않는다. 문장에서
  등급을 정규식으로 뽑으려 하지 말 것 (미결 23·24번).

## 테스트

```bash
uv run pytest tests/ -q     # 초록이 기본값이다
```

**지워서는 안 되는 검사**가 섞여 있다. 결함을 조용히 되살리지 못하게 두는 것들이라
"관련 없어 보인다"고 지우면 그 결함이 돌아온다.

| 검사 | 막고 있는 것 |
|---|---|
| `test_features.py::test_every_frame_valued_metric_is_declared` | 새 프레임 지표가 초 환산 선언을 빠뜨리는 것 |
| `test_keypoint_source.py::test_left_right_pairs_do_not_cross` | 좌우 관절이 뒤바뀐 채 지나가는 것 |
| `test_observability.py::test_eligible_threshold_matches_the_selector` | 관측 기준과 selector 동작 기준이 갈라지는 것 |
| `test_deploy_paths.py` | vLLM 백엔드가 **다른 모델을 서빙해도** 조용히 판정하는 것 |
| `test_worker.py::test_a_single_video_propagates_its_exit_code` | 실패한 분석이 `succeeded` 로 보고되는 것 (리포트가 없는데 큐는 줄어든다) |
| `test_worker.py::test_the_command_always_names_a_rubric` | 인사이드 패스를 **인스텝 루브릭으로** 채점하는 것 (`--rubric` 기본값이 인스텝이다) |
| `test_worker.py::test_a_sport_we_do_not_support_is_refused_not_guessed` | 축구 아닌 `sport_code` 가 **축구 루브릭으로** 채점되는 것. 백엔드 참조 테이블에는 다른 종목이 남아 있다 (2026.09.11 축구 단일 종목 전환) |
| `test_worker.py::test_the_analysis_child_is_seen_as_busy_by_autostop` | 분석 도중에 인스턴스가 꺼지는 것 (그 작업은 `running` 인 채 남는다) |
| `test_worker.py::test_an_empty_api_base_is_a_config_error` | 백엔드 호스트명이 기본값으로 되살아나 **공개 저장소에 다시 실리는 것** (미결 `jin` 22번) |
| `test_worker.py::test_focus_does_not_change_the_score` | 「집중해서 볼 항목」이 채점 경로에 새어드는 것 — 그러면 **같은 영상의 점수가 사용자 선택에 따라 달라져** 선수끼리 비교가 안 된다 (미결 `paik` 8번) |
| `test_metric_definitions.py::test_every_rubric_metric_is_declared` | 새 루브릭 코드가 시드 정본에 빠진 채 배포되는 것. 에이전트 테스트는 다 통과하고 **실서버 적재에서만** `UNKNOWN_METRIC_CODE` 로 터진다 (미결 `jin` 23번) |

## 남의 영역

계약(`fastapi/`)·화면(`www/`·`flutter/`)을 고쳐야 하면 **그 폴더의 진입점 문서를
먼저 읽고**, 스키마·API 계약이 바뀌면 미결 항목으로 알린다. 루트 `CLAUDE.md`
「코드 폴더는 담당자가 있습니다」 참고.
