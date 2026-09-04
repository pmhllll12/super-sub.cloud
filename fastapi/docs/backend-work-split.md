# 백엔드 미구현 분담 (2026-09-03)

> **받는 사람:** 백성검(패킷 A — 과금) · 박민호(패킷 B — 평가·신뢰)
> **보낸 사람:** 정어진 (백엔드 — `fastapi/`)
> **상태:** 전달 · 2026-09-03
> **확인:** 각 패킷의 「먼저 확인」을 돌리면 착수 여부가 바로 나옵니다

부록 D 의 여섯 도메인 중 **넷은 돌아가고 둘이 비어 있습니다.** 그 둘을 통째로
넘깁니다. 저는 나머지(카드·호칭의 남은 셋 · 매칭의 남은 둘 · `player_vector`)를
계속합니다.

## 이 문서를 Claude 에게 주실 때

```
fastapi/docs/backend-work-split.md 를 읽고 나에게 배정된 패킷을 찾아줘.
「먼저 확인」을 실제로 돌려보고, 이미 되어 있으면 손대지 마.
「하지 말 것」과 「공유 파일 5곳」은 반드시 지켜줘.
```

---

## 왜 테이블 수가 아니라 **도메인**으로 잘랐나

`app/` 아래 컨텍스트마다 `domain` · `application` · `adapter` · `dependencies` 를
두는 구조를 `tests/test_architecture.py` 가 **실제로 검사합니다.** 도메인 경계가 곧 폴더
경계라, 도메인으로 자르면 **두 사람의 파일이 안 겹칩니다.**

테이블 개수로 균등하게 자르면 한 도메인이 둘로 쪼개져 **같은 컨텍스트 폴더를 둘이
만지게 됩니다.** 그게 충돌의 원인이 됩니다.

## 🔴 건드리면 안 되는 공유 파일 5곳 — **배선은 제가 합니다**

새 컨텍스트를 하나 만들 때마다 반드시 손대야 하는 파일들입니다. 제가 09-03 에
클립 업로드를 넣으면서 다섯 곳 모두 건드렸습니다.

| 파일 | 무엇 |
|---|---|
| `app/main.py` | 라우터 등록 튜플 |
| `alembic/env.py` | ORM import 블록 |
| `tests/conftest.py` | 스텁 저장소 오버라이드 (세 자리) |
| `tests/user/adapter/test_auth_router.py` | OpenAPI 경로 집합 — **정확히 일치**로 검사합니다 |
| `alembic/versions/` | 🔴 `down_revision` **선형 체인** |

앞의 넷은 충돌해도 손으로 풀면 됩니다. **마지막 하나가 문제입니다** — 두 사람이
각자 마이그레이션을 만들면 `down_revision` 이 같은 값을 가리켜 **head 가 둘이 되고
`alembic upgrade head` 가 죽습니다.** 자동 병합이 안 되는 자리입니다.

**그래서 이 다섯 곳은 제가 배선합니다.** 두 분은 자기 컨텍스트 폴더 안에서만
작업하시고, 다 되면 알려 주십시오. 배선은 5분이고 충돌 해결은 30분입니다.

### 마이그레이션은 쓰시되 `down_revision` 만 비워 두십시오

파일은 만드셔도 됩니다 — 스키마를 아는 사람이 쓰는 게 맞습니다. 다만:

```python
revision: str = 'a1b2c3d4e5f6'          # 아무 16진수 12자리
down_revision: Union[str, Sequence[str], None] = None   # 🔴 제가 채웁니다
```

`down_revision` 을 `None` 으로 두시면 제가 병합할 때 체인에 맞게 채웁니다.

#### 🔴 다만 **마이그레이션만 먼저 `main` 에 가면 CI 가 깨집니다** (2026-09-04 추가)

이 안내에 빠진 것이 있었습니다. 실제로 그렇게 깨졌으니 적어 둡니다.

| 단계 | 무엇이 터지나 |
|---|---|
| `alembic upgrade head` | `down_revision` 이 비어 있으면 head 가 둘이 되어 **"Multiple head revisions"** 로 죽습니다 |
| `alembic check` | 이어 놓아도 **ORM 이 없으면** 그 테이블을 "DB 에만 있는 것"으로 보고 `DROP TABLE` 을 만듭니다 |

