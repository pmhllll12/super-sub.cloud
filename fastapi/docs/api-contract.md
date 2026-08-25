# API 계약 초안 — 인증 · 선수 카드

> **상태:** 진행 전 (초안, 합의 필요) · 2026-08-25 확인
> **확인:** `curl -s localhost:8000/openapi.json | python3 -c "import json,sys; print(list(json.load(sys.stdin)['paths']))"`
> → `['/health']` 이면 아직 아무것도 구현되지 않았다
> **메모:** 스프린트 2(09.01~)의 Flutter 화면 두 개(로그인 · 선수 카드)에 필요한
> 최소 범위만 잡았다. 구현 전에 정어진·박민호와 맞춘다.

대상: **정어진**(이 API를 호출하는 쪽), **박민호**(스키마 소유), **백성검**(범위 판단).

근거 문서는 부록 D — 데이터베이스 ERD(`jekyll/chapters/부록D-데이터베이스ERD.markdown`)와
그 SVG(`assets/erd/domain1-user-team.svg`, `domain3-card-title.svg`)다.
**여기 나오는 필드는 전부 실제 스키마에 있는 컬럼이다.** 없는 것은 "스키마에 없음"으로 적었다.

---

## 0. 먼저 정해야 하는 것

**이 두 개가 정해지기 전에는 인증을 구현할 수 없다.** 나머지는 내가 정해도 되는 수준이다.

### 🔴 Q1. `user` 테이블에 자격증명 컬럼이 없다

부록 D는 `user`를 "계정과 인증 주체 (SEC-003)"라고 하는데 실제 컬럼은 넷뿐이다.

| 컬럼 | 타입 |
|---|---|
| id | uuid PK |
| email | text (유일) |
| nickname | text |
| created_at | timestamptz |

**비밀번호 해시도, 소셜 로그인 provider도 둘 자리가 없다.** 어느 쪽으로 가든
**스키마 변경이 필요하고, 스키마는 박민호 담당이다.**

| 방식 | 필요한 변경 |
|---|---|
| 이메일 + 비밀번호 | `user`에 `password_hash text NOT NULL` 추가 |
| 소셜 로그인(카카오 등) | `user_identity` 테이블 신설 (`user_id`, `provider`, `provider_uid`, 유일제약 `(provider, provider_uid)`) |
| 둘 다 | 위 둘 다. `password_hash`는 널 허용으로 |

**소셜 로그인을 권한다** — 생활체육 사용자 대상이라 가입 이탈이 적고, 비밀번호 재설정
플로우(메일 발송 등)를 만들지 않아도 된다. 다만 **10주 일정에 OAuth 연동이 들어가는지**는
백성검이 판단할 일이다. 아래 명세는 **이메일+비밀번호 기준**으로 적었다 — 더 단순해서
초안의 기준선으로 삼았을 뿐 권고가 아니다.

### 🔴 Q2. 토큰 방식

액세스 토큰만 쓸지, 리프레시 토큰까지 둘지. 앱이라 세션이 길어야 해서 리프레시가
필요할 것 같은데, 프로토타입 단계에서는 **긴 만료의 액세스 토큰 하나**로 시작해도 된다.
아래는 후자로 적었다.

---

## 1. 공통 규약

| 항목 | 값 |
|---|---|
| 베이스 경로 | `/api/v1` |
| 식별자 | uuid (문자열) |
| 시각 | RFC 3339 UTC — `2026-08-25T10:30:00Z` |
| 인증 헤더 | `Authorization: Bearer <token>` |
| 요청·응답 본문 | `application/json`, 필드명 `snake_case` |

### 에러 응답

