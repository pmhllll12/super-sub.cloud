# 분석 워커 인터페이스 (정상호 님께, 2026-09-04)

> **이 문서를 Claude 에게 주실 때**: 이 파일 하나만 주시면 됩니다. 규격의 정본은
> `fastapi/docs/api-contract.md` **3-8절**이고 여기는 **워커를 만드는 쪽에서
> 알아야 할 것**만 추렸습니다.

미결 `ho` 17번(S3 에 영상이 올라와도 분석이 돌지 않는다)의 나머지 절반입니다.
**백엔드 쪽은 2026-09-04 에 냈습니다**(`f7ea780`). 남은 것은 **GPU 인스턴스에서
도는 폴링 루프**이고, 그게 `agent/` 영역이라 넘겨 드립니다.

```
POST /videos ──> analysis_job(queued)          ← 이미 있음
                      │
   워커가 주기적으로 ─┴─> claim   (running 으로)   ← 이미 있음 (백엔드)
                            │ analyze_s3.py         ← 이미 있음 (agent)
                            └─> PATCH  (succeeded|failed)  ← 이미 있음 (백엔드)
                            
                    이 셋을 잇는 루프가 없습니다 ← **여기입니다**
```

---

## 만족해야 할 성질

1. **`queued` 로 남아 있던 작업이 실제로 실행될 것**
2. **끝나면 상태가 옮겨져 있을 것** — `succeeded` 또는 `failed`
3. **실패 사유가 값으로 남을 것** — `failure_reason` 에
4. **인스턴스를 껐다 켜도 밀린 것이 처리될 것** — 큐가 사라지지 않습니다
5. **두 개를 동시에 돌려도 같은 작업을 두 번 하지 않을 것**

🔴 **파일·함수 이름은 예시지 규격이 아닙니다.** 위 성질만 만족하면 어떤 모양이든
괜찮습니다.

---

## 먼저 확인 — 이미 되어 있으면 손대지 않습니다

```bash
# 워커 루프가 이미 있는가
git grep -n "analysis-jobs/claim" -- agent/

# 서버에 폴링 서비스가 도는가
ssh <gpu-instance> 'systemctl list-units --type=service | grep -i worker'
```

결과가 있으면 이미 착수된 것입니다.

---

## 1. 작업 하나 집기

```
POST https://api.supersub-ai.com/api/v1/internal/analysis-jobs/claim
X-Worker-Token: <공유 시크릿>
```

| 응답 | 뜻 |
|---|---|
| **200** | 아래 형태의 작업 하나. 이미 `running` 으로 바뀌어 있습니다 |
| **204** | **큐가 비었습니다. 오류가 아닙니다** — 잠시 쉬었다 다시 부르시면 됩니다 |
| 401 | 토큰이 없거나 틀립니다 |

```json
{
  "job_id": "…", "video_id": "…",
  "storage_key": "videos/<user_id>/<uuid>.mp4",
  "sport_code": "baseball",
  "side": "right",
  "duration_ms": 4200
}
```

- `storage_key` 앞에 `s3://supersub-ai/` 를 붙이면 `analyze_s3.py` 의 첫 인자입니다
- `side` 는 없을 수 있습니다(`null`). 그러면 `--side` 를 주지 마십시오
- 🔴 **`POST` 입니다.** 조회처럼 보여도 이 호출은 작업을 하나 **소비**합니다 —
  실패해서 재시도하면 **다른 작업을 집습니다**(같은 것이 아닙니다)

### 동시에 둘을 돌려도 안전합니다

같은 작업을 두 워커가 집지 않도록 DB 에서 막았습니다(`FOR UPDATE SKIP LOCKED`).
그리고 **먼저 온 쪽이 멈춰 세우지 않습니다** — 두 번째 워커는 다음 것을 집습니다.
`fastapi/tests/analysis/adapter/test_job_db.py` 가 실제 PostgreSQL 로 확인합니다.

---

## 2. 루브릭 고르기 — 🔴 **`status: active` 인 것 하나를 씁니다**

응답에 **동작(motion)이 없습니다.** 담을 자리가 아직 없어서입니다(미결 `jin` 17번).
그래도 **지금은 종목만으로 정해집니다** — 종목당 `active` 가 하나씩이기 때문입니다.

| 종목 | active | draft |
|---|---|---|
| baseball | `baseball_pitching` | — |
| basketball | `basketball_jump_shot` | `basketball_layup` |
| football | `football_instep_shot` | `football_inside_pass` |

`scoring.py` 가 `status` 를 **"사용자에게 내보낼지 여부 — active만 선택지에
오른다"** 로 정의해 두셨고, 이 규칙은 그걸 그대로 따르는 것입니다.

### 규칙

> **그 종목의 `active` 루브릭이 정확히 하나면 그것을 쓴다. 0 개거나 2 개 이상이면
> 실행하지 말고 `failed` 로 보고한다.**

**draft 를 승격시키는 순간 둘이 됩니다.** 그때 조용히 아무거나 고르는 대신 멈추게
하려고 이렇게 씁니다. 미결 `jin` 17번(동작 컬럼)이 풀리면 응답에 `motion` 이
실리고 이 규칙은 필요 없어집니다.

🔴 **`--rubric` 을 생략하지 마십시오.** 기본값이 `football_instep_shot.yaml` 이라
안 주면 **야구·농구 영상을 축구 루브릭으로 채점합니다.** 그리고 그 결과가 틀렸다는
것이 값에 나타나지 않습니다.

---

## 3. 분석 실행