CI 가 이 둘을 순서대로 돌기 때문에 **마이그레이션과 ORM 은 같이 가야 합니다.**

**그러니 마이그레이션만 따로 푸시하지 마시고, 최소한 ORM 까지 함께 주십시오.**
(먼저 확인만 받고 싶으시면 브랜치에 두시고 **`main` 에는 안 올리면** 됩니다 —
CI 는 `main` 과 각자 브랜치에서 돌므로 브랜치에서도 같은 이유로 빨간불이 납니다.)

---

## 시작하기

### 1. 읽을 것 (순서대로)

| 문서 | 무엇 |
|---|---|
| `fastapi/CLAUDE.md` | 🔴 **관례. 이걸 안 읽으면 CI 가 막습니다** — 컨텍스트 경계, 검사 넷, 테스트 두 층 |
| `jekyll/chapters/부록D-데이터베이스ERD.markdown` | 테이블 정의의 정본. 컬럼을 여기서 벗어나지 않습니다 |
| `fastapi/docs/api-contract.md` | 계약 형식. 3-3 · 3-4 절이 최근 예시입니다 |

### 2. 환경

```bash
cd fastapi
pg_ctlcluster 18 main start          # root. WSL 은 자동 기동이 아닙니다
.venv/bin/pytest -q                  # 353 passed, skipped 0 이어야 합니다
```

🔴 **`skipped` 가 보이면 DB 를 안 띄운 것입니다.** 실패가 아니라 skip 이라 초록색으로
끝나 놓치기 쉽습니다. CI 는 skip 이 있으면 exit 1 을 냅니다.

### 3. 따라 쓸 본보기

**`app/match/`** 를 보십시오. 가장 최근에 만든 컨텍스트이고, 남의 테이블을 원시
쿼리로 읽는 방식까지 들어 있습니다.

| 볼 것 | 파일 |
|---|---|
| 폴더 구조 전체 | `app/match/` |
| 남의 테이블 읽기 | `app/match/adapter/outbound/pg/match_pg_repository.py` 맨 위 |
| 라우터 | `app/match/adapter/inbound/api/v1/match_router.py` |
| 계약 테스트 | `tests/match/adapter/test_match_router.py` |
| DB 통합 테스트 | `tests/match/adapter/test_match_db.py` |

### 4. 🔴 컨텍스트끼리 임포트하지 않습니다

남의 테이블이 필요하면 **모듈을 가져오지 말고 필요한 컬럼만** 읽습니다.

```python
from sqlalchemy import column, table
_match = table("match", column("id"), column("played_at"))
```

`tests/test_architecture.py` 가 이것을 검사합니다. 대가는 **저쪽 컬럼 이름이 바뀌면
파이썬이 안 잡아 준다**는 것이라, `@pytest.mark.db` 통합 테스트가 유일한 방어선입니다.
**그 테스트를 반드시 쓰십시오.**

---

## 패킷 A — 과금 (백성검 님)

부록 D 도메인 ⑥. 테이블 셋입니다.

| 테이블 | 컬럼 (ERD 그대로) |
|---|---|
| `analysis_credit` | `id` PK · `user_id` FK · `delta` int · `reason` text · `created_at` |
| `coach` | `id` PK · `name` text · `contact` text |
| `coach_referral` | `id` PK · `user_id` FK · `coach_id` FK · `fee` numeric · `created_at` |

### 🔴 잔량은 컬럼이 아니라 `SUM(delta)` 입니다

부록 D 가 그렇게 정했습니다 — "잔량은 delta 의 합으로 구한다". 지급은 양수, 차감은
음수 한 행입니다. **잔량 컬럼을 두면 이력과 갈릴 수 있고, 갈리면 어느 쪽이 맞는지
알 수 없습니다.**

무료 한도를 두든 건당 과금을 하든 **테이블 구조는 같습니다.** 과금 방식이 나중에
정해져도 이 테이블은 그대로 씁니다.

### 만족해야 할 성질