성공이 아닌 모든 응답은 형태가 같다.

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "이메일 또는 비밀번호가 올바르지 않습니다."
  }
}
```

`code`는 클라이언트가 분기할 값이고 `message`는 사람이 읽을 문장이다.
**정어진 쪽에서 `message`로 분기하지 않도록** `code`를 반드시 채운다.

| HTTP | 언제 |
|---|---|
| 400 | 요청 형식이 잘못됨 |
| 401 | 토큰 없음·만료·무효 |
| 403 | 권한 없음 (남의 자원) |
| 404 | 없는 자원 |
| 409 | 중복 (이메일 등) |
| 422 | 형식은 맞지만 값이 유효하지 않음 |

---

## 2. 인증

### `POST /api/v1/auth/signup`

인증 불필요.

```json
{ "email": "hong@example.com", "password": "...", "nickname": "홍길동" }
```

`201 Created`

```json
{
  "id": "3f1c...",
  "email": "hong@example.com",
  "nickname": "홍길동",
  "created_at": "2026-08-25T10:30:00Z"
}
```

| 에러 | code |
|---|---|
| 409 | `EMAIL_ALREADY_EXISTS` — `user.email` 유일제약(D.7) |
| 422 | `WEAK_PASSWORD` / `INVALID_EMAIL` |

> 비밀번호 최소 조건은 아직 미정이다. 5장 요구사항이 비어 있어 근거가 없다.

### `POST /api/v1/auth/login`

인증 불필요.

```json
{ "email": "hong@example.com", "password": "..." }
```

`200 OK`

```json
{ "access_token": "eyJ...", "token_type": "bearer", "expires_in": 604800 }
```

| 에러 | code |
|---|---|
| 401 | `INVALID_CREDENTIALS` |

> **이메일이 없는 경우와 비밀번호가 틀린 경우를 구분하지 않는다.** 구분하면 가입 여부가
> 새어 나간다.

### `GET /api/v1/me`

인증 필요.

`200 OK`

```json
{
  "id": "3f1c...",
  "email": "hong@example.com",
  "nickname": "홍길동",
  "created_at": "2026-08-25T10:30:00Z",
  "teams": [
    { "team_id": "9a2e...", "name": "번개FC", "region": "서울 강남",
      "sport_code": "futsal", "role": "member", "joined_at": "2026-07-01T00:00:00Z" }
  ]
}
```

`teams`는 `team_member`에서 **`left_at`이 널인 행만** 추린다. 탈퇴 이력은
소프트 삭제로 남아 있으므로(부록 D 도메인 ①) 걸러내지 않으면 나간 팀이 같이 나온다.

---

## 3. 선수 카드

### `GET /api/v1/me/card`

인증 필요. 내 카드.

`200 OK`

```json
{
  "id": "7b4d...",
  "public_slug": "hong-gildong-4f2a",
  "og_image_key": "cards/7b4d....png",
  "user": { "id": "3f1c...", "nickname": "홍길동" },
  "titles": [
    { "code": "sharp_shooter", "label": "슈팅이 매서운", "category": "강점",
      "granted_at": "2026-08-20T12:00:00Z" },
    { "code": "weekend_regular", "label": "주말 개근", "category": "활동",
      "granted_at": "2026-08-01T09:00:00Z" }
  ]
}
```

| 에러 | code |
|---|---|
| 404 | `CARD_NOT_FOUND` — 아직 카드가 없다 |

### `GET /api/v1/cards/{public_slug}`

**인증 불필요** — 공유용이다(SFR-009). 응답 형태는 위와 같되 `id`를 빼고
공개해도 되는 것만 담는다.

| 에러 | code |
|---|---|
| 404 | `CARD_NOT_FOUND` |

---

## 4. 스키마가 강제하는 규칙 — API에서도 지켜야 한다

부록 D.5가 "코드에만 두면 지켜지지 않으므로 테이블 설계 단계에서 막는다"고 한 것들이다.
**API 응답에서 되살아나면 설계가 무의미해진다.**

| 원칙 | API에서의 뜻 |
|---|---|
| 카드에 수치 능력치를 노출하지 않는다 (3.5) | `player_card`에는 능력치 컬럼이 **없다**. 카드 응답에 점수·등급·별점을 넣지 않는다. 수치는 `analysis_metric_value`에만 있고 **리포트 경로로만** 나간다 |
| 호칭은 미부여 방식으로만 작동한다 (3.5) | `titles`에 **받은 것만** 담는다. `"earned": false` 같은 필드를 만들지 않는다 — 미달 표식이 된다 |
| 전체 순위표를 두지 않는다 (3.4) | 사용자 간 비교·정렬 엔드포인트를 만들지 않는다 |

`titles`가 빈 배열인 것은 정상 상태다. **"아직 호칭 없음"을 부정적으로 표시하지 않도록**
정어진 쪽 화면에서도 확인이 필요하다.

---

## 5. 이 범위에 넣지 않은 것

스프린트 2 화면 두 개에 필요 없어서 뺐다. 필요해지면 그때 추가한다.

- 카드 생성·수정 (`POST/PATCH /me/card`) — 카드가 어느 시점에 생기는지가 미정
- 분석 리포트 조회 — 영상 분석 파이프라인(박민호)이 나온 뒤
- 매칭·평가·과금 — 스프린트 3 이후
- 비밀번호 재설정, 이메일 인증 — 인증 방식(Q1)이 정해진 뒤
- 토큰 갱신 — Q2가 정해진 뒤

---

## 6. 다음 단계

1. Q1(자격증명 컬럼)·Q2(토큰)를 **박민호·백성검과 확정**한다.
2. 확정되면 이 문서대로 Pydantic 모델과 라우트를 만든다. FastAPI가
   `/docs`에 OpenAPI를 자동 생성하므로 **정어진은 그걸 보고 붙이면 된다.**
3. DB가 아직 없으므로 **초기에는 고정 응답(스텁)으로 먼저 열어준다.** 정어진이
   09.01에 바로 화면을 붙일 수 있게 하는 것이 목적이고, 실제 조회는 그 뒤에 채운다.