```bash
uv run python scripts/analyze_s3.py \
  s3://supersub-ai/<storage_key> \
  --rubric rubrics/<위에서 고른 것>.yaml \
  --out s3://supersub-ai/reports \
  [--side <side>]
```

---

## 4. 결과 보고

```
PATCH https://api.supersub-ai.com/api/v1/internal/analysis-jobs/<job_id>
X-Worker-Token: <공유 시크릿>

{"status": "succeeded"}
{"status": "failed", "failure_reason": "품질 게이트 미달: …"}
```

`204` 면 됐습니다.

| 에러 | code | 어떻게 해야 하나 |
|---|---|---|
| 404 | `JOB_NOT_FOUND` | 없는 작업입니다. **재시도 무의미** |
| 409 | `JOB_NOT_RUNNING` | 집지 않았거나 이미 끝났습니다. **재시도 무의미** |
| 422 | `INVALID_JOB_STATUS` | `succeeded`·`failed` 만 받습니다 |

**`finished_at` 을 보내지 않습니다.** 서버가 찍습니다 — 워커의 시계가 어긋나면
소요 시간이 음수가 됩니다. `started_at` 도 `claim` 이 찍었습니다.

### 종료 코드 → `failure_reason`

`analyze_s3.py` 를 읽고 지금 확인된 것만 적습니다. **정리해 주신다고 하셨으니
그때 이 표를 고치겠습니다.**

| 종료 코드 | 무엇 | 제안 |
|---|---|---|
| `0` | 정상 | `succeeded` |
| `2` | **품질 게이트 미달**(`InsufficientQuality`) — 사람이 다시 찍어야 풀립니다 | `failed` + 표준출력 마지막 줄(`분석 중단: …`)을 사유로 |
| 그 외 0 아님 | 인자 오류·다운로드 실패·모델 적재 실패 등이 섞여 있습니다 | `failed` + 사유에 종료 코드와 마지막 줄 |

🔴 **사유는 255자로 잘립니다**(`failure_reason` 컬럼). 스택트레이스를 통째로
넣으면 잘려서 정작 원인이 사라집니다 — **마지막 줄만** 넣어 주십시오.

---

## 5. 인증

`X-Worker-Token` 헤더에 공유 시크릿을 넣습니다. **사람 토큰이 아닙니다** — 워커를
사용자 계정에 묶으면 그 계정이 탈퇴하거나 토큰이 폐기될 때 파이프라인이 조용히
멈춥니다.

🔴 **값은 제가 서버에 넣고 따로 전달드립니다.** 저장소에 커밋하지 마십시오.
(백엔드는 `WORKER_TOKEN` 환경변수로 읽습니다. 비어 있으면 **모든 요청이 401**
입니다 — 값을 안 넣은 배포에서 큐가 열려 있는 것보다 멈춰 있는 편이 낫다고 봤습니다.)

---

## 하지 말 것

- 🔴 **`--rubric` 을 생략하지 않기.** 위 2번의 이유입니다
- 🔴 **`claim` 을 `GET` 처럼 재시도하지 않기.** 한 번 부를 때마다 작업 하나가
  `running` 으로 넘어갑니다. 실패해서 다시 부르면 **다른 작업**을 집습니다
- 🔴 **204 를 오류로 다루지 않기.** 큐가 빈 것은 정상이고, 오류로 두면 로그가
  빈 폴링으로 찹니다
- 🔴 **`videos/` 에 쓰지 않기.** 지금 IAM 정책이 읽기 전용인 것이 의도라고
  적어 두셨고(`agent/deploy/README.md` 2-A), 이 설계는 그것을 지킵니다 —
  워커는 `videos/` 읽기와 `reports/` 쓰기만 하면 됩니다
- **폴링을 너무 촘촘히 하지 않기.** 큐가 비어 있을 때가 대부분입니다.
  30~60초면 충분하다고 봅니다 — 인스턴스가 꺼져 있는 동안 쌓인 것은 켜지면
  연달아 처리됩니다

---

## 아직 없는 것 (제 쪽 몫입니다)

| 무엇 | 메모 |
|---|---|
| **적재(`POST /analyses`)** | 미결 `jin` 1번(적재 규격)이 먼저입니다. `metric_definition` 이 **0 행**이라 지금 만들면 외래키에서 전부 거부됩니다. **그때까지 산출물은 `reports/` 의 JSON 입니다** |
| **`running` 회수** | 워커가 죽으면 작업이 `running` 인 채 남습니다. 몇 분 지나면 `queued` 로 되돌리는 규칙이 필요합니다 |
| **재시도** | `failed` 를 다시 큐에 넣는 경로. 횟수·간격 정책이 정해지지 않아 안 열었습니다 |
| **`WORKER_TOKEN` 서버 반영** | 값을 만들어 `.env` 에 넣고 전달드리겠습니다 |

---

## 확인하는 법

붙이신 뒤 이렇게 보면 됩니다.

```bash
# 큐가 줄어드는가
curl -s -H "X-Worker-Token: <값>" \
  -X POST https://api.supersub-ai.com/api/v1/internal/analysis-jobs/claim -i | head -1
# 204 면 빈 것, 200 이면 하나 집은 것 (🔴 이 명령 자체가 작업을 하나 소비합니다)

# 리포트가 생기는가
aws s3 ls s3://supersub-ai/reports/ --recursive | tail
```

⚠️ **위 `curl` 은 확인이 아니라 소비입니다.** 워커가 돌고 있을 때 부르면 그 작업을
가로챕니다. 상태만 보시려면 리포트 쪽을 보시는 편이 낫습니다.