1. **사용자가 자기 크레딧 잔량과 증감 이력을 볼 수 있을 것** (`/credits` 화면)
2. **코치 목록과 상세를 볼 수 있을 것** (방금 만드신 `market/coaches` 화면)
3. **코치 연결을 요청하면 기록될 것** (`coach_referral` 1행)

엔드포인트 이름·개수는 자유입니다. 계약 문서에 절을 추가하실 때 3-3 절 형식을
따라 주시면 됩니다.

### 먼저 확인

```bash
git grep -n "analysis_credit" -- fastapi/app
```

결과가 있으면 이미 착수된 것입니다 — **손대지 않습니다.**

### 정해야 할 것 (혼자 정하지 마시고 박민호 님·사용자와)

- **무료 크레딧을 언제 얼마나 주나** (가입할 때? 매월?)
- **분석 1건에 몇 크레딧인가**
- `reason` 에 들어갈 값의 목록 (`signup_bonus` · `analysis` · `refund` …)

정해지기 전에도 **테이블과 조회는 만들 수 있습니다.** 정책은 값이지 구조가 아닙니다.

### 하지 말 것

- 🔴 **크레딧 차감을 분석 경로에 연결하지 마십시오.** `POST /videos` 는 제
  컨텍스트(`analysis`)이고 컨텍스트끼리는 임포트할 수 없습니다(아키텍처 검사).
  **연결 지점은 제가 붙입니다.** 이번 범위는 조회·지급·수동 조정까지입니다
- **잔량 컬럼을 만들지 마십시오** (위 참조)
- **`coach` 에 `user_id` 를 넣지 마십시오.** ERD 에 없습니다 — 코치는 플랫폼
  사용자가 아니라 외부 제휴자입니다
- **상점(브랜드 카탈로그)은 범위 밖입니다.** 부록 D.8 이 "브랜드 제휴는 본 개발
  기간 범위 밖"이라고 적어 두었습니다. `market.ts` 의 상품 부분은 mock 으로 둡니다

### ⚠️ 붙일 때 걸리는 것 둘

🔴 **종목 코드가 다릅니다.** 백엔드는 `football` 인데
`www/src/lib/market.ts` 는 `soccer` 입니다.

```bash
grep -n "SportCode" www/src/lib/market.ts              # 'soccer' | 'baseball' | 'basketball'
grep -n '"football"' fastapi/alembic/versions/20260901_sport_and_position.py
```

**백엔드가 정본입니다**(`sport` 테이블의 기본키라 외래키가 걸려 있습니다). 화면
코드가 이미 많아 바꾸기 부담스러우면 말씀해 주십시오 — 경계에서 변환하는 것도
방법입니다. 다만 **두 이름이 그대로 공존하는 상태만은 피해야 합니다.**

⚠️ **미결 10번(웹이 mock 에 고정)이 먼저입니다.** 지금 상태로 API 를 만드시면
**자기가 만든 것을 자기 화면에서 확인할 수 없습니다.** 순서를 그렇게 잡아 주십시오.

---

## 패킷 B — 평가·신뢰 (박민호 님)

부록 D 도메인 ⑤. 테이블 다섯입니다. SFR-008.

| 테이블 | 컬럼 (ERD 그대로) |
|---|---|
| `review` | `id` PK · `match_id` FK · `reviewer_id` FK · `reviewee_id` FK · `submitted_at` |
| `review_option` | `code` PK text · `category` text · `label` text |
| `review_selection` | `review_id` PK · `option_code` PK **(복합 기본키)** |
| `report` | `id` PK · `reporter_id` FK · `target_user_id` FK · `reason` text · `created_at` |
| `no_show` | `id` PK · `match_id` FK · `user_id` FK · `recorded_at` |

유일 제약 (부록 D.7):

| 테이블 | 제약 | 뜻 |
|---|---|---|
| `review` | `(match_id, reviewer_id, reviewee_id)` | 경기당 1회 평가 |
| `no_show` | `(match_id, user_id)` | 경기당 1인 1건 |

### 🔴 이 도메인이 스키마로 강제하는 것 셋

