# 종목별 클립 배치 파이프라인

받고 → 재고 → 치우고 → 다음 100개. 저장 위치는 **D드라이브**다.

```bash
uv sync --extra aws                 # boto3 (S3 모드에서만 필요)
uv pip install huggingface_hub      # 이미 깔려 있다 (1.28.0 확인)
huggingface-cli login               # 축구 저장소가 게이트다 (아래 참고)

uv run python -m scripts.dataset_pipeline.run \
  --sport soccer --rubric rubrics/football_instep_shot.yaml \
  --event Shots --batch-size 100 --batches 1 --storage-mode keep
```

## 🔴 먼저 — 명세와 실제가 어긋난 곳

2026-09-04에 세 출처를 **실제로 조회해서** 확인했다. 추측이 아니다.

| 종목 | 명세 | 실제 | 지금 되는가 |
|---|---|---|---|
| ⚽ | SoccerNet **Clips-720p-10s** HF 선택 다운로드 | 그런 저장소가 **없다.** 720p 원본(`SoccerNet_raw_HQ`)은 `gated=manual`에 파일이 안 올라와 있다(NDA). 대안 `SushantGautam/SoccerNet-10s-5Class` — 10초 클립 34,050개가 파일 하나씩이라 **선택 다운로드가 된다.** 🔴 **224p** | **로그인하면 된다** |
| ⚾ | 메타데이터 필터 후 **선택 다운로드** | `hbfreed/Picklebot-130K` 는 있다. 영상이 **단일 28.4GB `tar.xz`** 라 파일 단위 선택 다운로드가 **원리적으로 불가능**하다 | CSV 필터는 **된다**. 영상은 28.4GB를 받아야 한다 |
| 🏀 | PL-NBA pre-trimmed 100개 | HF에 없다. 논문·GitHub은 실재하나 프리트림 클립이 **바이두넷디스크**로만 배포된다 | **자동 불가.** 사람이 받아 둔 폴더를 읽는다 |

카탈로그는 실제로 확인했다 — 축구 27,240건(Shots 5,456 · Goal · Foul · Throw-in ·
Ball out of play), 야구 12,965건(Called Strike 8,240 · Ball 4,725).

## 🔴 그 다음 — 받아도 지표를 믿을 근거가 없다

**세 데이터셋 모두 이 파이프라인이 재려는 것을 재기에 맞지 않는다.** 받는 것과
쓸 만한 것은 다른 문제다.

- **해상도.** 축구 224p · 야구 **224×224**. 우리 경로는 RT-DETR + ViTPose
  top-down 이라 화면 안에서 선수가 작으면 손목·발목을 못 믿는다
- **프레임레이트.** 야구가 **15fps** 다. 우리 동작점은 `DEFAULT_TARGET_FPS=30`
  이고, 미결 7번이 "15fps 에서는 임팩트가 격자에 아예 없는 경우가 많아 측정
  자체가 성립하지 않았다"고 적어 두었다. 클립마다 저fps 경고가 뜬다
- **단위가 다르다.** 셋 다 **이벤트 클립**이다 — 방송 화면, 여러 선수, 카메라
  전환. 우리 루브릭은 **(종목, 동작)** 으로 한 선수의 한 동작을 본다(미결 3번)
- **정답이 없다.** 이벤트·판정 라벨뿐이고 **자세 정답이 아니다.** `/labels/`
  가 정리한 네 층 중 어느 층도 이 데이터로는 안 열린다 →
  **결과를 보고 "정확해졌다"고 쓸 수 없다**
- **라이선스.** PL-NBA 는 **상업적 이용 금지**(연구용 한정), SoccerNet 계열은
  NDA 조건 — 미결 15번과 같은 축이다

🔴 **기존 39클립 평가셋과 섞지 않는다.** B-1~B-6 은 Kinetics 39클립 위의 값이고
여기 결과는 **다른 모집단의 새 측정**이다. 그래서 산출물이
`<root>/<종목>/results/` 에 따로 쌓이고 `agent/eval/` 로 들어가지 않는다.

## 🔴 먼저 이것부터 — 이미 가진 클립이 세 후보보다 낫다

```bash
uv run python -m scripts.dataset_pipeline.run --sport soccer \
  --rubric rubrics/football_instep_shot.yaml \
  --local-dir data/goldenset/soccerkicks_video --batch-size 19 --batches 1
```

2026-09-04 실행: **19건 중 18건 성공**(315초). 1건은 품질 게이트가 "임팩트 추정
프레임(0)이 구간 경계"로 정확하게 반려했다. **공이 15/18에서 검출**됐다.

| 가진 것 | 해상도 · fps |
|---|---|
| `data/goldenset/soccerkicks_video` 19건 | 522×358 ~ **1280×720**, 24~30fps |
| `data/bball_shot.mp4` · `bball_layup_trim.mp4` | **1920×1080**, 24fps |
| `data/baseball_pitch_trim.mp4` | **2160×3840**, 25fps |

