# 사전 등록 — 경로 리팩터를 **실제로 돌려서** 검증한다 (미결 14번의 남은 한계)

작성 2026.09.11 · 담당 정상호 · 🔴 **실행 전에 커밋한다**

## 왜 있는가

미결 14번(`/mnt/d` 하드코딩 56곳 → 7곳, 커밋 `3f3205d`)은 **돌려 보지 않고**
닫았다. 항목에 그 한계를 그대로 적어 두었다:

> 🔴 **남은 한계는 여전히 「돌려 보지 않았다」는 것**이다 — 무거운 9개는
> GPU·외부 자산이 있어야 돈다.

이 회차는 그 한 줄을 지우는 것이 목적이다. **바꾸는 것은 없다** — 조사 회차라
`src/`도 `eval/`의 로직도 고치지 않는다.

## 어디서 도는가 — EC2 가 아니라 로컬이다

2026.09.11에 GPU 인스턴스를 켜고 확인했더니 **거기에는 외부 자산이 없다**
(`clips/`·`labeling/` 없음, 저장소 사본 33MB뿐). 자산과 GPU 가 **둘 다 있는
기계는 이 로컬**이다(RTX 3050 8GB · `torch 2.8.0+cu126` CUDA ✅, 포즈 단독 피크는
903MiB 로 이미 측정돼 있다). 그래서 로컬에서 돈다.

## 🔴 보존 자산을 건드리지 않는 방법

`candidates.py`·`extract.py` 는 **`external_root()` 아래에 쓴다**
(`ROOT/"candidates"`, `ROOT/"cache"`, `ROOT/"frames"`). 그래서 원본 위에 덮지
않으려면 **뿌리를 옮기면 된다** — 리팩터가 만든 바로 그 손잡이를 쓰는 셈이라,
검증 방법 자체가 검증 대상을 한 번 더 쓴다.

```
SUPERSUB_PHASEA_ROOT=<재실행 루트>
  clips      -> 심볼릭 링크 (/mnt/d/supersub-phaseA/clips, 읽기만)
  labeling   -> 심볼릭 링크
  ann        -> 심볼릭 링크
  candidates/  cache/  frames/   ← 빈 디렉터리. 산출물은 여기로 떨어진다
```

**둘 다 `if 산출물.exists(): skip` 이라** 빈 디렉터리로 시작해야 실제로 돈다
(빈 채로 두지 않으면 「돌았다」가 아니라 「건너뛰었다」가 된다).

## 무엇을 돌리는가

모델(RT-DETR·ViTPose)을 쓰거나 `external_root()` 의 큰 자산을 읽는 것들이다.

| | 스크립트 | 무엇이 필요한가 |
|---|---|---|
| 1 | `phaseA/candidates.py` | RT-DETR · `clips/` |
| 2 | `phaseA/extract.py` | production 포즈 경로 · `clips/` |
| 3 | `phaseA/eval_selectors.py` | 포즈 · 캐시 |
| 4 | `phaseA/soccer_check.py` | 포즈 |
| 5 | `phaseA/other_sports.py` | 포즈 |
| 6 | `phaseA/eval_b2/other_sports.py` | 포즈 |
| 7 | `phaseA/eval_b2/pose_quality.py` | 포즈 · 캐시 |
| 8 | `phaseA/eval_b2/render_soccer_diffs.py` | 포즈 · `clips/` |
| 9 | `phaseA/labeling/render_targets.py` | `clips/` · `labeling/` |

## 합격 기준 — **결과를 보기 전에 고정한다**

| | 기준 |
|---|---|
| **A** | 위 9개가 **예외 없이 끝까지** 돈다(exit 0). 실패하면 B~E 와 무관하게 그 건은 불합격이고 사유를 적는다 |
| **B** | `candidates.py` 재산출 39개 `.npz` 가 보존 사본 `candidates_target30/` 과 **배열 단위로 동일**(모든 키에 대해 `np.array_equal`, dtype·shape 포함) |
| **C** | `extract.py` 재산출 39개 `.npz` 가 `cache_target30/` 과 **배열 단위로 동일** |
| **D** | 실행 전후로 **저장소와 `/mnt/d` 에 쓰기가 0건** — 두 곳의 파일 목록·mtime·크기를 실행 전에 떠 두고 뒤에 대조한다 |
| **E** | 실패가 나오면 **경로 탓인지 이 작업 전부터의 결함인지 가른다** — `git stash` 로 리팩터 전 코드에서 같은 것을 돌려 본다(`clean_review_analysis.py` 의 `KeyError` 가 그렇게 갈린 선례다) |

🔴 **바이트 동일을 기준으로 삼지 않는다.** `np.savez_compressed` 는 zip 항목에
**쓰는 시각**을 넣으므로 내용이 같아도 바이트는 다르다. 이것은 결과를 보고
기준을 무르는 것이 아니라 **계기의 성질이고, 그래서 먼저 적는다**(미결 18번
8·10회차에서 계기가 재려던 것을 재지 않아 두 번 어긋났다).

🔴 **B·C 가 어긋나면 그 자체가 결과다.** 모델 가중치는 커밋으로 고정돼 있고
(`ef59faa`) `read_frames` 는 결정적이라고 적혀 있다 — 달라지면 **그 두 문장 중
하나가 틀린 것**이므로 「경로 리팩터가 깼다」로 성급히 읽지 않고 어느 쪽인지 가른다.

## 이 회차가 **말하지 않는 것**

- **「평가 결과가 맞다」가 아니다.** 같은 입력에서 같은 산출이 나오는지만 본다
- 9개 밖의 스크립트는 import 까지만 확인됐다(2026.09.11, 35개 중 34개 OK ·
  1건은 위 `KeyError` 로 **이 작업 전부터** 나던 것)
- **정답은 필요 없다**