부록 D 가 설계 원칙을 테이블 모양으로 박아 둔 자리입니다. **어기면 요구사항이
무너집니다.**

1. **평가는 선택형입니다**(3.4). 선택지를 `review_option` 에 정의하고 고른 것을
   `review_selection` 에 **행으로** 담습니다. **`review` 에 총점·별점 컬럼을
   넣지 마십시오** — 그러면 선택형이 아니게 됩니다
2. **평가자 신뢰도는 테이블로 두지 않습니다**(D.4). `review` 와 `review_selection`
   을 집계하면 나오는 **파생값**이라 저장하면 제3정규형에 어긋납니다. 가중치는
   언제든 다시 계산할 수 있고, **소급 생성이 불가능한 것은 원자료뿐**입니다 —
   평가자·피평가자·시점·선택 결과는 처음부터 빠짐없이 적재하십시오
3. **제재는 평가 점수가 아니라 별도 기록입니다**(3.5). 그래서 `report` 와
   `no_show` 는 **`review` 와 이어지지 않습니다.** 외래키를 만들지 마십시오

### 만족해야 할 성질

1. **확정된 경기가 끝난 뒤, 참가자끼리 서로 평가할 수 있을 것**
2. **선택지 목록을 받아올 수 있을 것** (평가 작성 화면이 그려져야 합니다)
3. **같은 경기에서 같은 사람을 두 번 평가할 수 없을 것** — 파이썬이 아니라
   **DB 유일 제약이 막아야 합니다**
4. **주장이 불참·지각을 기록할 수 있을 것** (경기당 1인 1건)
5. **신고를 접수할 수 있을 것**

### 남의 테이블을 읽어야 합니다

| 무엇 | 어디서 | 왜 |
|---|---|---|
| 경기가 끝났나 | `match.played_at` | 경기 전에는 평가할 수 없습니다 |
| 누가 확정됐나 | `match_application` 의 **두 수락 시각이 다 찬 행** | 확정된 사람끼리만 평가합니다 |
| 사람이 있나 | `user.id` | |

전부 제 컨텍스트라 **임포트하지 말고 `table()`/`column()` 으로** 읽으십시오.
`app/match/adapter/outbound/pg/match_pg_repository.py` 맨 위가 그 예시입니다.

### 먼저 확인

```bash
git grep -n "review_option" -- fastapi/app
```

결과가 있으면 이미 착수된 것입니다 — **손대지 않습니다.**

### 정해야 할 것 (PM 이신 만큼 여기가 본론입니다)

- 🔴 **`review_option` 초기 목록** — `category` · `code` · `label`. 이게 평가
  화면의 내용 전부입니다. **마이그레이션이 넣습니다** (`position` 을 그렇게
  넣었습니다 — `20260902_match_tables` 참고)
- **평가 가능 기간** — 경기 후 며칠까지?
- **신고 `reason`** 이 자유 텍스트인가 정해진 목록인가
- **불참을 누가 기록할 수 있나** — 주장만? 상대 팀도?

### 하지 말 것

- **신뢰도 점수 컬럼이나 테이블을 만들지 마십시오** (위 2번)
- **`review` 에 총점·별점을 넣지 마십시오** (위 1번)
- **`report`·`no_show` 를 `review` 에 잇지 마십시오** (위 3번)
- **`review_selection` 에 대리 키(`id`)를 넣지 마십시오** — ERD 가 복합 기본키로
  정해 두었습니다. 대리 키를 두면 같은 선택지를 두 번 담을 수 있게 됩니다

---

## 다 만들면

1. 자기 브랜치(`paik` · `min`)에 푸시하고 **알려 주십시오**
2. 제가 공유 파일 5곳을 배선하고 `down_revision` 을 채웁니다
3. 배선 뒤 `.venv/bin/pytest -q` 가 **skipped 0** 으로 통과하면 끝입니다

막히거나 규격이 애매하면 **미결 항목에 올리거나 저에게 물어보십시오.** 부록 D 와
어긋나는 것을 발견하시면 **문서를 고치지 마시고** 미결 항목으로 올려 주십시오 —
남의 문서를 직접 고치면 머지 충돌이 됩니다.