전부 **단독 선수 · 단일 동작**이고 게이트도 대용량 다운로드도 필요 없다.
`--local-dir` 은 어느 종목에서나 쓸 수 있다.

## 저장 위치

명세의 `D:/sports_dataset` 을 지금 OS에 맞게 번역한다 — 이 기계는 WSL2라
`/mnt/d/sports_dataset` 이다. 윈도우 경로를 그대로 쓰면 저장소 안에 `D:` 라는
폴더가 생겨 **용량을 D로 빼려던 목적이 뒤집힌다.**

```
/mnt/d/sports_dataset/
  soccer/
    _hf_cache/              HF 캐시도 D드라이브에 둔다 (기본값은 C드라이브)
    clips/batch_0000/       현재 배치 원본
    results/batch_0000.json 지표
    _state.json             진행 커서
  baseball/ …
  basketball/_incoming/     🔴 PL-NBA 를 여기에 직접 넣는다
```

`SPORTS_DATASET_ROOT` 로 바꿀 수 있다. 여유 공간은 확인했다 — **212GB**.

## 정리 방식 (`--storage-mode`)

| | |
|---|---|
| `keep` | 아무것도 안 한다. **기본값** — 지우는 것이 기본이면 처음 돌려 보는 사람이 원본을 잃는다 |
| `delete` | D드라이브에서 지운다 |
| `s3` | S3에 올린 **뒤** 지운다. 🔴 **올리기에 실패하면 안 지운다** |

```bash
uv run python -m scripts.dataset_pipeline.run --sport soccer \
  --rubric rubrics/football_instep_shot.yaml \
  --storage-mode s3 --s3-prefix s3://supersub-ai/datasets/soccer --s3-region ap-northeast-2
```

S3 코드는 새로 쓰지 않고 `supersub_agent.storage` 를 쓴다(boto3 는
`uv sync --extra aws` 로 들어오는 선택 의존성이다). 자격증명은 **인자로 받지
않는다** — boto3 가 표준 순서로 찾는다.

```bash
aws configure                     # ~/.aws/credentials 에 남는다 (권장)
# 또는
export AWS_ACCESS_KEY_ID=...      # 셸 히스토리에 남는 것에 주의
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=ap-northeast-2
```

EC2에서 돌린다면 키를 넣지 말고 **인스턴스 역할**을 쓴다. 다만
`agent/deploy/README.md` 2-A 가 정한 대로 지금 EC2 역할은 `videos/` 에 **읽기
전용**이다 — 이 파이프라인이 쓰려면 쓰기 권한이 있는 **다른 접두사**를 줘야 한다.

## 종목별 실행

```bash
# ⚽ 축구 — huggingface-cli login 필요 (gated=auto, 약관 동의)
--sport soccer --rubric rubrics/football_instep_shot.yaml --event Shots

# ⚾ 야구 — 투구다. baseball_pitching 과 맞는다(타격 루브릭은 없다, 미결 3번)
--sport baseball --rubric rubrics/baseball_pitching.yaml --split val --event "Called Strike"

# 🏀 농구 — 먼저 클립을 <root>/basketball/_incoming/ 에 넣을 것
--sport basketball --rubric rubrics/basketball_jump_shot.yaml
```

🔴 `--rubric` 은 **필수 인자**다. 기본값을 두면 야구 영상이 축구 루브릭으로
조용히 채점된다 — 미결 17번 「하지 말 것」이 지목한 함정이다.

`--stage pose`(기본)는 포즈+지표까지, `--stage full` 은 판정(LLM)까지 간다.
100건에 LLM을 태우면 오래 걸리므로 처음에는 `pose` 로 본다.

## 알아 둘 것

- **커서(`_state.json`)가 "다음 100개"를 기억한다.** 배치를 지우고 나면 디스크
  로는 받은 적이 있는지 알 수 없기 때문이다. 처음부터 다시 하려면 지운다
- **받은 것만** 처리 완료로 적는다. 받기에 실패한 것은 다음에 다시 시도한다
- **파일 이름을 안전하게 줄인다.** SoccerNet 클립 이름은 27,240건 전부 `|` 를
  담고 110자를 넘는다 — NTFS 에서 깨지고 MAX_PATH 에 걸린다. 원래 id 는 커서와
  결과 JSON 이 그대로 들고 있는다
- **`observe=False` 로 포즈를 뽑는다.** 기본값이면 데이터셋 수천 건이 서비스
  입력 관측에 섞여 그 통계가 못 쓰게 된다(미결 12번과 같은 축)
- 야구는 **`prefetch` 로 배치를 한 번에 꺼낸다.** `.tar.xz` 는 랜덤 접근이
  없어서 하나씩 꺼내면 28GB 를 건수만큼 다시 푼다
