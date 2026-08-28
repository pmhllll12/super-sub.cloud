# Phase B-3 preflight

작업 전 상태 기록. 이 시점까지 어떤 파일도 수정하지 않았다.

## git

| 항목 | 값 |
|---|---|
| HEAD | `5e0a4857f406e4a367a43dced1e24d8db2bf3926` |
| `git status --short` | `?? _posts/2026-08-26-포즈-신뢰도-임계값은-모델에-종속된다.markdown` (untracked 1건) |
| `git diff -- agent/` | 0줄 |
| `git diff --cached -- agent/` | 0줄 |
| rubric (`agent/rubrics/`) | 변경 없음 |
| goldenset (`agent/data/`) | 변경 없음 (gitignore 대상, 읽기만) |

production code / tests / rubric / goldenset 변경: **0**

## 입력 파일 해시

작업 종료 시 동일한지 재확인한다.

| 파일 | sha256 |
|---|---|
| `labeling/labels.json` | `d17f54d8b3e3c44ffb97b89f58f4a5b6f8c6ca8f209ca94d92c9bf8b915e383e` |
| `eval_b2/eval_config.json` | `44ecb8786ef353396043c8d176fb620e8cddccc99960acf303d694f0dea7052d` |
| `eval_b2/pose_quality_config.json` | `2799663794a9c26e98ba8d66747714703e3ac2e91d79fd94ca402b90b7982735` |

## 이번 Phase에서 사용할 입력 파일

읽기 전용으로만 쓴다.

| 파일 | 용도 |
|---|---|
| `labeling/labels.json` | 원본 GT (117건). **수정 금지** |
| `eval_b2/review_cases.csv` | 검수 대상 33건 목록 |
| `eval_b2/review_cases/*.jpg` | 중립 렌더 33장 + 축구 5장 |
| `eval_b2/eval_config.json` | 재평가에 쓸 가중치 (변경 금지) |
| `eval_b2/pose_quality.csv` | 후보별 pose_quality 20,677행 |
| `eval_b2/selector_eval_frames.csv` | B-2 결과 (비교 기준) |
| `eval_b2/other_sports_diffs.csv` | 축구 변경 5프레임 |
| `candidates/*.npz` | 후보 박스 캐시 |

## Step 1 — review case 정합성 검증 결과

| 항목 | 결과 |
|---|---|
| `review_cases.csv` 행 수 | **33** |
| 렌더 이미지 (클립) | **33** |
| 렌더 이미지 (축구) | **5** |
| CSV ↔ 대상 목록 frame 일치 | 전건 일치 |
| CSV ↔ 후보 수 일치 | 전건 일치 |
| box index 범위 초과 | 0건 |
| CSV에 없는 고아 렌더 | 0건 |
| **검증 문제 총계** | **0** |

## Step 2 — 사람 검수 입력 상태

| 항목 | 결과 |
|---|---|
| `human_box_index` 입력됨 | **0 / 33** |
| `human_note` 입력됨 | **0 / 33** |
| `labels_verified.json` 존재 | **아니오** |

**사람 검수 입력이 없다.** 17절의 중단 조건에 해당하므로 Step 3 이후를 진행하지 않는다.

## 발견한 문제 — B-2 입력 폼의 정답 노출

`eval_b2/review_cases.csv`에는 다음 컬럼이 들어 있다.

```
gt_box_index, baseline_box_index, a_box_index, b_box_index,
baseline_correct, a_correct, b_correct, continuity, reason
```

이 파일을 그대로 검수자에게 주면 5절("selector 결과를 사람에게 보여주지 마라")을 위반한다.
렌더 이미지 자체는 중립이지만(모든 후보 동일 색·굵기, index만 표시) 입력 폼이 답을 흘린다.

따라서 B-2 산출물은 **수정하지 않고** 블라인드 입력 폼을 별도로 만들었다:

- `eval_b3/review_input.csv` — 33건. `clip_id, ratio, frame, n_candidates, image, human_box_index, human_note`만 포함
- `eval_b3/soccer_review_input.csv` — 축구 5프레임. 동일 구조
- `eval_b3/ingest_review.py` — 입력 검증 후 취합 (범위·중복·미입력 검사, 실패 시 exit 1)
- `eval_b3/REVIEW_INSTRUCTIONS.md` — 검수자 안내

이 폼에는 GT도, selector 선택도, 정답 여부도 들어 있지 않다.
