# API 계약 초안 — 인증 · 선수 카드

> **상태:** 구현됨 — **전부 PostgreSQL에 붙었다. 고정 응답은 없다** · 2026-09-02 확인
> **확인:** `cd fastapi && .venv/bin/pytest` → `318 passed`
> (DB가 없는 환경에서는 `223 passed, 95 skipped`. 통합 테스트만 건너뛴다)
> **메모:** 스프린트 2(09.01~)의 Flutter 화면 두 개(로그인 · 선수 카드)에 필요한
> 최소 범위. **응답 형태는 2026-08-25 이후 바뀌지 않았다** — 화면 쪽에서 고칠 것은 없다.

| 엔드포인트 | 상태 |
|---|---|
| `POST /auth/signup` · `POST /auth/login` · `POST /auth/google` | **실제 DB** |
| `GET /me` · `PATCH /me` | **실제 DB** |
| `GET /me/card` · `GET /cards/{slug}` | **실제 DB** (2026-08-26에 스텁을 걷어냈다) |
| `POST /me/card` | **실제 DB** (2026-09-02 추가 — 카드는 여기서만 생긴다, 3장) |
| `POST /teams` · `GET /teams/{id}` · `POST`·`DELETE /teams/{id}/members` | **실제 DB** (2026-09-02 추가, 3-3절) |
| `POST`·`GET /teams/{id}/matches` · `GET /matches/{id}` | **실제 DB** (2026-09-02 추가, 3-4절) |
| `POST`·`GET /matches/{id}/applications` · `POST .../accept` · `DELETE .../{application_id}` | **실제 DB** (2026-09-02 추가 · 무르기·거절은 2026-09-04, 3-5절) |
| `GET /admin/users` · `GET /admin/users/{id}` · `DELETE /admin/users/{id}` | **실제 DB** (2026-08-31 추가, 3-2절) |
| `GET /admin/videos` · `DELETE /admin/videos/{id}` | **실제 DB** (2026-09-08 추가 — 미결 `jin` 24번, 3-2절) |
| `POST /internal/analysis-jobs/claim` · `PATCH /internal/analysis-jobs/{id}` | **실제 DB** (2026-09-04 추가 — **워커 전용**, 3-8절) |
| `GET /review-options` · `POST /matches/{id}/reviews` · `POST /matches/{id}/no-shows` · `POST /reports` | **실제 DB** (2026-09-04 추가, 3-9절) |

## 눌러볼 수 있는 값

| | |
|---|---|
| 데모 이메일 | `demo@super-sub.example` |
| 데모 비밀번호 | `supersub2026` |
| 공개 카드 슬러그 | `hong-gildong-4f2a` (스텁) |

**전부 실제 DB다.** 위 데모 계정과 카드는 개발 DB에 넣어 둔 실물이고,
`POST /auth/signup`으로 **새 계정을 만들어 그걸로 로그인해도 된다.**

🔴 **새 계정은 빈 상태로 온다.** 화면에서 이 두 가지를 확인해 둘 것.

| 화면 | 빈 상태 |
|---|---|
| `GET /me` | `teams`가 **빈 배열** (소속 팀이 없다) |
| `GET /me/card` | **404 `CARD_NOT_FOUND`** — 카드는 가입만으로 생기지 않는다 |

카드가 어느 시점에 생기는지는 아직 미정이다(5절). 지금은 개발 DB에 넣어 둔 데모
카드 하나뿐이므로, 새 계정으로는 카드 화면을 볼 수 없다.

`/docs`(Swagger UI)에도 같은 안내가 떠 있다. ⚠️ **`/docs`·`/redoc`·`/openapi.json`은
`APP_ENV`가 `local`·`dev`일 때만 열린다** — 그 밖의 환경에서는 404이고 위 데모 계정도
문서에 찍히지 않는다. 배포된 주소에서 404가 나오면 고장이 아니다.

대상: **백성검**(이 API를 호출하는 쪽), **박민호**(범위 판단). 스키마는 내가 소유한다.

근거 문서는 부록 D — 데이터베이스 ERD(`jekyll/chapters/부록D-데이터베이스ERD.markdown`)와
그 SVG(`assets/erd/domain1-user-team.svg`, `domain3-card-title.svg`)다.
**여기 나오는 필드는 전부 실제 스키마에 있는 컬럼이다.** 없는 것은 "스키마에 없음"으로 적었다.

---

## 0. 정해진 것

### ✅ 인증 방식 — 이메일 + 비밀번호, 그리고 구글 (2026-08-26 갱신)

부록 D의 `user`는 컬럼이 `id`·`email`·`nickname`·`created_at` 넷뿐이라 자격증명을
둘 자리가 없었다. **`user`를 건드리는 대신 `user_credential` 테이블을 새로 만든다.**

| 컬럼 | 타입 |
|---|---|
| id | uuid PK |
| user_id | uuid FK → user (유일) |
| password_hash | text |
| updated_at | timestamptz |

`user`에 `password_hash`를 붙이지 않은 이유는 두 가지다.

1. 나중에 소셜 로그인을 추가할 때 `user_identity`를 나란히 두면 되고 `user`는 그대로다.
   컬럼으로 붙였다면 소셜 가입자에게 널 허용으로 바꿔야 한다.
2. `user`는 거의 모든 테이블이 조인하는 허브다(부록 D 서두). **해시가 그 위에 있으면
   무심코 조회될 여지가 생긴다.** 분리해 두면 자격증명 조회 경로가 로그인 하나로 좁혀진다.

부록 D는 갱신했다(도메인 ① 표 · D.6 삭제 연쇄 · D.7 유일제약 · **34테이블**).
**단 SVG 그림은 손대지 않았다** — 좌표가 직접 박힌 수작업 파일이라 비용이 크다.
그림 밑에 낡았다는 주석을 달아 두었다.

> **2026-08-26 — 구글 로그인을 범위에 넣었다.** 08-25 에는 "소셜 로그인은 넣지
> 않는다"고 적었으나 뒤집었다. 위 구조 덕에 `user_identity` 테이블 하나만 추가하면
> 됐고 `user`·`user_credential` 은 그대로다.
>
> **백엔드는 끝났다. 남은 것은 백성검 쪽이다** — `google_sign_in` 으로 받은
> **ID 토큰**을 `POST /auth/google` 에 넘기면 된다. 그리고 구글 클라우드에서
> 플랫폼별 OAuth 클라이언트 ID 를 발급해 서버 `GOOGLE_CLIENT_IDS` 에 넣어야 한다.
>
> 카카오·애플은 여전히 범위 밖이다. 붙일 때는 `user_identity.provider` 에 값을
> 하나 더 쓰면 되고 테이블은 늘지 않는다.

### ✅ 토큰 — 액세스 토큰 하나 (재검토 대상)

리프레시 토큰을 두지 않는다. 프로토타입 단계라 **긴 만료(7일)의 액세스 토큰 하나**로
시작한다. 앱 세션이 길어야 하는 문제가 실제로 확인되면 그때 리프레시를 붙인다.

**이건 내가 정한 것이고 되돌리기 쉬운 쪽을 골랐다.** 리프레시를 나중에 추가하는 것은
엔드포인트 하나(`POST /auth/refresh`)와 저장소 하나가 늘 뿐이고, 반대로 지금 넣으면
회전·폐기·재사용 탐지를 다 만들어야 한다.

**대신 폐기 능력만 따로 넣었다 (2026-08-28).** 서명만으로 검증되는 토큰은 서버가
"잊을" 방법이 없어서, 기기를 잃어버려도 7일이 지나야 만료된다. 사용자마다 버전을
하나 두고 발급 시점의 값을 토큰에 실어 대조한다 — 버전을 올리면 그 사람의 **기존
토큰이 한 번에 무효**가 된다(`POST /auth/logout-all`). 회전은 여전히 없다.

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
**백성검 쪽에서 `message`로 분기하지 않도록** `code`를 반드시 채운다.

| HTTP | 언제 |
|---|---|
| 400 | 요청 형식이 잘못됨 |
| 401 | 토큰 없음·만료·무효 |
| 403 | 권한 없음 (남의 자원) |
| 404 | 없는 자원 |
| 409 | 중복 (이메일 등) |
| 422 | 형식은 맞지만 값이 유효하지 않음 |
| 429 | 요청이 너무 잦음 (인증 엔드포인트) |

### 인증 헤더 관련 code

| HTTP | code | 언제 |
|---|---|---|
| 401 | `UNAUTHORIZED` | `Authorization` 헤더가 없거나 `Bearer ` 형식이 아니다 |
| 401 | `INVALID_TOKEN` | 형식은 맞지만 토큰이 유효하지 않다 — 만료·서명 불일치, 그리고 **폐기된 토큰**(`logout-all` 이후)도 여기다 |

**둘을 나눈 이유**는 클라이언트 동작이 다르기 때문이다. 전자는 로그인 화면으로,
후자는 토큰을 버리고 재로그인으로 보낸다.

### 요청 제한(429)

| HTTP | code | 언제 |
|---|---|---|
| 429 | `TOO_MANY_REQUESTS` | 같은 출처에서 **한 인증 경로에 1분 안에 10회**를 넘겼다 |

`/auth/signup` · `/auth/login` · `/auth/google` 에만 걸린다. 경로별로 따로 세므로
로그인이 막혀도 가입은 열려 있다. 조회 API(`/me` 등)에는 걸리지 않는다.

비밀번호 해싱이 일부러 느려서 **인증 요청 자체가 서버 자원을 태우는 수단**이기
때문이다(5장 SEC-009). 계정 잠금은 쓰지 않는다 — 남의 이메일만 알면 그 계정을
잠글 수 있어 그 자체가 공격이 된다.

#### `Retry-After` 헤더 (2026-09-01 추가)

429 응답에는 **`Retry-After` 가 정수 초로 함께 온다.** 고정값이 아니라 **그 시점에
남은 시간**이다 — 기다릴수록 줄어든다.

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 37
```

**올림한 값이라 그만큼 기다리면 반드시 한 자리가 비어 있다.** 내림하면 알려 준
시각에 다시 429 를 맞으므로 올린다.

> **앱 쪽에서 할 일:** 429 를 받으면 **곧바로 재시도하지 않는다.** `Retry-After`
> 만큼 기다린 뒤에만 다시 보낸다(자체 타이머를 만들 필요가 없다). 사용자에게는
> "잠시 후 다시 시도" 안내를 띄운다. `message` 가 아니라 `code` 로 분기한다.

⚠️ **거부된 요청은 카운터에 넣지 않는다.** 즉 429 를 받는 동안 계속 두드려도
**제한이 연장되지는 않는다** — 창이 지나면 풀린다. 다만 서버 자원을 쓰는 무의미한
요청이므로 하지 않는 편이 맞다. (`Retry-After` 가 신뢰할 수 있는 값인 이유이기도
하다 — 재시도가 만료 시각을 뒤로 밀지 않는다.)

### 검증 실패(422)

Pydantic 검증에 걸리면 `code`는 항상 `VALIDATION_ERROR` 하나이고 `message`에
문제가 된 필드 이름이 들어간다.

```json
{ "error": { "code": "VALIDATION_ERROR",
             "message": "요청 값이 올바르지 않습니다: email, password, nickname" } }
```

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

**입력 제약**

| 필드 | 제약 |
|---|---|
| email | 이메일 형식 |
| password | **8자 이상** |
| nickname | 1~20자 |

비밀번호에 대문자·특수문자를 강제하지 않는다 — 사용자를 예측 가능한 패턴으로 몰 뿐이다.
5장 요구사항이 비어 있어 근거가 없으므로 최소한만 걸었다. 해시는 bcrypt를 쓴다
(**스텁 단계라 아직 해싱하지 않는다 — 저장 자체를 하지 않는다**).

닉네임 20자는 내가 정했다. 카드에 표시되는 값이라 상한이 필요한데 근거 문서가 없다.

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

### `POST /api/v1/auth/google`

인증 불필요. **처음 들어온 구글 계정이면 그 자리에서 가입까지 된다.**

```json
{ "id_token": "eyJ..." }
```

> ⚠️ `access_token` 이 아니라 **`id_token`** 이다. `google_sign_in` 은 둘 다 주는데,
> 바꿔 보내면 서명 검증에서 401 이 난다.

`200 OK` — **비밀번호 로그인과 응답이 같다.** 이후 흐름을 하나로 유지하면 된다.

```json
{ "access_token": "eyJ...", "token_type": "bearer", "expires_in": 604800 }
```

| 에러 | code | 언제 |
|---|---|---|
| 401 | `INVALID_GOOGLE_TOKEN` | 서명·만료·발급자·대상 중 하나라도 어긋남 |
| 409 | `EMAIL_ALREADY_EXISTS` | 같은 이메일의 계정이 있는데 구글이 그 이메일을 **확인해 주지 않았다** |
| 422 | `GOOGLE_EMAIL_MISSING` | 구글 토큰에 이메일이 없다 |
| 503 | `GOOGLE_LOGIN_NOT_CONFIGURED` | 서버에 `GOOGLE_CLIENT_IDS` 가 없다 |

**같은 이메일의 계정이 이미 있으면** 구글이 이메일 소유를 확인해 준 경우에만
그 계정에 연결한다. 확인되지 않았으면 409 로 막고 비밀번호 로그인을 안내한다 —
연결해 주면 아무 이메일이나 적어 남의 계정을 가져갈 수 있다.

**연결된 계정의 닉네임은 바꾸지 않는다.** 구글 표시 이름으로 덮어쓰지 않는다.
새로 만드는 경우에만 구글 이름(20자 초과 시 자름)을 쓰고, 이름이 없으면
이메일 앞부분을 쓴다.

#### 앱 쪽에서 할 일 (2026-08-26 기준)

구글 클라우드 등록은 **끝났다.** 프로젝트 `supersub` 에 클라이언트 세 개가 있다 —
웹 하나, 안드로이드 둘(디버그 서명 두 종류).

🔴 **`google_sign_in` 의 `serverClientId` 에는 "웹 애플리케이션" 클라이언트 ID 를 넣는다.**
안드로이드 클라이언트 ID 가 아니다. 안드로이드 클라이언트는 "이 패키지·이 서명의 앱이
로그인을 요청해도 된다"를 구글에 등록하는 용도이고, 발급되는 ID 토큰의 `aud` 에는
들어가지 않는다. 잘못 넣으면 **로그인은 되는데 서버가 401 만 준다.**

값은 저장소에 두지 않는다(공개 저장소다). 구글 클라우드 콘솔
**사용자 인증 정보 → `supersub`(웹 애플리케이션)** 에서 복사하거나 정어진에게 요청한다.

| 항목 | 값 |
|---|---|
| 안드로이드 패키지 | `cloud.supersub.super_sub` |
| iOS 번들 ID | `cloud.supersub.superSub` (iOS 클라이언트는 아직 안 만들었다) |

⚠️ **릴리스 빌드는 아직 구글 로그인이 안 된다.** 등록된 SHA-1 이 디버그 키 두 개뿐이다
(`build.gradle.kts` 가 아직 디버그 키로 서명한다). 릴리스 키스토어를 만들면 그 SHA-1 로
안드로이드 클라이언트를 하나 더 등록해야 한다 — **디버그에서 되니까 릴리스도 되겠지가
안 통하는 자리다.**

### `POST /api/v1/auth/logout-all`

**인증 필요.** 이 계정에 발급된 **모든 토큰을 무효로** 만든다(5장 SEC-004).

`204 No Content` — 본문이 없다.

| 에러 | code |
|---|---|
| 401 | `UNAUTHORIZED` · `INVALID_TOKEN` |

🔴 **지금 쓰고 있는 토큰도 함께 끊긴다.** 호출한 기기도 로그인 화면으로 돌아가야
한다 — 기기를 잃어버렸을 때 쓰라고 만든 것이라 "지금 것만 남기기"는 두지 않았다.

> **앱 쪽에서 할 일:** 204 를 받으면 저장한 토큰을 지우고 로그인 화면으로 보낸다.
> 그 뒤의 요청은 전부 401 `INVALID_TOKEN` 이다.

이후 다른 기기의 요청도 401 `INVALID_TOKEN` 을 받는다. **계정이 잠기는 것이 아니라
토큰만 끊기는 것**이므로 다시 로그인하면 정상 동작한다(잠금 방식은 쓰지 않는다 —
5장 SEC-009).

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
      "sport_code": "football", "role": "member", "joined_at": "2026-07-01T00:00:00Z" }
  ]
}
```

`teams`는 `team_member`에서 **`left_at`이 널인 행만** 추린다. 탈퇴 이력은
소프트 삭제로 남아 있으므로(부록 D 도메인 ①) 걸러내지 않으면 나간 팀이 같이 나온다.

### `PATCH /api/v1/me`

인증 필요. **2026-08-26에 추가됐다** — 그전에는 없어서 클라이언트가 닉네임 수정을
막아 두어야 했다.

```json
{ "nickname": "새이름" }
```

`200 OK` — **응답이 `GET /me`와 완전히 같다.** 클라이언트는 파서를 하나만 들면 되고,
수정 후 다시 조회할 필요도 없다.

| 에러 | code | 언제 |
|---|---|---|
| 401 | `UNAUTHORIZED` / `INVALID_TOKEN` | 인증 헤더 규약과 같다 |
| 422 | `VALIDATION_ERROR` | 닉네임이 비었거나 20자를 넘는다 |

- **앞뒤 공백은 서버가 정규화한다.** `"  홍길동  "` → `"홍길동"`.
  클라이언트에서 따로 다듬지 않아도 된다.
- **바꿀 수 있는 것은 닉네임뿐이다.** 이메일은 계정 식별자라(부록 D.7 유일 제약)
  바꾸려면 재인증과 중복 검사가 붙는다 — 별도 엔드포인트가 될 것이다.

---

### `PATCH /api/v1/me/password`

**인증 필요.** 비밀번호를 바꾼다.

```json
{ "current_password": "...", "new_password": "..." }
```

`204 No Content`

| 에러 | code | 언제 |
|---|---|---|
| 401 | `INVALID_CREDENTIALS` | **현재** 비밀번호가 틀렸다 |
| 401 | `UNAUTHORIZED` · `INVALID_TOKEN` | 인증 실패 |
| 422 | `VALIDATION_ERROR` | 새 비밀번호가 8자 미만이거나 72바이트를 넘는다 |

**현재 비밀번호를 함께 받는 이유**는 토큰만으로 바꿀 수 있으면 토큰을 훔친 쪽이
비밀번호를 갈아 주인을 밀어낼 수 있어서다.

🔴 **성공하면 기존 토큰이 전부 무효가 된다**(SEC-004) — 지금 쓰던 토큰도 포함이다.
앱은 204 를 받으면 토큰을 지우고 새 비밀번호로 다시 로그인시켜야 한다.

### `DELETE /api/v1/me`

**인증 필요.** 탈퇴한다. 계정과 파생 데이터가 함께 지워진다(SEC-006).

```json
{ "password": "..." }
```

`204 No Content`

| 에러 | code | 언제 |
|---|---|---|
| 401 | `INVALID_CREDENTIALS` | 비밀번호가 틀렸다 |
| 401 | `UNAUTHORIZED` · `INVALID_TOKEN` | 인증 실패 |
| 422 | `PASSWORD_REQUIRED` | 비밀번호가 있는 계정인데 안 보냈다 |

**비밀번호가 있는 계정만 비밀번호를 요구한다.** 구글로만 가입한 계정에는 확인할
비밀번호가 없으므로 본문 없이 부르면 된다 — 요구하면 탈퇴할 방법이 사라진다.

되돌릴 수 없는 동작이라 비밀번호 변경보다 엄격하게 잡았다. 함께 지워지는 것은
자격증명·외부 신원·카드·호칭·소속, 그리고 영상 → 분석 작업 → 지표 → 리포트 체인이다
(부록 D.6). **호칭·지표 정의 같은 목록 테이블은 지워지지 않는다.**

> ⚠️ **객체 저장소의 원본·썸네일·추출 프레임은 아직 지우지 않는다.** 저장소가
> 정해지지 않아서다(5장 ASM-003). SEC-006 은 현재 **DB 쪽만** 만족한다.

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
  ],
  "tagline": "THREE LUNGS",
  "style": {
    "bg": "#91ea92", "logo": "#0b0b0b", "text_color": "#0b0b0b",
    "text_x": 50, "text_y": 34, "brush": 0, "brush_color": "#0b0b0b",
    "brush_scale": 1, "brush_x": 0, "brush_y": 0
  }
}
```

**둘 다 안 정했으면 `null`** — 만든 직후 카드가 그렇다(아래 참고).

| 에러 | code |
|---|---|
| 404 | `CARD_NOT_FOUND` — 아직 카드가 없다 |

### `POST /api/v1/me/card` (2026-09-02 추가)

인증 필요. 본문 없음. **카드를 만든다.**

| 응답 | 뜻 |
|---|---|
| `201 Created` | 없던 카드를 만들었다 |
| `200 OK` | 이미 있었다. **있는 카드를 그대로 돌려준다** |

**응답 본문은 `GET /me/card` 와 완전히 같다.** 클라이언트는 파서를 하나만 들면 된다.

🔴 **멱등이다.** 두 번 불러도 카드는 하나고 `public_slug` 도 그대로다. 네트워크가
끊겨 재시도해도 **공유 링크가 바뀌지 않는다** — 이미 공유한 주소가 죽으면 안 된다.

- `public_slug` 는 **무작위**다(96비트, `secrets`). 닉네임에서 유도하지 않는다
  (SEC-005) — 유도하면 이름만 알고 남의 카드 주소를 맞힐 수 있고, 닉네임을 바꿔도
  옛 주소가 뜻을 남긴다
- `titles` 는 **빈 배열**이다. 호칭은 분석 결과로 붙으므로 생성 시점에 있을 수 없다
- `og_image_key` 는 규칙(`cards/{card_id}.png`)으로 채우지만 ⚠️ **그 위치에 파일은
  아직 없다.** 이미지 생성기도 저장 위치도 정해지지 않았다 — 지금 이 값을 그리는
  클라이언트는 없다(`www` 의 카드 화면은 고정 장식 이미지를 쓴다). 그리기 시작하려면
  **생성기가 먼저 있어야 한다**

#### 카드는 언제 생기나 — **요청할 때** (2026-09-02 결정)

요구사항 문서에 "미정"으로 남아 있던 자리다. 셋 중에서 골랐다.

| 안 | 왜 안 골랐나 / 골랐나 |
|---|---|
| **요청할 때 (채택)** | 공개 링크가 생기는 것은 **사용자의 행위**여야 한다. `GET` 이 쓰기를 하지 않아 프리페치·재시도에 안전하다 |
| 조회할 때 자동 | `GET /me/card` 가 행을 만들게 된다. 프리페치나 봇도 생성을 유발하고, 한번 나가면 되돌리기 어렵다 |
| 가입할 때 자동 | `user` 컨텍스트가 `card` 를 임포트해야 하는데 **막혀 있다**(`tests/test_architecture.py`). 슬러그 생성 같은 카드 규칙이 `user` 쪽으로 샌다 |

**기존 계정은 이 엔드포인트를 부르기 전까지 카드가 없다.** `GET /me/card` 는 그대로
404 `CARD_NOT_FOUND` 를 낸다 — 클라이언트의 "아직 없습니다" 빈 상태는 계속 유효하다.

### `PATCH /api/v1/me/card` — 한 줄과 꾸미기 (2026-09-04 신설, 2026-09-11 `style` 추가)

인증 필요. 카드에서 **사람이 정하는 값**을 바꾼다. 미결 `paik` 3번 —
지금까지 카드는 만들고 나면 손댈 것이 없어 **모든 카드가 글자까지 똑같았다**
(별명이 화면의 붙박이 상수였다). `tagline`(한 줄)으로 그 일부를 풀었고,
`style`(바탕·로고·글자 색·글자 자리·붓자국)로 나머지를 마저 푼다.

```json
{
  "tagline": "THREE LUNGS",
  "style": {
    "bg": "#91ea92", "logo": "#0b0b0b", "text_color": "#0b0b0b",
    "text_x": 50, "text_y": 34, "brush": 0, "brush_color": "#0b0b0b",
    "brush_scale": 1, "brush_x": 0, "brush_y": 0
  }
}
```

`200 OK` — 응답 본문은 `GET /me/card` 와 같다.

🔴 **둘은 따로 바뀐다** — `model_fields_set` 로 **보낸 필드만** 본다.
`{"style": {...}}` 만 보내면 `tagline` 은 그대로다(반대도 마찬가지). 아예
빈 본문 `{}` 을 보내면 아무것도 안 바뀌고 지금 카드가 그대로 온다.

| 보내면 | 결과 |
|---|---|
| `{"tagline": "…"}` | 한 줄을 정한다 (**20자까지**) |
| `{"tagline": null}` · `{"tagline": "   "}` | 한 줄을 **지운다** — 안 정한 상태로 |
| 20자 초과 | `422 VALIDATION_ERROR`. 🔴 **조용히 자르지 않는다** — 쓴 것과 보이는 것이 달라지고 알아차리는 시점은 공유한 뒤다 |
| `{"style": {...}}` (아래 형태 그대로) | 꾸미기를 **통째로** 바꾼다 |
| `{"style": null}` | 꾸미기를 지운다 — 기본 모습으로 돌아간다 |
| `style` 필드가 하나라도 모자라거나 색이 `#rrggbb` 형식이 아님 | `422 VALIDATION_ERROR`. 🔴 **부분 병합을 하지 않는다** — 일부만 보내면 나머지를 지우는 대신 거부한다. 화면이 늘 전체 값을 들고 있다가 저장하므로 병합할 이유가 없다 |
| 카드가 없음 | `404 CARD_NOT_FOUND`. **여기서 만들지 않는다** — 만드는 자리는 `POST /me/card` 하나다 |

#### `style` 의 필드

| 필드 | 뜻 | 형식 |
|---|---|---|
| `bg` | 카드 바탕색 | `#rrggbb` |
| `logo` | 워드마크 색 | `#rrggbb` |
| `text_color` | 가운데 큰 글자(=`tagline`) 색 | `#rrggbb` |
| `text_x`·`text_y` | 그 글자의 자리 (카드 폭·높이 대비 %) | `0`~`100` |
| `brush` | 뒤에 까는 자국 — 몇 번째인지 (`www` 의 자산 목록 순서) | 정수 |
| `brush_color` | 자국 색 | `#rrggbb` |
| `brush_scale` | 자국 크기 배율 | `0.1`~`5` |
| `brush_x`·`brush_y` | 자국 자리 (%) | `-100`~`100` |

🔴 **`brush` 의 정확한 상한을 값으로 안 막는다.** 고를 수 있는 자국 개수는
`www` 쪽 자산이라 늘어날 수 있다 — `focus`(3-6절)가 루브릭 항목의 실재를
안 보는 것과 같은 판단으로, 서버는 형식(정수·구간)만 본다.

#### 🔴 여기 없는 것

- `public_slug`·`og_image_key` — **요청 본문에 자리가 없다.** 보내도 무시된다.
  `public_slug`는 이미 공유된 주소라 바꾸면 남이 가진 링크가 죽고, `og_image_key`는
  슬러그에서 규칙으로 나오는 값이다
- `titles` — **분석이 주는 것**이라 사람이 못 고른다(3.5)
- **가운데 큰 글자의 내용** — `style` 이 아니라 **`tagline` 이 그 값이다.**
  `www`가 04-09 이후 이걸 몰라 `style.text`를 새로 만들어 브라우저에만
  담고 있었는데, 이 갱신에서 `tagline` 쪽으로 합친다(`client-contract-
  changes.md` 35번)
- **사진** — `og_image_key`가 "규칙은 있는데 파일이 없는" 상태라(위 `POST
  /me/card` 참고) 저장 위치부터 정해야 한다. 사진에 딸린 자리·크기
  (`photoScale`·`photoX`·`photoY`)와 통째로 까는 모드(`mode`)도 사진이
  없으면 뜻이 없어 같이 뺐다 — `www`는 넷 다 그대로 브라우저에만 둔다.
  `CardStyleSchema` 가 `extra=forbid` 라 이 필드들을 보내면 조용히
  무시되지 않고 **422** 로 막힌다

#### 공개 카드에도 나간다

`GET /cards/{slug}` 응답에도 `tagline`·`style` 이 실린다. 안 실으면 **남이
보는 카드만** 밋밋해진다.

🔴 `tagline`·`style` 은 **부록 D 의 `player_card` 에 없는 컬럼**이다
(각각 2026-09-04 · 2026-09-11 에 늘렸다). ERD 갱신은 미결 항목이다.

### `GET /api/v1/cards/{public_slug}`

**인증 불필요** — 공유용이다(SFR-009). 응답 형태는 위와 같되 `id`를 빼고
공개해도 되는 것만 담는다.

| 에러 | code |
|---|---|
| 404 | `CARD_NOT_FOUND` |

---

## 3-1. 분석 결과 적재 (규격 초안 — 정상호 회람용)

> **상태:** 적재 경로·읽기 엔드포인트는 **구현됨** (2026-09-10, 미결 `jin` 27번) —
>   아래 「✅ 적재 경로(흐름 B)·읽기 엔드포인트」 절. 그 앞의 `POST /analyses`
>   (`metrics[]` 통째 제출) 초안은 **폐기됐다.**
> **확인:** `grep -rn 'videos/{video_id}/report' fastapi/app/` → 라우트가 있으면 읽기 착수됨 ·
>   `grep -rn report_ingest fastapi/app/analysis/` → 적재 인터랙터
> **메모:** 스키마(`40a4991`)와 적재 자리(`analysis_metric_criterion` 등)는 들어갔다.
>   아래 초안 본문은 **폐기된 `POST /analyses` 규격**이라 그대로 두되(닫힌 경로),
>   실물은 「✅ 적재 경로」 절을 본다.

에이전트(`agent/`)가 분석 1회의 결과를 백엔드에 넘기는 경로다. 대상은 **정상호**다.

### 왜 DB에 직접 쓰지 않는가

에이전트가 `analysis_metric_value`에 직접 INSERT하면 세 가지가 양쪽 코드에 중복된다 —
지표 항목 검증, 산출 버전 기록(QUA-002), 삭제 연쇄(SEC-006). 한쪽만 고치면 조용히
갈라진다. **API로 받으면 그 셋이 백엔드 한 곳에만 있고, 에이전트는 DB 접속 정보를
몰라도 된다.**

### 흐름

```
(1) 사용자가 클립을 올린다                (3-6절 — analysis_job 이 queued 로 생긴다)
(2) 에이전트가 분석                       (측정 -> 판정 -> 합산)
(3) POST /analyses  결과를 제출한다      -> analysis_metric_id
```

### 🔴 `POST /videos` 를 정정합니다 (2026-09-03)

**앞서 이 자리에 적었던 `POST /api/v1/videos` 규격은 폐기합니다.** 그때는 객체
저장소가 안 정해져서(5장 ASM-003) "이미 어딘가에 있는 파일의 키만 등록한다"고
적었는데, 09-03 에 **S3 + 사전 서명 URL** 로 정해지면서 그 엔드포인트가 사용자
업로드 경로로 실제 구현됐습니다. 정본은 **3-6절**입니다.

무엇이 달라졌는지:

| | 옛 초안 | 지금 (3-6절) |
|---|---|---|
| 키를 얻는 법 | 밖에서 정해 온다 | `POST /videos/upload-url` 이 발급한다 |
| 키 형태 | `videos/2026/08/28/abc.mp4` | `videos/<user_id>/<uuid>.mp4` — **업로더가 들어간다** |
| 요청 필드 | `sport_code`·`storage_key`·`duration_ms`·`side` | `width`·`height` 가 **추가**됐다(규격 검사) |
| 응답 | `{video_id, analysis_job_id, status}` | `{id, passed, reject_reason, analysis_job_id, analysis_status, …}` |
| 규격 위반 | 없던 개념 | **201 이고 `passed: false`** 다 |

**에이전트가 이 경로로 클립을 등록할 일은 없어졌습니다.** 사용자가 올린 것을 받아
분석하는 것이 흐름이라, 에이전트가 하는 일은 (2)·(3) 뿐입니다. 자체적으로 클립을
넣어 시험해야 하면 저장 키가 업로더에 묶여 있어 그대로는 안 되니, 필요하면
말씀해 주십시오 — 서비스 자격증명으로 넣는 경로를 따로 내겠습니다.

### `POST /api/v1/analyses`

분석 1회의 결과를 **통째로** 받는다. 항목을 나눠 여러 번 부르지 않는다 — 중간에
끊기면 반쪽짜리 지표 묶음이 남기 때문이다.

```json
{
  "analysis_job_id": "9a2e...",
  "pipeline_version": "2026.08.28",
  "metrics": [
    { "code": "knee_angle_impact", "value": 141.7, "frame_index": 62 },
    { "code": "total_score",       "value": 78 }
  ],
  "report": {
    "summary": "디딤발이 공보다 앞서 있습니다. 임팩트에서 무릎을 더 덮어 주세요.",
    "model_name": "exaone-4.0-1.2b"
  }
}
```

`201 Created`

```json
{ "analysis_metric_id": "7c05...", "metric_count": 12 }
```

**총점과 항목별 등급도 `metrics`에 넣는다.** 카드에 능력치 컬럼을 두지 않는 원칙과
짝이다(4장) — 수치는 전부 `analysis_metric_value` 한 곳에 있고 리포트 경로로만 나간다.

`report.summary`는 **선수에게 보여줄 두 문장 이내의 코멘트**이며 **총점·등급 숫자를
넣지 않는다**(3장 4). 숫자는 `metrics`가 갖는다.

| 에러 | code | 언제 |
|---|---|---|
| 401 | `UNAUTHORIZED` | 서비스 자격증명이 없거나 틀리다 |
| 404 | `JOB_NOT_FOUND` | `analysis_job_id`가 없다 |
| 409 | `ANALYSIS_ALREADY_SUBMITTED` | 그 작업의 결과가 이미 있다(작업당 지표 묶음 1건) |
| 422 | `UNKNOWN_METRIC_CODE` | `metric_definition`에 없는 지표 코드 |
| 422 | `VALIDATION_ERROR` | 형식 오류 |

🔴 **`UNKNOWN_METRIC_CODE`는 오타를 막기 위한 것이다.** 지표 코드는
`metric_definition`에 미리 정의돼 있어야 하며, 없는 코드는 DB의 외래키가 거부한다.
**오타 하나가 조용히 새 지표가 되는 것**을 막는 자리다 — 이 검사를 느슨하게 하면
같은 지표가 두 이름으로 쌓인다.

### 분석이 실패했을 때

`analysis_job`은 `queued · running · succeeded · failed`와 실패 사유를 갖는다.
✅ **워커가 `PATCH /internal/analysis-jobs/{job_id}` 로 `{"status": "failed",
"failure_reason": …}` 를 보낸다** (3-8절). `succeeded`·`failed` 둘 다 이 한 자리로
받는다 — `POST /analyses`(적재)와는 별개다. 워커 배선은 미결 `ho` 18번에서 끝났다.

### ✅ 결정 — 리포트 읽기 경로는 DB에서 조립한다 (2026-09-09)

`metrics`·`report` 를 `POST /analyses` 로 받아 DB(`analysis_metric_value` ·
`analysis_report`)에 적재하고, **화면이 읽는 리포트는 그 DB에서 조립해 내보낸다.**
S3 의 분석 산출물(`report.json`)을 서버가 받아 점수만 걷어내고 그대로 돌려주는
방식(passthrough)은 **택하지 않는다.**

보안이 먼저이고 속도는 그다음이라는 기준으로 골랐다:

| | DB 조립 (택함) | S3 산출물 passthrough |
|---|---|---|
| 점수 노출 통제 | 응답을 명시적 DTO 로 조립 — 넣기로 한 필드만 나가는 **허용목록** | 상위에서 진화하는 JSON 에 **차단목록 필터** — 필드 하나 놓치면 조용히 유출 |
| 객체 저장소 | 완전히 서버 내부 | 서버가 매 요청마다 상위 문서를 프록시 |
| 3장 4)("리포트 본문에 수치 금지") | 구조적으로 보장 | 매 읽기 경로가 필터 버그 하나 거리 |
| 서빙 비용 | DB 쿼리 1회 | 매 요청 객체 저장소 GET |

**따라오는 것:**

1. **항목별 `stat`(0~100 연속값)도 `metrics` 로 적재한다.** 위에서 "총점과 항목별
   등급"만 명시했으나, 항목별 연속값이 화면에 필요하고(레이더 축 등) DB 조립이면
   그 값도 DB 에 있어야 S3 를 안 거친다. 코드 형식은
   `stat.{sport}.{motion}.{criterion_id}` — 등급 코드와 같은 축(루브릭 종속,
   아래 「항목별 등급」 참고).
2. **`impact_frame` 은 `metrics[]` 행이다**(예시의 `frame_index` 필드가 아니다).
   파이프라인이 `features` 에 스칼라(초)로 방출하므로 `metric_definition` 에 코드가
   있어야 하고, 없으면 적재가 통째로 `UNKNOWN_METRIC_CODE` 로 거부된다.
3. `metric_definition` 시드 규모: 측정 12 + `total_score` 1 + 항목별 등급 16 +
   항목별 `stat` 16 = **45개.** 코드·`label`·`unit` 의 정본과 산출 스크립트는
   `agent/contracts/metric_definitions.yaml` · `agent/scripts/export_metric_definitions.py`
   (미결 `jin` 23·25번). 🔴 **부분 시드 금지** — 전부 없으면 `POST /analyses` 가
   실서버에서 전부 거부된다. **✅ 시드 완료** (2026-09-10, 마이그레이션
   `ca31a2180b54`). draft 루브릭(73행)은 승격 시 그 루브릭의 행을 함께 넣는다.

### ✅ 적재 경로(흐름 B)·읽기 엔드포인트 — 구현됨 (2026-09-10, 미결 `jin` 27번)

적재는 **S3 `report.json` 하나를 입력으로** 한다. `POST /analyses` 로 `metrics[]`
배열을 통째로 받는 위 초안(2026-08-28)은 **폐기한다** — 워커가 같은 결과를 S3 와
요청 본문에 두 번 만들어야 해서 갈라진다(미결 `jin` 27번 표).

| | |
|---|---|
| 입력 | 완료 보고(`PATCH /internal/analysis-jobs/{id}`)의 `report_key`. 서버가 그 객체를 읽는다 — 워커는 DB 접속 정보를 모른다(위 「왜 DB에 직접 쓰지 않는가」 유지) |
| 트리거 | 완료 보고가 `succeeded` 로 작업 상태를 넘긴 **직후, best-effort**. 적재가 실패해도 완료 보고 자체는 성공이다(리포트를 화면이 못 찾을 뿐) |
| 스키마 | `report.json` 봉투 + `result` = `agent/report-contract.md`. `schema_version` 의 major 가 모르는 값이면 **적재 거부**(반쯤 적재 금지 — 어느 행이 낡은 스키마인지 사후 구분 불가) |
| 적재 대상 | `analysis_metric`(작업당 1, 루브릭 `sport`/`motion`/`version` 을 여기 둔다) · `analysis_metric_value`(측정 + `total_score` + `grade.*` + `stat.*` 행) · `analysis_metric_criterion`(항목별 `grade`·`title`·`band`·`out_of_band`·`evidence`·`metric_ref`·`weight`·`contribution`·`skipped` — 항목당 1행) · `analysis_report`(`summary`·`model_name`·`provisional`·`previews`·`keypoint_quality`·`schema_version`) |
| 재분석 | 같은 작업을 다시 적재하면 **앞의 것을 지우고 새로 넣는다**(`analysis_metric` CASCADE). 작업당 한 벌만 남는다 |
| 지표 코드 검증 | 쓰기 전에 모든 `metric_code` 를 `metric_definition` 과 대조 — 하나라도 없으면 `UnknownMetricCode` 로 통째 거부(부분 적재 없음) |

#### `GET /api/v1/videos/{video_id}/report`

그 영상의 적재된 분석 리포트. 자기 영상만. **DB 에서 명시적 DTO 로 조립한다** —
`report.json` passthrough 가 아니다(2026-09-09 결정).

`200 OK`

```json
{
  "video_id": "3f1c...",
  "analyzed_at": "2026-09-10T12:00:00Z",
  "summary": "디딤발 무릎 굽히기가 강점입니다.",
  "provisional": true,
  "total_score": 71,
  "overall_grade": "B",
  "breakdown": [
    { "criterion_id": "plant_knee_flexion", "name": "디딤발 무릎 굽히기",
      "grade": 2, "title": "흔들리지 않는 축",
      "evidence": "안정적으로 놓였습니다.", "stat": 88.5,
      "metric_ref": "plant_knee_angle_at_impact", "skipped": false },
    { "criterion_id": "plant_foot_position", "name": "디딤발 위치",
      "grade": null, "title": null, "evidence": null, "stat": null,
      "metric_ref": null, "skipped": true }
  ],
  "scenes": [
    { "metric_code": "impact_frame", "label": "임팩트 프레임", "at_seconds": 2.07 }
  ],
  "previews": { "impact": "s3://.../impact.png" },
  "keypoint_quality": { "known": true, "swing_side_valid_ratio": 0.9 }
}
```

🔴 **허용목록이다.** DB 에 있어도 여기 없는 것: `band`·`weight`·`contribution`·
`out_of_band`(검수 전 임계값 — 미결 `jin` 24번)·`view_dependent` — 전부 개발
확인용이다. **`total_score`·`overall_grade`·`breakdown[].stat` 는 나간다**
(2026-09-11 정정, 미결 `ho` 28번 — 이 문서가 앞서 "카드 경로가 따로 읽는다"고
적었던 것은 틀렸다. 계약 3장 4가 막은 것은 `summary` 문장 **안에** 숫자를 넣는
것이지 이 필드들 자체가 아니다). `grade` 가 `null` 이면 **제외(skipped)** 지
0점이 아니고, 그 항목의 `stat` 도 `null` 이다. `overall_grade` 는 `total_score`
와 마찬가지로 영상 하나(=분석 1회)의 값 — 선수 단위로 합친 오버롤은 없다.
옛 행(이 필드가 생기기 전 적재분)은 `total_score`/`overall_grade` 가 `null`.
`scenes` 는 프레임 지표(`impact_frame` 등)의 초 환산 — "이렇게 본 장면"으로
이동하는 자리다.

| 에러 | code | 언제 |
|---|---|---|
| 401 | `UNAUTHORIZED` | 토큰이 없거나 틀리다 |
| 404 | `VIDEO_NOT_FOUND` | 없는 영상이거나 남의 영상이다 |
| 404 | `ANALYSIS_FAILED` | 작업이 `failed`로 끝났다 — **다시 물어봐도 절대 안 생긴다.** `message`에 실패 사유(2026-09-11 추가, 사용자가 화면에서 실제로 겪음). 재촬영·재분석을 안내할 자리 |
| 404 | `REPORT_NOT_READY` | 영상은 있고 작업이 `queued`·`running`이라 아직 적재 전이다 — 다시 물어보면 될 수도 있다 |

🔴 **`ANALYSIS_FAILED`와 `REPORT_NOT_READY`를 같은 걸로 다루지 않는다** — 전자는
끝난 상태(재시도해도 안 바뀜), 후자는 진행 중(재시도하면 바뀔 수 있음)이다. 이
둘을 가르기 전에는 실패한 분석도 `REPORT_NOT_READY`로 나가서 화면이 "다시 확인"을
무한 반복시켰다.

### 🔴 지표 코드 실태 — 지금 스키마로는 루브릭을 담을 수 없다 (2026-09-01 조사)

`metric_definition`이 비어 있어서 "코드 목록의 주인"만 미정이라고 적어 뒀는데,
`agent/rubrics/`를 실제로 읽어 보니 **더 앞에서 막히는 문제**가 있다.

루브릭 5개(야구 투구 · 농구 점프슛 · 농구 레이업 · 축구 인사이드 패스 · 축구 인스텝
슛)가 참조하는 측정 지표는 **11개**인데, 그중 **5개가 종목을 넘나든다.**

| 지표 코드 | 쓰이는 종목 |
|---|---|
| `trunk_forward_lean_deg_at_impact` | **축구 · 야구 · 농구 (전부)** |
| `swing_elbow_angle_at_impact` | 야구 · 농구 |
| `swing_knee_angle_at_impact` | 농구 · 축구 |
| `plant_knee_angle_at_impact` | 야구 · 축구 |
| `swing_shoulder_flexion_after_impact_deg` | 야구 · 농구 |
| 나머지 6개 | 한 종목 전용 |

그런데 `metric_definition`은 **`code`가 기본키**이고 `sport_code`가 NOT NULL 단일
값이다. 같은 코드를 두 종목으로 정의할 수 없다 — 적혀 있는 제약이 아니라 **실제로
막는다.**

```
1) trunk_forward_lean_deg_at_impact / football  -> 들어감
2) trunk_forward_lean_deg_at_impact / baseball  -> 🔴 UniqueViolation
     duplicate key value violates unique constraint "metric_definition_pkey"
```

**항목별 등급도 같은 문제다.** 루브릭의 `criteria.id`가 등급 항목의 코드 후보인데
`release_arm_extension`·`follow_through`가 각각 3개 루브릭에, `trunk_lean` 등
5개가 2개 루브릭에 겹친다. 게다가 같은 이름이라도 **종목마다 기준이 다르다.**

#### 선택지 셋 — 정상호와 합의할 것

| 안 | 내용 | 대가 |
|---|---|---|
| **A (권고)** | `metric_definition.sport_code`를 **없앤다.** 지표는 물리량이고, 어느 종목에서 쓰는지는 루브릭이 안다 | 부록 D.3이 `sport` 외래키를 전제하므로 그 문서도 함께 고쳐야 한다 |
| B | 기본키를 **`(code, sport_code)` 복합키**로 | `analysis_metric_value`의 외래키가 두 컬럼이 되고, 제출할 때 종목을 항목마다 실어야 한다 |
| C | 코드에 **종목 접두어**를 붙인다 | 같은 물리량이 이름 3개가 된다. 값끼리 비교가 불가능해져 **선수 벡터·유사도 검색(SFR-005)에 직접 해롭다.** 루브릭도 전부 고쳐야 한다 |

A를 권하는 이유는 데이터가 이미 그렇게 말하고 있어서다 — 11개 중 5개가 공유되고
그중 하나는 전 종목 공통이다. **종목은 지표의 속성이 아니라 루브릭의 속성이다.**

> 참고: 이름 길이는 문제없다. 가장 긴 `swing_shoulder_flexion_after_impact_deg`가
> 39자로 `String(50)` 안에 들어간다. 다만 **C안은 접두어까지 붙으면 상한에 닿는다.**

#### ✅ 결정 — **A안** (정상호, 2026-09-08)

`metric_definition`에서 `sport_code`를 **없앤다.** 기본키는 `code` 그대로다.
루브릭 6개를 다시 세어 확인했고, **권고 당시보다 근거가 더 강해졌다.**

| | 2026-09-01 조사 (루브릭 5개) | **2026-09-08 재조사 (루브릭 6개)** |
|---|---|---|
| 지표 총수 | 11 | **11** (그대로) |
| 종목을 넘나드는 것 | 5 | **7** (11개 중 64%) |

늘어난 둘은 야구 타격 루브릭(`baseball_batting.yaml`, draft)이 기존 코드를 그대로
쓴 결과다 — `support_elbow_angle_at_impact`(야구·농구) ·
`plant_knee_angle_at_impact`(야구·축구). **새 종목을 열 때마다 공유가 늘어난다**는
뜻이고, 그것이 A안이 맞는 방향이라는 증거다.
`trunk_forward_lean_deg_at_impact`는 여전히 축구·야구·농구 전부에 쓰인다.

B·C를 안 고른 이유:

| | |
|---|---|
| **B(복합키)** | 부록 D의 **제2정규형 서술을 깬다** — "모든 테이블이 단일 컬럼 기본키를 쓴다. 복합키는 `review_selection` 하나뿐"이라고 적혀 있다. 게다가 **항목 코드 쪽에서는 아예 성립하지 않는다**(아래) |
| **C(종목 접두어)** | 제기하신 대로 선수 벡터·유사도 검색(SFR-005)에 직접 해롭다. 같은 물리량을 이름 3개로 쪼개면 종목 간 비교가 죽는다 |

🔴 **항목별 등급(`criteria.id`)은 `sport_code`로 못 가른다 — 같은 종목 안에서도
겹칩니다.** 이건 A·B·C 어느 쪽을 골라도 남는 별개 문제라 따로 적습니다.

```
follow_through        4개 루브릭  baseball_batting · basketball_jump_shot
                                  football_inside_pass · football_instep_shot
plant_foot_position   2개 루브릭  football_inside_pass · football_instep_shot   ← 둘 다 축구
swing_knee_extension  2개 루브릭  football_inside_pass · football_instep_shot   ← 둘 다 축구
trunk_lean            2개 루브릭  football_inside_pass · football_instep_shot   ← 둘 다 축구
trunk_alignment       2개 루브릭  basketball_jump_shot · basketball_layup       ← 둘 다 농구
```

항목 id 18개 중 8개가 2개 이상 루브릭에 겹치고, **그중 4개는 같은 종목의 서로 다른
동작**입니다. 축구 인사이드 패스의 `trunk_lean`과 인스텝 슛의 `trunk_lean`은 임계값이
다른 **다른 기준**입니다. 그래서 등급 항목의 식별자는 종목이 아니라 **루브릭**이
정해야 합니다 — `(rubric_code, criterion_code)`거나 루브릭 참조를 갖는 대리키입니다.
지표(물리량, 종목 무관)와 항목(기준, 루브릭 종속)은 **축이 반대**입니다.

동작 구분을 어디에 담을지는 같은 구역 17번(「클립의 **동작**을 담을 자리가 없습니다」)과
같은 문제라 그쪽에서 함께 봅니다.

**따라오는 조치**(에이전트 쪽에서 직접 하지 않은 것):

- 부록 D.3의 `metric_definition` 외래키 표(`sport_code → sport`)와 "종목별 지표
  항목" 설명 — **박민호 님 판단**으로 미결 `ho` 구역에 올렸습니다. 공개 제안서라
  제가 직접 고치지 않았습니다
- 스키마·마이그레이션은 **정어진 님 영역이라 손대지 않았습니다.** 이 문서에 결정만
  적습니다 → ✅ **2026-09-08 반영됨** (정어진, `5db18b239336`):
  `metric_definition_orm.py` 에서 `sport_code` 제거 +
  `op.drop_column("metric_definition","sport_code")`. 그 컬럼엔 외래키가 없었다.
  테이블이 0 행이라 컬럼 삭제로 끝. `alembic check` · downgrade 왕복 클린, 572 통과
- 지표 코드 목록의 주인은 제안하신 대로 **에이전트가 정의하고 백엔드가 따라가는**
  형태로 갑니다. 11개 코드·단위·설명은 `agent/rubrics/`에서 뽑아 시드용으로 냅니다

### 🔴 정해야 하는 것 — 합의 전에는 구현하지 않는다

| 무엇 | 왜 지금 못 정하나 |
|---|---|
| ~~**지표 코드의 종목 처리 (A·B·C)**~~ | ✅ **A안** (2026-09-08). 스키마 반영 완료(`5db18b239336`). 남은 것은 부록 D.3 수정(박민호, 미결 `ho` 구역)뿐이다 |
| ~~**서비스 인증 방식**~~ | ✅ `X-Worker-Token` 헤더 + `WORKER_TOKEN` 공유 시크릿(3-8절 · `core/deps.py` 의 `require_worker`). 비어 있으면 fail-closed(전부 401) |
| **지표 코드 목록의 주인** | ✅ **에이전트가 정의하고 백엔드가 따라간다** — `agent/` 의 `metric_definitions.yaml` 이 정본(정상호, 미결 `jin` 23번). 새 코드가 `metric_definition` 시드에 반영되는 경로는 미결 `jin` 25번에서 마무리 |
| ~~**실패 보고 경로**~~ | ✅ `PATCH /internal/analysis-jobs/{job_id}` 하나로 `succeeded`·`failed` 둘 다(3-8절, 미결 `ho` 18번) |
| **신뢰도(키포인트 품질)를 어디에 담나** | 3장 4)의 산출물 넷 중 하나다. 지표 항목으로 넣을지 별도 필드로 둘지 |

> ⚠️ 7장 칸반과 스프린트 1 로그에 **"측정값 MySQL 적재"** 라고 적혀 있는데,
> 이 프로젝트의 저장소는 **PostgreSQL + pgvector**다(부록 D). 표기를 바로잡아야 한다.

---

## 3-2. 회원 관리 (admin)

> **상태:** 구현됨 · 2026-08-31 추가
> **대상:** 관리자 화면(웹). 일반 사용자는 이 경로를 쓸 일이 없다.

`user` 테이블에 role 컬럼이 없어 관리자 여부는 `ADMIN_EMAILS`(환경변수, 쉼표 구분)
화이트리스트로 가른다. 위 세 엔드포인트 모두 `Authorization` 토큰의 주인 이메일이
그 목록에 있어야 통과한다 — 없거나 목록이 비어 있으면 `403 FORBIDDEN`이다.

### `GET /api/v1/admin/users`

`?q=`(이메일·닉네임 부분일치, 대소문자 무시) · `?page=`(기본 1) · `?size=`(기본 20, 최대 100).

**`q`는 패턴이 아니라 글자다.** `%`·`_`·`\`는 그대로 그 문자를 찾는다 — 와일드카드로
쓸 수 없다. 목록은 `created_at` 내림차순(최근 가입 순)이고, `total`은 페이지가 아니라
검색 결과 **전체**의 개수다.

`200 OK`

```json
{
  "items": [
    { "id": "3f1c...", "email": "demo@super-sub.example", "nickname": "홍길동",
      "created_at": "2026-07-13T10:30:00Z" }
  ],
  "total": 1,
  "page": 1,
  "size": 20
}
```

### `GET /api/v1/admin/users/{user_id}`

`GET /me`와 달리 **나간 팀도 포함한 소속 이력 전체**와 `has_card`를 준다.

`200 OK`

```json
{
  "id": "3f1c...", "email": "demo@super-sub.example", "nickname": "홍길동",
  "created_at": "2026-07-13T10:30:00Z",
  "teams": [
    { "team_id": "9a2e...", "name": "번개FC", "region": "서울 강남",
      "sport_code": "football", "role": "member",
      "joined_at": "2026-07-01T00:00:00Z", "left_at": null }
  ],
  "has_card": true
}
```

| 에러 | code |
|---|---|
| 404 | `USER_NOT_FOUND` |

### `DELETE /api/v1/admin/users/{user_id}`

강제 탈퇴. `DELETE /me`와 달리 **비밀번호를 요구하지 않는다** — 관리자 인증이
이미 그 자리를 대신한다. 파생 데이터가 외래키 연쇄로 함께 지워지는 것은 `DELETE /me`와
같다(부록 D.6). 지워진 계정의 토큰은 즉시 막힌다(`401 INVALID_TOKEN`).

🔴 **자기 자신은 이 경로로 지울 수 없다.** 지운 사람이 사라지면 감사 기록의 상대가
없어지고 되돌릴 방법도 없다. 관리자 본인의 탈퇴는 비밀번호를 확인하는 `DELETE /me`다.

비밀번호를 안 받는 대신 **누가 눌렀는지**를 서버 로그에 남긴다
(`event=admin_force_delete admin_id=… user_id=…`, 5장 SEC-010).

`204 No Content`

| 에러 | code |
|---|---|
| 404 | `USER_NOT_FOUND` |
| 409 | `CANNOT_DELETE_SELF` — 자기 자신을 대상으로 호출했다 |

### `GET /api/v1/admin/videos` — 한 사람의 영상 전부 (2026-09-08 추가)

미결 `jin` 24번. **문제 영상을 사람이 찾아 지우고, 에이전트가 제대로 돌았는지
확인**하는 자리다. 위 세 admin 경로와 같은 화이트리스트 게이트를 쓴다.

`?user=<uid|email>` **필수**. `user.id`(UUID)나 이메일(대소문자 무시) 중 하나로
사람을 짚는다. 없는 사람이면 `404 USER_NOT_FOUND`.

`GET /videos`(본인 목록)와 달리 **아직 저장 안 한(`kept:false`) 임시분까지** 담고,
최근 것이 앞에 온다.

`200 OK`

```json
{
  "user_id": "3f1c...", "nickname": "홍길동", "email": "demo@super-sub.example",
  "items": [
    { "id": "7c05...", "sport_code": "football",
      "original_filename": "My Kick.mp4",
      "storage_key": "videos/3f1c.../홍길동-My-Kick-20260908-1419-3f1c8a2b.mp4",
      "created_at": "2026-09-08T09:00:00Z",
      "kept": false, "is_public": false, "passed": true, "reject_reason": null,
      "analysis_status": "failed", "analysis_failure_reason": "품질 게이트 미달: …",
      "report_prefix": "reports/3f1c.../7c05.../" }
  ]
}
```

- `nickname`·`email` 은 **현재 값**이다(DB 조인). 저장 키 안의 닉네임 글자는
  업로드 시점에 얼어붙지만, 목록은 `user.id` 로 조인해 rename 을 따라간다.
- **재생·리포트 링크는 안 싣는다** — 목록 한 번에 객체마다 사전 서명을 하지
  않으려는 것이다. 재생은 `storage_key` 로, 리포트는 `report_prefix` 아래
  (`report.json`·`impact.jpg`·`tracked.webm`)를 콘솔이나 별도 사전 서명으로 짚는다.
- 🔴 **`analysis_failure_reason`** (2026-09-11 추가). `analysis_status`가
  `failed`일 때만 값이 있고, 그 외엔 `null`이다 — "에이전트가 제대로 돌았는지"를
  이 목록만으로 확인하려는 용도다(관리자 전용, `GET /videos`엔 없다).

### `DELETE /api/v1/admin/videos/{video_id}` — 관리자 영상 삭제 (2026-09-08 추가)

미결 `jin` 24번. **아무** 영상이나 지운다 — `DELETE /videos/{id}` 와 달리 소유를
확인하지 않는다(관리자 인증이 그 자리를 대신한다).

- **DB 행**과 연쇄(`video_validation`·`analysis_job`·그 하위, `ON DELETE CASCADE`).
- **S3 객체**(`storage_key` + `reports/<user_id>/<video_id>/`)도 best-effort 로
  지운다 — 실패해도 `204`. `DELETE /videos/{id}` 와 같다(EC2 역할에
  `s3:DeleteObject` 가 붙기 전에는 객체가 남는다 — 미결 `jin` 24번 IAM 조각).
- 비밀번호를 안 받는 대신 누가 눌렀는지 로그에 남긴다
  (`event=admin_delete_video admin_id=… video_id=…`).

`204 No Content`

| 에러 | code |
|---|---|
| 404 | `VIDEO_NOT_FOUND` |

---

## 3-3. 팀 (2026-09-02 추가)

동호회 팀을 만들고 사람이 드나든다. **경기 등록(SFR-010)의 선행**이고, 분석 적재와는
무관하게 돈다.

| | |
|---|---|
| 역할 | `owner`(만든 사람) · `member`. 부록 D 는 값을 열거하지 않아 **앱이 쓰는 집합**으로 정했다 |
| 가입 | **본인이 가입**하거나 **주장이 넣는다.** 초대·승인 테이블이 부록 D 에 없어 신청-승인 흐름은 넣지 않았다 |
| 탈퇴 | 행을 **지우지 않고** `left_at` 을 채운다(부록 D.6). 재가입은 새 행이라 이력이 남는다 |
| 종목 | `team` 이 정한다. 경기에 종목 컬럼을 두지 않고 `match → team → sport_code` 로 결정된다(부록 D.4) |

### `POST /api/v1/teams`

인증 필요. 팀을 만든다. **만든 사람이 `owner` 로 함께 들어간다.**

```json
{ "name": "번개FC", "region": "서울 강남", "sport_code": "football" }
```

`201 Created` — 아래 `GET /teams/{id}` 와 같은 형태.

| 에러 | code |
|---|---|
| 422 | `UNKNOWN_SPORT` — `sport` 에 없는 종목 코드다 |
| 422 | `VALIDATION_ERROR` — 이름·지역이 비었거나 너무 길다 |

> `team.sport_code` 에는 **외래키가 없다**(부록 D.3 의 외래키 표에 없어 늘리지 않았다).
> DB 가 막아 주지 않으므로 앱이 `sport` 를 조회해 막는다. 종목이 늘 때는 **앱 배포 없이
> 행만 넣으면** 되도록 고정 목록으로 두지 않았다.

### `GET /api/v1/teams/{team_id}`

인증 필요. 팀과 **현재 구성원**. 나간 사람은 담기지 않는다.

```json
{
  "id": "9a1e...", "name": "번개FC", "region": "서울 강남", "sport_code": "football",
  "members": [
    { "user_id": "3f1c...", "nickname": "홍길동", "role": "owner",
      "joined_at": "2026-09-02T01:00:00Z",
      "player_card_id": "7b2d...", "card_public_slug": "brave-tiger-1234" }
  ]
}
```

소속이 아니어도 볼 수 있다 — 가입하려면 먼저 봐야 하고, 담기는 것은 팀 정보와
구성원 닉네임뿐이다.

#### 카드 두 값 (2026-09-04 추가)

**구성원의 선수 카드를 가리킨다.** 스쿼드 등재(3-7절)가 `player_card_id` 를 받는데
그 값을 얻을 경로가 없었다 — 남의 카드는 슬러그를 알아야 열 수 있고 그 슬러그를
알 방법도 없었다(미결 `paik` 2번).

| 값 | 쓰는 곳 |
|---|---|
| `player_card_id` | **스쿼드 등재** — `POST /teams/{id}/squad/members` 가 받는 값 |
| `card_public_slug` | **카드로 가는 링크** — `GET /cards/{slug}` |

🔴 **카드가 없는 구성원은 둘 다 `null` 이고, 그래도 목록에 남는다.** 팀에는 여전히
있는 사람이다 — 걸러 내면 구성원 목록이 카드 목록이 되어 버린다.

| 에러 | code |
|---|---|
| 404 | `TEAM_NOT_FOUND` |

### `POST /api/v1/teams/{team_id}/members`

인증 필요. **본문을 비우면 본인이 가입**한다. `user_id` 를 담으면 주장이 남을 넣는다.

```json
{ "user_id": "3f1c..." }
```

`201 Created` — 갱신된 팀(위와 같은 형태).

| 에러 | code |
|---|---|
| 403 | `FORBIDDEN` — 주장이 아닌데 남을 넣으려 했다 |
| 404 | `TEAM_NOT_FOUND` · `USER_NOT_FOUND` |
| 409 | `ALREADY_MEMBER` — 이미 이 팀의 구성원이다 |

### `DELETE /api/v1/teams/{team_id}/members/{member_id}`

인증 필요. 본인이면 탈퇴, 주장이면 방출. `204 No Content`.

| 에러 | code |
|---|---|
| 403 | `FORBIDDEN` — 주장이 아닌데 남을 빼려 했다 |
| 404 | `TEAM_NOT_FOUND` · `NOT_A_MEMBER` |
| 409 | `LAST_OWNER` — 마지막 주장은 나갈 수 없다 |

🔴 **마지막 주장이 나가면 아무도 남을 넣을 수 없는 팀이 된다.** 소유권 이양 API 가
아직 없어 되돌릴 방법이 없으므로 미리 막는다. 팀 해체도 같은 이유로 아직 없다 —
필요해지면 이양과 함께 낸다.

---

## 3-4. 경기 등록 (2026-09-02 추가)

팀이 경기를 열고 **필요한 포지션과 인원**을 함께 적는다(SFR-010). 지원·적합도·추천
(`match_application` · `fitness_score` · `recommendation`)은 다음 단계다.

| | |
|---|---|
| 누가 | **주장(`owner`)만** 등록한다. 상대 팀·지원자에게 이 팀의 약속이 되기 때문이다 |
| 종목 | **경기에 종목이 없다.** 주최 팀이 결정한다(부록 D.4 — 컬럼을 두면 "중복이자 모순 가능성") |
| 포지션 | 문자열 한 컬럼이 아니라 **행으로** 나눈다(`match_position_need`). 경기당 포지션 1행이다 |

### `POST /api/v1/teams/{team_id}/matches`

인증 필요. 주장만.

```json
{
  "played_at": "2026-09-10T19:00:00+09:00",
  "place": "강남 풋살장 2구장",
  "needs": [
    { "position_code": "GK", "head_count": 1 },
    { "position_code": "FW", "head_count": 2 }
  ]
}
```

`201 Created` — 아래 `GET /matches/{id}` 와 같은 형태.

| 에러 | code |
|---|---|
| 403 | `FORBIDDEN` — 주장이 아니다(소속이 아닌 경우도 포함) |
| 404 | `TEAM_NOT_FOUND` |
| 422 | `PAST_MATCH` — 지난 시각이다 |
| 422 | `UNKNOWN_POSITION` — **이 팀 종목에** 없는 포지션 코드다 |
| 422 | `DUPLICATE_POSITION` — 같은 포지션을 두 번 적었다 |
| 422 | `VALIDATION_ERROR` — 인원이 1 미만이거나 `needs` 가 비었다 |

🔴 **포지션 코드는 종목 안에서만 뜻이 있다.** 야구의 `C` 는 포수, 농구의 `C` 는
센터다. 그래서 코드만으로 찾지 않고 **팀 종목으로 좁혀서** 찾는다 — 축구 팀에 `P`
(투수)를 적으면 `UNKNOWN_POSITION` 이다.

### `GET /api/v1/teams/{team_id}/matches` (2026-09-02 추가)

인증 필요. 그 팀의 **다가오는** 경기. 이른 것이 앞에 온다. 소속이 아니어도 본다 —
모집 글이라 지원할 사람이 봐야 한다.

`200 OK` — 아래 `GET /matches/{id}` 와 같은 형태의 배열. 필요 포지션도 함께 온다.

| 에러 | code |
|---|---|
| 404 | `TEAM_NOT_FOUND` — **빈 배열이 아니다.** 오타 난 id 를 "경기가 없구나"로 읽으면 안 된다 |

🔴 **지난 경기는 목록에서 빠진다.** 등록은 미래만 되지만 그 뒤로 시간이 흐른다.
기록이 사라지는 것은 아니라서 `GET /matches/{id}` 로는 여전히 읽힌다.

### `GET /api/v1/matches/{match_id}`

인증 필요. 모집 글이라 소속이 아니어도 본다.

```json
{
  "id": "5c2a...", "team_id": "9a1e...",
  "played_at": "2026-09-10T10:00:00Z",
  "place": "강남 풋살장 2구장",
  "needs": [
    { "position_code": "FW", "position_label": "공격수", "head_count": 2 },
    { "position_code": "GK", "position_label": "골키퍼", "head_count": 1 }
  ]
}
```

| 에러 | code |
|---|---|
| 404 | `MATCH_NOT_FOUND` |

### `GET /api/v1/matches` — 경기 탐색 (2026-09-03 추가)

🔴 **팀 id 를 몰라도 되는 유일한 경로다.** 다른 목록은 그 팀을 이미 알아야 하므로,
이것이 생기기 전에는 **용병이 지원할 경기를 찾을 방법이 없었다.**

```
GET /api/v1/matches?sport_code=football&region=서울&page=1&size=20
```

| 파라미터 | 기본 | 뜻 |
|---|---|---|
| `sport_code` | 전체 | 종목. 실재하지 않으면 **422** 다 |
| `region` | 전체 | 팀 지역. **부분 일치**이고 대소문자를 가리지 않는다 |
| `page` | 1 | 1부터 |
| `size` | 20 | 1~100 |

`200 OK`

```json
{
  "items": [
    {
      "id": "7c05...",
      "team_id": "3f1c...",
      "team_name": "강남FC",
      "region": "서울 강남구",
      "sport_code": "football",
      "played_at": "2026-09-10T19:00:00Z",
      "place": "강남 풋살장 2구장",
      "needs": [
        { "position_code": "GK", "position_label": "골키퍼", "head_count": 1 }
      ]
    }
  ],
  "total": 3,
  "page": 1,
  "size": 20
}
```

**팀 이름·지역·종목이 함께 온다.** 용병이 경기를 고르는 기준이 그 셋이라, 없으면
화면이 팀을 한 건씩 다시 물어야 한다. 페이지 형식은 `GET /admin/users` 와 같다 —
형식이 갈리면 클라이언트가 페이지 처리를 두 벌 짜야 한다.

🔴 **다가오는 경기만 담긴다.** 이른 것이 앞에 온다 — 목록은 모집 글이고 임박한
것이 급하다. 지난 경기도 `GET /matches/{id}` 로는 여전히 읽힌다.

**종목 코드가 틀리면 빈 배열이 아니라 422 다.** 빈 배열로 답하면 오타와 "그 종목
경기가 없다"가 같아 보여서, 사용자가 없는 것을 계속 기다리게 된다. 반면 **지역은
자유 문자열이라 검증할 대상이 없어** 안 걸리면 그냥 빈 목록이다.

| 에러 | code | 언제 |
|---|---|---|
| 422 | `UNKNOWN_SPORT` | 지원하지 않는 종목 코드 |
| 422 | `VALIDATION_ERROR` | `page < 1` · `size > 100` 등 |

### `PATCH /api/v1/matches/{match_id}` — 수정 (2026-09-03 추가)

**주장만.** 보낸 항목만 바뀐다.

```json
{ "played_at": "2026-09-12T19:00:00+09:00", "place": "옮긴 구장",
  "needs": [{ "position_code": "DF", "head_count": 2 }] }
```

`200 OK` — `GET /matches/{id}` 와 같은 모양으로 **고쳐진 경기 전체**를 돌려준다.

셋 다 선택이고 **`null` 은 "안 바꾼다"** 는 뜻이다. 시각·장소·필요 포지션은 비울 수
있는 값이 아니라, "안 보냄"과 "null 로 지움"을 가르지 않았다.

🔴 **`needs` 를 보내면 통째로 갈아 끼운다.** 부분 갱신은 "어느 포지션을 빼라"를
표현할 방법이 없어 뜻이 애매해진다. 보낼 거면 **남길 것까지 전부** 보낸다.

| 에러 | code | 언제 |
|---|---|---|
| 403 | `FORBIDDEN` | 주장이 아니다 |
| 404 | `MATCH_NOT_FOUND` | 경기가 없다 |
| 422 | `PAST_MATCH` | **지난 경기**를 고치려 하거나, **과거 시각**으로 옮기려 한다 |
| 422 | `DUPLICATE_POSITION` · `UNKNOWN_POSITION` | 등록과 **같은 검증**이다 |

⚠️ **지원자가 있어도 막지 않는다.** 막아 버리면 오타 하나를 못 고치게 되고 그쪽이
더 나쁘다. 대신 **지원자에게 알림이 가지 않는다** — 알림 인프라가 없다. 시각·장소를
바꾸면 **사람이 따로 알려야 한다.**

### `DELETE /api/v1/matches/{match_id}` — 취소 (2026-09-03 추가)

**주장만.** `204 No Content`.

🔴 **취소는 행 삭제다.** 부록 D 의 `match` 에는 상태 컬럼이 없고 D.8 도 취소를
다루지 않아 **`canceled_at` 을 늘리지 않았다.** 대신 스키마가 이미 말하고 있는 것을
따른다 — `match_application` 의 삭제 규칙이 RESTRICT 라 **지원이 붙은 경기는 DB 가
못 지우게 한다.**

| 에러 | code | 언제 |
|---|---|---|
| 403 | `FORBIDDEN` | 주장이 아니다 |
| 404 | `MATCH_NOT_FOUND` | 경기가 없다 |
| 409 | `MATCH_HAS_APPLICATIONS` | **지원·제안이 하나라도 있다** |
| 422 | `PAST_MATCH` | 지난 경기. 이미 열린 경기를 "취소"하는 것은 뜻이 없다 |

**409 가 오면 지원을 먼저 정리한다** — 3-5절
`DELETE /matches/{match_id}/applications/{application_id}` 로 하나씩 없앤 뒤 다시
취소한다. 주장은 그 경로로 거절할 수 있다(2026-09-04 추가).

⚠️ **한 번에 지우는 경로는 일부러 두지 않았다.** 지원자에게 알림이 가지 않으므로
**사람이 건별로 정리하는 편**이 맞다고 봤다. 알림이 생기면 다시 본다.

### 아직 없는 것

- ~~**지원 취소·거절**~~ ✅ **2026-09-04 에 넣었다** — 3-5절
  `DELETE /matches/{match_id}/applications/{application_id}`. 지원을 전부 없애면
  **위 409 가 풀린다.** 미결 `jin` 16번에서 A-1(거절 = 행 삭제)로 정했다
- **알림** — 경기가 바뀌거나 취소될 때 지원자에게 알릴 인프라가 없다
- **경기 탐색의 포지션 필터** — "골키퍼를 구하는 경기만". 지금은 `needs` 가 응답에
  실려 오므로 화면에서 거를 수 있다. 목록이 길어지면 서버에서 좁힌다
- **탐색의 날짜 범위** — 지금은 "다가오는 전부"다
- **적합도·추천** — SFR-006·007. 도메인 ④ 의 나머지 둘이다

### 포지션 목록은 마이그레이션이 넣는다

`position` 은 08-31 에 **빈 테이블**로 만들어 두고 "참조하는 쪽이 들어올 때 채운다"고
적어 두었다. `match_position_need` 가 그 참조라 `20260902_match_tables` 가 채웠다.

| 종목 | 코드 |
|---|---|
| `football` | `GK` 골키퍼 · `DF` 수비수 · `MF` 미드필더 · `FW` 공격수 |
| `baseball` | `P` 투수 · `C` 포수 · `IF` 내야수 · `OF` 외야수 |
| `basketball` | `G` 가드 · `F` 포워드 · `C` 센터 |

**확정된 목록이 아니다.** 스쿼드(`squad_member`)가 들어올 때 세분화가 필요하면 늘린다.

### `GET /api/v1/positions` — 포지션 목록 (2026-09-09 추가)

위 표를 **API 로** 준다. 지금 스쿼드 등재·경기 `needs`·챗봇 화면이 이 목록을
**하드코딩**하고 있어서, 마이그레이션이 바뀌면 조용히 낡는다. 그 자리를 이걸로
갈아 끼운다. **로그인하면 누구나** — 참조 데이터라 사용자별 내용이 없다.

```
GET /api/v1/positions              → 전 종목
GET /api/v1/positions?sport_code=football
```

```json
[
  { "sport_code": "football", "code": "DF", "label": "수비수" },
  { "sport_code": "football", "code": "FW", "label": "공격수" }
]
```

`sport_code` 순으로 정렬돼 온다. 🔴 **약칭(`code`)은 종목 안에서만 유일**하다 —
야구 `C`(포수)와 농구 `C`(센터)는 다른 것이라 둘 다 실린다.

| 에러 | code | 언제 |
|---|---|---|
| 422 | `UNKNOWN_SPORT` | `sport_code` 필터가 `sport` 에 없는 값이다 — 빈 배열이면 오타와 "그 종목 포지션이 아직 없다"가 같아 보인다(`GET /matches` 와 같은 판단) |

---

## 3-5. 지원과 제안 (2026-09-02 추가)

경기 1건에 대한 한 사람의 지원 1건이다. **사람이 지원**하거나 **팀이 제안**하고,
**양쪽이 다 수락해야 확정**이다.

### 🔴 상태값이 없다 — 두 시각으로 읽는다

부록 D.5 의 「매칭 확정은 사람이 한다」를 스키마로 강제한 자리다. `status` 하나로
두면 확정 조건이 코드에만 남는다.

| 채워진 것 | 뜻 |
|---|---|
| `user_accepted_at` 만 | 사람이 **지원**했다. 팀의 수락을 기다린다 |
| `team_accepted_at` 만 | 팀이 **제안**했다. 그 사람의 수락을 기다린다 |
| 둘 다 | **확정** (`confirmed: true`) |

`confirmed` 는 **서버가 계산해서 내려준다.** 두 시각만 주고 클라이언트가 판단하게
두면 확정 조건이 화면마다 갈린다.

### `POST /api/v1/matches/{match_id}/applications`

인증 필요. **본문을 비우면 본인이 지원**한다. `user_id` 를 담으면 주장이 제안한다.

```json
{ "user_id": "3f1c..." }
```

`201 Created`

```json
{
  "id": "8d2f...", "match_id": "5c2a...", "user_id": "3f1c...",
  "nickname": "홍길동",
  "team_accepted_at": null,
  "user_accepted_at": "2026-09-02T05:00:00Z",
  "confirmed": false
}
```

| 에러 | code |
|---|---|
| 403 | `FORBIDDEN` — 주장이 아닌데 남을 제안했다 |
| 404 | `MATCH_NOT_FOUND` · `USER_NOT_FOUND` |
| 409 | `ALREADY_APPLIED` — 경기당 1인 1건이다(부록 D.7) |
| 409 | `TEAM_MEMBER_CANNOT_APPLY` — **그 팀 소속**이다 |
| 422 | `PAST_MATCH` — 이미 지난 경기다 |

> `TEAM_MEMBER_CANNOT_APPLY` 는 **앱이 정한 규칙**이다. 이 서비스는 팀에 없는 사람을
> 부르는 용병 매칭이라(1장) 소속 선수의 "지원"은 뜻이 없고 적합도(SFR-006)도 외부인
> 기준으로 계산된다. 팀 내부 참가 신청까지 담게 되면 `application_rules.can_apply`
> 를 고친다.

### `POST /api/v1/matches/{match_id}/applications/{application_id}/accept`

인증 필요. **비어 있는 반대쪽**을 채운다. 둘 다 차면 `confirmed` 가 참이 된다.

`200 OK` — 위와 같은 형태.

| 에러 | code |
|---|---|
| 403 | `FORBIDDEN` — 이 건과 무관한 사람이다 |
| 404 | `MATCH_NOT_FOUND` · `APPLICATION_NOT_FOUND` |
| 409 | `ALREADY_ACCEPTED` — 자기 쪽은 이미 차 있다 |

🔴 **무관한 사람에게 404 가 아니라 403 을 준다.** 404 로 주면 "그 id 의 지원 건이
있는가"가 응답으로 새어 나간다. 반대로 **없는 id 는 404** 다 — 관계된 사람에게는
없다는 사실을 알려야 한다.

### `DELETE /api/v1/matches/{match_id}/applications/{application_id}` — 무르기·거절 (2026-09-04 추가)

인증 필요. **지원 당사자가 부르면 무르기, 주최 팀 주장이 부르면 거절**이고, 둘 다
**행을 지운다.** 한 경로로 둔 이유는 하는 일이 같아서다 — 누가 부르느냐만 다르다.

`204 No Content` — 본문 없음.

| 에러 | code |
|---|---|
| 403 | `FORBIDDEN` — 당사자도 주장도 아니다 |
| 404 | `MATCH_NOT_FOUND` · `APPLICATION_NOT_FOUND` |
| 422 | `PAST_MATCH` — 지난 경기의 지원은 무를 수 없다 |

🔴 **이것이 3-4절 `DELETE /matches/{match_id}` 의 409(`MATCH_HAS_APPLICATIONS`)를
푸는 길이다.** 지원을 전부 없애면 경기를 취소할 수 있다.

> **왜 거절을 시각 컬럼으로 담지 않았나** — 미결 `jin` 16번에서 **A-1** 로 정했다.
> `match_application.match_id` 가 RESTRICT 라 **행이 남아 있으면 경기를 못 지운다.**
> 거절 시각 컬럼을 늘리면 부록 D 를 고치고도 그 막다른 곳이 그대로다.

⚠️ **거절 이력이 남지 않는다.** 나중에 필요해지면 **컬럼이 아니라 별도 테이블**이어야
한다 — 행이 남으면 같은 문제가 돌아온다.

⚠️ **상대에게 알림이 가지 않는다.** 알림 인프라가 없다(아래 「아직 없는 것」).

🔴 **지난 경기에서는 422 다.** 두 수락 시각이 다 찬 행이 **"누가 그 경기에 뛰었나"의
유일한 근거**라, 지우면 평가(SFR-008 · 부록 D 도메인 「평가·신뢰」)가 대상을 잃는다.
**확정된 건이라도 경기 전에는 없앨 수 있다** — 그렇지 않으면 취소가 다시 막힌다.

### `GET /api/v1/matches/{match_id}/applications`

인증 필요. **주장은 전부, 그 외에는 자기 건만** 본다 — 지원자 명단은 팀의 정보다.
먼저 시작된 건이 앞에 온다(`created_at` 이 없으므로 먼저 찬 수락 시각으로 센다).

`200 OK` — 위 형태의 배열.

### 아직 없는 것

- ~~**취소·거절**~~ ✅ **2026-09-04 에 넣었다** — 위
  `DELETE /matches/{match_id}/applications/{application_id}`. 미결 `jin` 16번에서
  **A-1**(거절 = 행 삭제)로 정했고, 그래서 3-4절의 409 도 함께 풀렸다
- **적합도**(`fitness_score`, SFR-006) · **추천**(`recommendation`, SFR-007) —
  도메인 ④ 의 나머지 둘
- 확정 뒤의 알림 — 알림 인프라가 없다

---

## 3-6. 클립 업로드 (2026-09-03 추가)

SFR-001. 사용자가 자기 클립을 올리고, 서버가 규격을 검사해 **반려 사유를 값으로
남기는** 경로다.

> **상태:** 구현됨 · 2026-09-03
> **확인:** `git grep -n "video_validation" -- fastapi/app` → 결과가 있으면 들어왔다

### 두 번에 나눠 부른다

```
(1) POST /videos/upload-url   올릴 자리를 받는다  -> storage_key · upload_url
(2) PUT  <upload_url>          S3 에 직접 올린다   (앱 서버를 지나지 않는다)
(3) POST /videos               등록하고 검사한다   -> passed · reject_reason
```

원본이 앱 서버를 지나지 않는 것이 PER-002 다. 서버가 아는 것은 **키와 크기**뿐이다.

### 🔴 반려는 실패가 아니다 — `201` 이다

규격에 안 맞는 클립을 422 로 돌려보내면 **사유가 아무 데도 안 남는다.** SFR-001 이
요구하는 것은 그 반대다. 그래서 반려도 `201 Created` 로 답하고 `passed: false` 와
사유를 본문에 싣는다. **등록은 성공했고, 그 클립이 분석 대상이 아닐 뿐이다.**

클라이언트는 **`passed` 로 분기한다.** 상태 코드로 분기하면 반려를 놓친다.

422 로 내는 것은 등록 자체가 성립하지 않는 경우뿐이다 — 종목이 없다, 파일이 안
올라와 있다, 남의 저장 키다.

### 상한 (2026-09-03 결정)

| 항목 | 값 |
|---|---|
| 용량 | 200MB |
| 길이 | 60초 |
| 해상도 | 긴 변 3840 · 짧은 변 2160(4K, 방향 무관) — **`analyze: true` 일 때만** (2026-09-11 정정) |
| 형식 | `video/mp4` · `video/quicktime` |

**해상도 상한은 분석 워커의 메모리 예산을 지키는 값이다**(`ho` 9번). `analyze:
false` 기록용 업로드에는 걸지 않는다 — 그 클립은 워커를 지나지 않는다.

🔴 **정정 (2026-09-11)**: 여기 적혀 있던 "1920x1080, `ho` 9번이 풀리면 상한을
올린다"는 예고 그대로 실행이 안 된 상태였다 — `ho` 9번은 2026-09-08에 이미
4K(2160×3840, 300프레임)를 실측 기준으로 안전하다고 확정했는데, 이 상한만 안
풀려 있었다(사용자가 화면에서 발견). 이제 그 기준까지 허용한다. **곁가지**:
옛 상한이 `width`·`height`를 그대로 비교해서, 4K와 무관하게 **세로로 찍은
보통 1080p 영상(1080×1920)도 방향 때문에 반려되고 있었다** — 같이 풀렸다.
용량·길이는 저장소·비용에 걸린 것이라 `analyze` 와 무관하다.

🔴 **길이 상한이 에이전트의 프레임 상한과 아직 안 맞는다.**
`agent/src/supersub_agent/pose.py` 의
`max_frames=300` 은 `target_fps=15` 기준 **20초분**이라 60초 클립은 앞 20초만
분석된다. 미결 항목으로 올렸다 — 정해지면 여기 값이 바뀐다.

### `POST /api/v1/videos/upload-url`

```json
{ "content_type": "video/mp4", "size_bytes": 52428800, "filename": "우리팀 첫 골.mp4" }
```

`filename` 은 **원본 파일 이름**이다(2026-09-08 추가, 미결 `jin` 24번). 저장 키를
사람이 알아볼 수 있게 짓는 데 쓴다 — 슬러그화되므로 공백·문장부호·이모지가
들어와도 안전하다.

`200 OK`

```json
{
  "storage_key": "videos/3f1c8a2b-…/업로더-우리팀-첫-골-20260908-1419-9a2e0c11.mp4",
  "upload_url": "https://<bucket>.s3.<region>.amazonaws.com/...",
  "expires_in": 900
}
```

`storage_key` 는 `videos/<user_id>/<닉네임 슬러그>-<원본이름 슬러그>-<YYYYMMDD-HHMM>-<8자>.<ext>`
다. 🔴 **`<user_id>/` 접두사(UUID)는 그대로다** — 등록할 때 소유를 대조하고,
닉네임이 바뀌어도 이 UUID 로 주인을 되짚는다. 닉네임 조각은 **업로드 시점 라벨**
이라 rename 해도 옛 키는 안 바뀐다. 클라이언트는 이 값을 **그대로** `POST /videos`
에 넘긴다 — 뜯어보지 않는다.

🔴 **`upload_url` 에 PUT 할 때 `Content-Type` 을 요청한 값 그대로 보내야 한다.**
서명에 들어 있어서 다르면 S3 가 거절한다.

⚠️ **이 URL 은 용량 상한을 강제하지 못한다.** 사전 서명 PUT 은 크기를 조건으로 걸
수 없다. `size_bytes` 는 헛걸음을 줄이려고 미리 받는 값이고, 진짜 상한은 등록할 때
저장소에 물어 **실측으로** 건다.

| 에러 | code | 언제 |
|---|---|---|
| 422 | `UNSUPPORTED_FORMAT` | 받지 않는 형식 |
| 422 | `FILE_TOO_LARGE` | `size_bytes` 가 상한을 넘는다 |
| 503 | `STORAGE_NOT_CONFIGURED` | 서버에 `S3_BUCKET` 이 없다 |

### `POST /api/v1/videos`

```json
{
  "sport_code": "football",
  "storage_key": "videos/3f1c.../9a2e....mp4",
  "duration_ms": 10200,
  "width": 1920,
  "height": 1080,
  "side": "right",
  "analyze": true,
  "filename": "우리팀 첫 골.mp4",
  "subject_box": [0.39, 0.35, 0.12, 0.4],
  "subject_at_ms": 4200,
  "focus": ["follow_through", "guide_hand"]
}
```

`filename` 은 **원본 이름**이다 — DB `video.original_filename` 에 온전히 남긴다
(저장 키 슬러그는 손실적이다). 관리자 목록이 이 값으로 "문제 영상"을 되짚는다.
생략 가능(`null`).

`subject_box`·`subject_at_ms` 는 「이 사람으로 분석」 대상이다(미결 `paik` 6번).
`subject_box` 는 정규화 `[x, y, w, h]` (0~1) — **화면 픽셀이 아니다.** `subject_at_ms`
는 그 박스를 그린 영상 시각(ms). 응답에는 실리지 않는다(분석 작업의 값이라
`claim` 응답으로 나간다 — 3-8절).

| 규칙 | |
|---|---|
| 🔴 정규화만 | `x·y·w·h` 가 `[0, 1]` 밖이면 422. 조용히 클램프하면 엉뚱한 사람을 분석하고도 "지정대로"라 답한다 |
| 🔴 함께 or 생략 | 박스만 주고 시각을 안 주면(또는 반대) 422 |
| 기하 | `w·h > 0`, `x+w ≤ 1`, `y+h ≤ 1`. `subject_at_ms ≤ duration_ms` |
| 🔴 없어도 된다 | 생략하면 「자동으로 고르기」다 — **실패로 만들지 않는다** |
| 작업이 없으면 | `analyze: false` 거나 반려면 박스는 버려진다(담을 작업 행이 없다). 이것도 실패가 아니다 |

`focus` 는 「어디를 집중해서 볼지」다(미결 `paik` 8번) — 루브릭 `criteria[].id`
목록(예: `["follow_through", "guide_hand"]`). `subject_box` 와 같이 `claim` 응답으로
워커에 흘러간다(`--focus`).

| 규칙 | |
|---|---|
| 🔴 빈 목록·생략 = 「전체적으로」 | 기본이자 가장 흔한 경우 — **실패로 만들지 않는다** |
| 형식 | 문자열 리스트. 서버가 공백·중복을 정리한다. 항목 40자·목록 24개 상한. 값의 실재(그 루브릭에 있는 id 인지)는 서버가 못 본다 — 루브릭은 `agent/` |
| 작업이 없으면 | `subject_box` 와 같다 — 버려진다, 실패 아님 |

`201 Created`

```json
{
  "id": "7c05...",
  "sport_code": "football",
  "storage_key": "videos/3f1c.../9a2e....mp4",
  "duration_ms": 10200,
  "side": "right",
  "created_at": "2026-09-03T09:00:00Z",
  "passed": true,
  "reject_reason": null,
  "analysis_job_id": "9a2e...",
  "analysis_status": "queued",
  "is_public": false,
  "is_featured": false,
  "title": null,
  "description": null,
  "kept": false
}
```

반려면 `passed: false` · `reject_reason: "해상도가 상한을 넘습니다: 7680x4320
(상한 긴 변 3840 · 짧은 변 2160)"` · `analysis_job_id: null` 이다. **반려된
클립은 분석하지 않는다** —
규격 검사를 두는 이유가 그것이다.

`kept` 는 **프로필에 저장됐는가**다(미결 `jin` 24번 5조각 해소, 2026-09-11).
`GET /videos`(본인 목록) · 공개 목록 둘 다 `kept: true` 만 준다. **작업이 생긴
클립만 등록 시 `kept: false` 로 시작한다** — `analyze: false`(기록용 업로드)와
반려된 클립(작업이 안 생긴다)은 처음부터 `kept: true` 다. 임시 클립은 아래
`POST /videos/{id}/keep` 을 불러야 영구가 된다 — 그전까지는 화면을 벗어나면
곧 `DELETE /videos/{id}` 가, 그것도 놓치면 `PROVISIONAL_VIDEO_TTL_HOURS`
백스톱이 지운다(2164줄 참고) — **분석에 실패해 다시 볼 리포트가 없는 클립을
DB·S3 에 남기지 않으려는 것**이다(사용자가 화면에서 직접 지적).

`is_public`·`title`·`description` 은 **등록 시 정할 수 없다** — 각각 `false`·`null`
로 저장된다(미결 `paik` 5번). 바꾸는 것은 아래 `PATCH /videos/{id}` 다.

`duration_ms`·`width`·`height` 는 **클라이언트가 잰 값**이다. 서버가 다시 재려면
원본을 내려받아야 하고 그러면 PER-002 가 무너진다. 용량만은 저장소에 물어 실측한다.

`side` 는 던지는 팔·차는 발이다. 자동 판별이 팔 종목에서 신뢰할 수 없어(5장
CON-007) 사람이 지정할 수 있게 열어 둔다. 생략하면 에이전트의 자동 판별을 쓴다.

`analyze` 는 **생략하면 참**이다(안 보내던 클라이언트의 동작이 그대로다).
`false` 로 보내면 **규격은 검사하되 분석 작업을 만들지 않는다** — `passed` 는
그대로 오고 `analysis_job_id`·`analysis_status` 가 `null` 이다. 기록으로
남기려고 올리는 클립("업로드 영상")과 실력을 재려고 올리는 클립을 가르는
자리다(미결 `paik` 4번). 반려된 클립은 `analyze` 와 무관하게 작업이 없다.

| 에러 | code | 언제 |
|---|---|---|
| 403 | `FORBIDDEN` | 남에게 발급된 저장 키다 |
| 422 | `UNKNOWN_SPORT` | 지원하지 않는 종목 코드 |
| 422 | `FILE_NOT_UPLOADED` | 그 키에 올라온 파일이 없다 |
| 503 | `STORAGE_NOT_CONFIGURED` | 서버에 `S3_BUCKET` 이 없다 |

**저장 키에 업로더가 들어 있다**(`videos/<user_id>/<uuid>.<확장자>`). 등록할 때 그
접두사를 대조하므로 남이 올린 객체를 자기 영상으로 등록할 수 없다.

### `GET /api/v1/videos`

내 영상 목록. **최근 것이 앞에 온다.** 한 줄의 모양은 `POST /videos` 응답과 같다
(`is_public` 포함).

`analysis_status` 는 그 영상의 **가장 최근** 분석 작업 상태다(`queued` · `running` ·
`succeeded` · `failed`). 같은 영상을 다시 분석하면 작업이 여러 건이 되는데 목록은
최근 것만 보여준다. 반려된 클립은 작업이 없어 `null` 이다.

플러터 `/videos` 화면(영상 상세 펼침 + 규격 반려 사유 바텀시트)이 이 응답 하나로
그려진다.

### `PATCH /api/v1/videos/{video_id}` — 부분 수정 (2026-09-08 추가)

미결 `paik` 5번. **자기 클립**의 공개 여부·제목·한 줄 설명·대표 여부를 바꾼다.

```json
{ "is_public": true, "title": "우리 팀 첫 골", "description": "왼발 감아차기" }
{ "is_featured": true }
```

- **전부 생략 가능하다 — 보낸 것만 바뀐다.** 안 보낸 필드는 그대로다
- `title` 100자 · `description` 280자. **`null` 이나 공백만 보내면 지운다**
  (`PATCH /me/card` 의 `tagline` 과 같은 규칙). `is_public`·`is_featured` 는
  불리언이라 `null` 은 무시한다
- `is_featured: true` — **「나를 보여주는 대표 영상」**(미결 `paik` 10번)으로 세운다.
  🔴 **사람당 하나** — 세우면 그 사람의 다른 대표는 자동으로 내려간다(DB 부분
  유일 인덱스). 🔴 **반려된 클립(`passed: false`)은 대표가 될 수 없다** →
  `422 CANNOT_FEATURE`. 내리려면 `is_featured: false`
- `200 OK` — 응답은 `GET /videos` 한 줄과 같은 모양(바뀐 값이 실려 온다).
  `is_featured` 도 그 줄에 실린다

| 에러 | code | 언제 |
|---|---|---|
| 404 | `VIDEO_NOT_FOUND` | 없는 클립이거나 **남의 클립**이다 — 존재 여부를 구별해 주지 않는다 |
| 422 | `CANNOT_FEATURE` | 반려된 클립을 대표로 세우려 했다 |
| 422 | `VALIDATION_ERROR` | `title`·`description` 이 길이 상한을 넘는다 |

### `GET /api/v1/videos/public` — 공개 클립 목록 (2026-09-08 추가)

홈의 영상 모음이 쓴다. **공개된 클립만**, 업로더 구분 없이, 최근 것이 앞에 온다
(최대 100건).

```json
[
  { "id": "7c05...", "sport_code": "football", "duration_ms": 10200,
    "created_at": "2026-09-08T09:00:00Z", "title": "우리 팀 첫 골",
    "description": "왼발 감아차기" }
]
```

🔴 **로그인이 필요하다.** 확인 방법이 "다른 계정으로 로그인해도 보인다"라 인증을
그대로 뒀다 — 익명 피드가 필요하면 연다.

🔴 **저장 키·업로더는 안 실린다.** 저장 키에는 업로더 `user_id` 가 들어 있다
(`videos/<user_id>/…`). 재생은 아래 `GET /videos/{id}/playback-url` 로 따로 받는다.

### `GET /api/v1/videos/{video_id}/playback-url` — 재생용 주소 (2026-09-08 추가)

원본을 재생·다운로드할 **사전 서명 GET URL**. 재생도 앱 서버를 지나지 않는다
(PER-002).

```json
{ "url": "https://<bucket>.s3.<region>.amazonaws.com/videos/…?X-Amz-…", "expires_in": 900 }
```

- **공개 클립이거나 자기 클립일 때만.** 아니면 `404 VIDEO_NOT_FOUND` — 비공개
  남의 클립은 "없음"과 같게 답한다
- URL 은 `expires_in` 초 뒤 만료된다. 매번 새로 받는다(캐시하지 않는다)

| 에러 | code | 언제 |
|---|---|---|
| 404 | `VIDEO_NOT_FOUND` | 없는 클립이거나 비공개 남의 클립이다 |
| 503 | `STORAGE_NOT_CONFIGURED` | 서버에 `S3_BUCKET` 이 없다 |

### `POST /api/v1/videos/{video_id}/keep` — 프로필에 저장 (2026-09-08 추가, 2026-09-11 www 배선)

미결 `jin` 24번 2·5조각. **"내 프로필에 리포트 저장"** — 작업이 생긴 클립의
임시 상태를 영구로 만든다. **자기 클립만.** `200 OK`, 응답은 `GET /videos` 한
줄과 같은 모양.

- `kept` 를 `true` 로 만든다. **이 호출 전에는 `GET /videos`(본인 목록) · 공개
  목록 어디에도 안 뜬다** — 등록 시점부터 `kept: false` 로 시작하기 때문이다
  (위 `POST /videos` 절). `www` 의 분석 화면(`AnalysisStage.tsx`)이 리포트가
  `ready` 일 때만 이 호출을 부른다 — 분석이 실패·반려로 끝났으면 부를 것이
  없다(리포트가 없다).
- **임시 원본(`videos/…`)이면 리포트 자리로 옮긴다** —
  `reports/<user_id>/<video_id>/source.<ext>`. S3 `CopyObject`(서버 쪽) 후 원본
  삭제라 바이트가 앱 서버를 지나지 않는다(PER-002). 옮긴 뒤 `storage_key` 가
  새 값으로 바뀌어 응답에 실린다. 재생(`playback-url`)도 새 키를 쓴다.
- **분석 작업이 없는 클립**(`/me` 업로드, `analyze:false`)은 옮기지 않는다 —
  리포트 폴더가 없다. `kept` 만 켜고 `videos/` 에 그대로 둔다.
- **멱등이다.** 이미 저장된 클립에 다시 불러도 `200` 이고 이동은 건너뛴다.
- 🔴 리포트 JSON 안의 `source_video` 는 아직 옛 `videos/…` 키를 가리킨다 —
  리포트를 DB 로 옮길 때(`paik` 7) 정리한다. 미리보기(`reports/…`)는 영향 없다.

| 에러 | code | 언제 |
|---|---|---|
| 404 | `VIDEO_NOT_FOUND` | 없는 클립이거나 **남의 클립**이다 |
| 503 | `STORAGE_NOT_CONFIGURED` | 서버에 `S3_BUCKET` 이 없다 |

### `DELETE /api/v1/videos/{video_id}` — 클립 삭제 (2026-09-08 추가)

미결 `jin` 24번. **자기 클립만.** `204 No Content`.

- **DB 행**과 그 연쇄(`video_validation`·`analysis_job`·그 하위)를 지운다 —
  외래키 `ON DELETE CASCADE`(SEC-006).
- **S3 객체**도 지운다: `storage_key` + `reports/<user_id>/<video_id>/` 접두사 전부.
  🔴 **best-effort** — 실패해도 `204` 다. DB 에서 사라진 것이 "사용자에게 없어진
  것"이고, 남은 S3 객체는 백스톱 스윕이 잡는다. (지금 EC2 역할에 `s3:DeleteObject`
  가 없어 실서버에서는 객체가 남는다 — 미결 `jin` 24번 IAM 조각)

| 에러 | code | 언제 |
|---|---|---|
| 404 | `VIDEO_NOT_FOUND` | 없는 클립이거나 남의 클립이다 |

### `GET /api/v1/cards/{card_public_slug}/featured-video` — 남의 대표 영상 (2026-09-09 추가, 미결 `paik` 10번)

어떤 사람의 「나를 보여주는 대표 영상」을 **그 사람의 카드 슬러그**로 가져온다.
추천 판에서 후보 옆에 도는 장면이 이것이다. 세우는 것은 위 `PATCH /videos/{id}`
의 `is_featured` 다.

```json
{
  "video_id": "7c05...",
  "url": "https://<bucket>.s3.<region>.amazonaws.com/…?X-Amz-…",
  "expires_in": 900,
  "sport_code": "football",
  "duration_ms": 10200
}
```

- 🔴 **로그인하면 누구나.** 대표는 「보여 주려고」 고른 장면이지만, 사전 서명
  URL 을 내주는 자리라 익명 긁기는 막는다.
- 🔴 **저장 키가 아니라 사전 서명 GET URL** 을 준다 — 버킷은 닫혀 있다
  (`playback-url` 과 같은 원칙). `expires_in` 초 뒤 만료, 매번 새로 받는다.
- `is_public` 여부와 무관하다 — **대표로 세운 것 자체가 「보여 준다」는 뜻**이다.

| 에러 | code | 언제 |
|---|---|---|
| 404 | `NO_FEATURED_VIDEO` | 슬러그가 없든·대표를 안 세웠든·그 대표가 반려됐든 — 밖에서는 다 "없음"이다 |
| 503 | `STORAGE_NOT_CONFIGURED` | 서버에 `S3_BUCKET` 이 없다 |

### 아직 없는 것

- **재분석** — `analysis_job` 은 여러 건을 허용하지만 만드는 경로가 업로드뿐이다
- **분석 결과 적재**(`POST /analyses`) — 3-1 절. `metric_definition` 합의가 선행이다

---

## 3-7. 스쿼드 (2026-09-03 추가)

부록 D 도메인 ③ 의 남은 둘(`squad` · `squad_member`). **팀 단위 카드 묶음**이다 —
`player_card` 가 개인의 얼굴이라면 스쿼드는 팀의 얼굴이고, 그래서 모양이 같다:
주인을 가리키는 외래키 하나와 공유용 슬러그 하나.

> **상태:** 구현됨 · 2026-09-03
> **확인:** `git grep -n "squad_member" -- fastapi/app` → 결과가 있으면 들어왔다

### 팀당 하나로 다룬다 — 스키마는 여러 개를 허용한다

부록 D.7 이 `squad` 에 정한 유일 제약은 `public_slug` 하나뿐이라 `team_id` 에는
제약이 없다. **ERD 에 없는 제약은 늘리지 않았다.** 다만 `squad` 에 이름 컬럼이
없어 한 팀에 여러 개를 만들면 서로 구별할 수가 없다.

그래서 **애플리케이션이 팀당 하나로 다룬다** — 경로가 `/teams/{id}/squad` 단수이고
생성이 멱등이다. 이름 컬럼이 생기면 스키마를 바꾸지 않고 여러 개를 열 수 있다.

### 권한

| 무엇 | 누가 |
|---|---|
| 만들기 · 등재 · 제외 | **주장만** (경기 등록과 같은 기준 — 팀을 대표하는 행위다) |
| 팀 화면에서 보기 | 소속이면 된다 |
| 공유 슬러그로 보기 | **누구나. 인증하지 않는다** |

팀 조회에 소속을 요구하는 것은 비밀을 지키는 검사가 아니다 — 슬러그를 아는 사람은
어차피 볼 수 있다. **팀 id 로 남의 팀 구성을 훑는 것**을 막는 자리다.

### `POST /api/v1/teams/{team_id}/squad`

본문이 없다. `201 Created`, 이미 있으면 `200 OK`.

```json
{
  "id": "7c05...",
  "team_id": "3f1c...",
  "public_slug": "aB3xK9mQ2pL7vN4t",
  "formation": null,
  "members": []
}
```

**멱등이다.** 두 번 불러도 스쿼드는 하나고 슬러그도 그대로다 — 클라이언트가
재시도해도 공유 링크가 바뀌면 안 된다(`POST /me/card` 와 같은 판단이다).

`formation` 은 홈 스쿼드 판의 판 크기다(`"3:3"`·`"5:5"`·`"7:7"`) — 아직 안
정했으면 `null`. `PATCH /teams/{team_id}/squad` 로 저장한다(아래).

| 에러 | code | 언제 |
|---|---|---|
| 403 | `FORBIDDEN` | 주장이 아니다 |
| 404 | `TEAM_NOT_FOUND` | 팀이 없다 |

### `GET /api/v1/teams/{team_id}/squad`

소속이면 본다. 아직 안 만들었으면 `404 SQUAD_NOT_FOUND` 다 — 빈 스쿼드를 돌려주면
"만들지 않은 것"과 "비어 있는 것"이 같아 보인다.

### `POST /api/v1/teams/{team_id}/squad/members`

```json
{ "player_card_id": "9a2e...", "position_code": "GK" }
{ "player_card_id": "9a2e...", "position_code": "GK", "grid_col": 1, "grid_row": 3 }
```

`grid_col`·`grid_row` 는 **선택**이다 — 등재하면서 홈 판 칸에 바로 올릴 때 준다.
🔴 **함께 주거나 함께 비운다**(한쪽만 주면 422). 격자·픽셀 규칙은 아래 「홈 판 격자」.

`201 Created` — **바뀐 스쿼드 전체**를 돌려준다(화면이 목록을 다시 그린다).

```json
{
  "id": "7c05...",
  "team_id": "3f1c...",
  "public_slug": "aB3xK9mQ2pL7vN4t",
  "formation": "5:5",
  "members": [
    {
      "id": "1d4f...",
      "player_card_id": "9a2e...",
      "card_public_slug": "hong-gildong-4f2a",
      "nickname": "홍길동",
      "position_code": "GK",
      "position_label": "골키퍼",
      "grid_col": 1,
      "grid_row": 3
    }
  ]
}
```

판에 안 올린 등재는 `grid_col`·`grid_row` 가 `null` 이다.

`card_public_slug` 로 그 사람의 공개 카드(`/cards/{slug}`)로 갈 수 있다 —
**내부 id 를 밖에 내보내지 않는 것**이 카드와 같은 원칙이다.

🔴 **팀 구성원의 카드만 등재할 수 있다.** 스쿼드는 *팀의* 카드 묶음이라, 아무
카드나 넣을 수 있으면 남의 선수로 팀을 꾸민 것처럼 보이게 만들 수 있다.
⚠️ 이것은 스키마가 아니라 **앱이 정한 규칙**이다 — 용병을 넣어야 할 일이 생기면
외래키를 그대로 둔 채 규칙만 고치면 된다.

`position_code` 는 **팀 종목 안에서** 찾는다. 약칭이 종목을 넘나들기 때문이다 —
야구 `C` 는 포수, 농구 `C` 는 센터다.

| 에러 | code | 언제 |
|---|---|---|
| 403 | `FORBIDDEN` | 주장이 아니다 |
| 404 | `SQUAD_NOT_FOUND` | 스쿼드를 아직 안 만들었다 |
| 404 | `CARD_NOT_FOUND` | 그 카드가 없다 |
| 409 | `ALREADY_ENLISTED` | 이미 등재된 카드다 (부록 D.7 — 스쿼드당 카드 1회) |
| 422 | `NOT_TEAM_MEMBER` | 팀 구성원의 카드가 아니다 |
| 422 | `UNKNOWN_POSITION` | 이 종목에 없는 포지션이다 |

### `DELETE /api/v1/teams/{team_id}/squad/members/{member_id}`

등재를 뺀다. **카드는 지워지지 않는다** — 스쿼드에서 빠질 뿐이다. 바뀐 스쿼드
전체를 돌려준다.

🔴 **그 등재가 이 팀 스쿼드의 것인지 확인한다.** 안 하면 주장이 id 만 알고 남의
스쿼드에서 카드를 뺄 수 있다. 남의 것이면 `404 MEMBER_NOT_FOUND` 다.

### `PATCH /api/v1/teams/{team_id}/squad` (2026-09-09 추가, 미결 `paik` 9번)

홈 스쿼드 판의 **판 크기**를 저장한다. **주장만.** 바뀐 스쿼드 전체를 돌려준다.

```json
{ "formation": "5:5" }
```

값 집합(`"3:3"`·`"5:5"`·`"7:7"`)을 서버가 강제하지 않는다 — `analysis_job.status`
와 같은 판단(값 규칙이 늘 때 마이그레이션 없이). 길이만 본다(1\~8).

| 에러 | code | 언제 |
|---|---|---|
| 403 | `FORBIDDEN` | 주장이 아니다 |
| 404 | `SQUAD_NOT_FOUND` | 스쿼드를 아직 안 만들었다 |

### `PATCH /api/v1/teams/{team_id}/squad/members/{member_id}` (2026-09-09 추가, 미결 `paik` 9번)

등재 하나의 **포지션·판 배치**를 바꾼다. **주장만.** 바뀐 스쿼드 전체를 돌려준다.
계약의 「아직 없는 것 — 포지션 바꾸기」를 이걸로 해소한다.

```json
{ "position_code": "DF", "grid_col": 0, "grid_row": 2 }
{ "position_code": "GK", "grid_col": null, "grid_row": null }
```

- `position_code` 는 **항상 준다** — 등재는 포지션 없이 존재하지 않는다. 포지션은
  그대로 두고 칸만 옮기려면 지금 코드를 그대로 실으면 된다.
- `grid_col`·`grid_row` 는 **함께 주거나 함께 비운다**. 둘 다 `null` 이면 등재는
  남기고 **판에서만 뺀다**.

| 에러 | code | 언제 |
|---|---|---|
| 403 | `FORBIDDEN` | 주장이 아니다 |
| 404 | `MEMBER_NOT_FOUND` | 이 팀 스쿼드의 등재가 아니다 (남의 것도 이 코드다) |
| 422 | `UNKNOWN_POSITION` | 이 종목에 없는 포지션이다 |

### 홈 판 격자 — 지금 3열 × 4행 (2026-09-09 추가)

`grid_col`·`grid_row` 는 **격자 칸 번호**다. 🔴 **화면 픽셀이 아니다** — 카드
크기가 바뀌어도 배치가 안 어긋나게. 서버는 `0 ≤ 값 ≤ 15` 만 본다(픽셀 좌표
방어). 지금 판은 **3열(0\~2) × 4행(0\~3)** 이고 **행이 포지션 라인**이다:
`0` FW · `1` MF · `2` DF · `3` GK. `formation` 이 바뀌어도 격자는 이대로다.

🔴 **격자 크기·행 의미가 바뀌면 저장된 값의 뜻도 바뀐다** — 그때는 리매핑
마이그레이션이 필요하다. 이 절이 그 값의 정본이다.

### `GET /api/v1/squads/{public_slug}`

**인증하지 않는다.** 공개 카드(`/cards/{slug}`)와 같은 결이다 — 슬러그가 96비트
난수라 그 자체가 유일한 접근 통제다(SEC-005).

### 아직 없는 것

- **스쿼드 삭제** — 팀 해체 시의 처리가 안 정해졌다(부록 D.6). `squad.team_id` 의
  삭제 규칙을 기본(RESTRICT)으로 둔 것도 같은 이유다
- ~~**포지션 바꾸기**~~ ✅ 2026-09-09 — `PATCH .../squad/members/{member_id}` (미결 `paik` 9번)
- **여러 스쿼드** — 이름 컬럼이 필요하다(위 「팀당 하나로 다룬다」)

---

## 3-8. 분석 작업 큐 — **워커 전용** (2026-09-04 추가)

미결 `ho` 17번(S3 에 영상이 올라와도 분석이 돌지 않는다)의 백엔드 쪽이다.
`POST /videos` 가 `analysis_job` 을 `queued` 로 만들어 두는데 **꺼내 가는 것이
없었다.** 여기가 그 자리다.

```
POST /videos ──> analysis_job(queued)
                      │
   워커가 주기적으로 ─┴─> POST /internal/analysis-jobs/claim   (running 으로)
                            │ 분석 실행 (agent/scripts/analyze_s3.py)
                            └─> PATCH /internal/analysis-jobs/{id}  (succeeded|failed)
```

### 🔴 워커가 **가져간다**(pull). 서버가 밀지 않는다

| 왜 | |
|---|---|
| GPU 인스턴스가 **자동 종료**된다 | 밀어 주는 방식은 대상이 꺼져 있으면 실패한다. 가져가는 방식이면 켜질 때 밀린 것을 처리한다 |
| 루브릭을 고르려면 **종목이 필요**하다 | S3 의 `videos/` 와 `reports/` 를 비교하는 방식으로는 알 수 없다 — 그 값은 DB 에 있다 |
| `analysis_job` 이 **이미 상태의 정본**이다 | S3 비교는 이것을 우회해 진실을 둘로 만든다 |
| nginx `proxy_read_timeout` 기본 **60초** | 오래 도는 쪽이 워커고 서버는 짧게 답한다. 동기 호출로 만들면 여기서 끊긴다 |
| EC2 에 `videos/` **쓰기 권한이 필요 없다** | 미결 `ho` 17번의 「하지 말 것」을 그대로 지킨다 |

### 인증 — 사람 토큰이 아니다

`X-Worker-Token` 헤더에 공유 시크릿을 넣는다(`WORKER_TOKEN`). 워커는 기계라
사용자 계정에 묶지 않는다 — 묶으면 그 계정이 탈퇴하거나 토큰이 폐기될 때
파이프라인이 조용히 멈춘다.

🔴 **`WORKER_TOKEN` 이 비어 있으면 이 경로는 전부 401 이다**(fail-closed).
`ADMIN_EMAILS` 와 같은 이유다.

### `POST /api/v1/internal/analysis-jobs/claim`

가장 오래된 `queued` 하나를 `running` 으로 바꾸고 돌려준다.

`200 OK`
```json
{
  "job_id": "…", "video_id": "…",
  "storage_key": "videos/<user_id>/<uuid>.mp4",
  "sport_code": "baseball", "side": "right", "duration_ms": 4200,
  "subject_box": [0.39, 0.35, 0.12, 0.4], "subject_at_ms": 4200,
  "focus": ["follow_through", "guide_hand"]
}
```

`subject_box`·`subject_at_ms` 는 「이 사람으로 분석」 대상이다(미결 `paik` 6번,
등록 시 검증됨). 🔴 **없으면 둘 다 `null` 이고 그게 정상**이다 — 워커는
「자동으로 고르기」로 돈다. 있으면 `analyze_s3.py --subject-box x,y,w,h
--subject-at-ms` 로 넘긴다. `side`·`focus` 와 같은 축이다.

`focus` 는 「집중해서 볼 항목」이다(미결 `paik` 8번) — 루브릭 `criteria[].id` 목록.
🔴 **`null` 이나 빈 리스트면 「전체적으로」**다 — 워커는 `--focus` 를 안 붙인다.
있으면 `--focus a,b,c` 로 넘긴다.

**`204 No Content` — 큐가 비었다. 오류가 아니다.** 오류로 다루면 워커 로그가 빈
폴링으로 가득 찬다.

`POST` 인 이유는 **상태를 바꾸기 때문**이다. 이름이 조회처럼 보여도 이 호출은 작업을
하나 소비한다 — `GET` 으로 두면 프록시·클라이언트가 마음대로 재시도해서 작업이
조용히 사라진다.

🔴 **동작(루브릭)이 응답에 없다.** 담을 자리가 아직 없어서다(미결 `jin` 17번).
`sport_code` 만으로는 축구·농구에서 루브릭이 **둘로 갈린다.**

| 종목 | 루브릭 | 정해지나 |
|---|---|---|
| baseball | `baseball_pitching` | ✅ |
| basketball | `basketball_jump_shot` · `basketball_layup` | ❌ |
| football | `football_instep_shot` · `football_inside_pass` | ❌ |

**갈리는 종목은 실행하지 말고 `failed` 로 보고한다.** `analyze_s3.py --rubric` 의
기본값은 `football_instep_shot` 이라, 안 주면 농구를 축구 루브릭으로 채점하고
**그 결과가 틀렸다는 것이 값에 나타나지 않는다.**

### `PATCH /api/v1/internal/analysis-jobs/{job_id}`

```json
{ "status": "succeeded" }
{ "status": "succeeded", "report_key": "reports/<user_id>/<video_id>/report.json" }
{ "status": "failed", "failure_reason": "품질 게이트 미달" }
```

`204 No Content`.

| 에러 | code | 뜻 |
|---|---|---|
| 404 | `JOB_NOT_FOUND` | 없는 작업이다 |
| 409 | `JOB_NOT_RUNNING` | 집지 않았거나 이미 끝났다. **재시도해도 소용없다** |
| 422 | `INVALID_JOB_STATUS` | `queued`·`running` 으로는 보고할 수 없다 |

#### `report_key` — 워커가 만든 리포트의 자리 (2026-09-09 추가, 미결 `paik` 11번)

**선택 필드.** 워커가 분석 결과를 S3 에 쓴 뒤 그 **버킷 상대 키**를 함께 싣는다.
백엔드는 이 값을 `analysis_job.report_key` 에 그대로 남긴다 — 자리 규칙
(`analyze_s3` 의 `report_targets`)이 워커 안에만 있고, 파일 이름에 분석 시각이
붙어 같은 영상을 두 번 돌리면 파일이 둘이 되므로 **백엔드가 계산으로 찾을 수 없다.**

| | |
|---|---|
| 형태 | 버킷 상대 키. 예: `reports/<user_id>/<video_id>/report.json`. 상한 1024자(S3 객체 키 한계) — 넘으면 422 |
| 🔴 `succeeded` 일 때만 | `failed` 와 함께 와도 **버린다**(실패한 작업이 가리킬 리포트는 없다). 계약이 아니라 데이터 무결성이라 받는 쪽에서 막는다 |
| 없어도 된다 | 워커가 자리를 못 실어도(리포트가 다른 버킷 등) 분석은 성공한 것이다. 화면이 리포트를 못 찾을 뿐이다 |
| 읽는 쪽 | 이 값으로 무엇을 읽을지는 미결 `paik` 7번(리포트 읽는 경로)에서 정한다 |

**`finished_at` 을 받지 않는다.** 워커의 시계가 어긋나면 소요 시간이 음수가 된다 —
서버가 찍는다. 같은 이유로 `started_at` 은 `claim` 이 찍는다. 🔴 이 두 시각의 차이가
**PER-001 이 보려는 값**이라, `queued` 를 바로 끝낼 수 있게 두면 `started_at` 이 빈
채 `finished_at` 만 차서 그 값이 망가진다.

### 아직 없는 것

- 🔴 **적재(`POST /analyses`)** — 규격은 3-1 절에서 정해졌고(적재 규격 = 미결
  `jin` 1번 A안, 2026-09-08), `metric_definition` 도 45행 시드됐다(마이그레이션
  `ca31a2180b54`). 남은 것은 적재 경로(흐름 B) 구현이다. 그때까지 워커의 산출물은
  `reports/` 의 JSON 이다
- **재시도** — `failed` 를 사람이 다시 `queued` 로 되돌리는 경로. (워커가 죽어서
  생긴 실패는 아래 회수가 **한 번은 자동으로** 되살린다. 여기서 말하는 것은
  분석이 실제로 실패한 건이다)
- **작업 취소** — 진행 중인 작업을 사람이 멈추는 경로

### 멈춘 작업은 자동으로 회수된다 (2026-09-04 추가)

워커가 **보고 없이 죽으면**(크래시·강제 종료·**인스턴스 자동 종료**) 작업이
`running` 인 채 남는다. `claim` 이 불릴 때마다 그런 것을 먼저 정리한다.

| 몇 번째인가 | 어디로 | `failure_reason` |
|---|---|---|
| 처음 멈춤 | **`queued`** — 다시 처리된다 | `회수됨: 워커가 보고 없이 멈췄습니다…` |
| 또 멈춤 | **`failed`** — 중단한다 | `회수됨 뒤 또 멈췄습니다…` |

🔴 **한 번만 되살리는 이유**: 되돌리기만 하면 **워커를 죽이는 클립**(4K 에서 host
RAM 이 터지는 것 — 미결 `ho` 9번)이 큐를 영원히 돌게 된다. 반대로 한 번도 안
되살리면 인스턴스가 정지하며 멈춘 작업이 전부 버려진다.

⚠️ **스스로 `failed` 를 보고하고 끝나는 경우는 회수 대상이 아니다.** 회수가 잡는
것은 보고 없이 사라진 작업뿐이다.

**기다리는 시간은 `ANALYSIS_JOB_TIMEOUT_MINUTES`(기본 30분)** 다. 🔴 **가장 긴
분석보다 넉넉히 길어야 한다** — 짧으면 아직 돌고 있는 작업을 빼앗아 같은 클립을
두 번 분석한다. PER-001 의 실측이 나오면 줄인다.

⚠️ 별도 스케줄러를 두지 않았다. 회수가 필요한 시점은 정확히 "누군가 일을 달라고
할 때"이고, 타이머를 새로 만들면 **그 타이머가 살아 있는지를 또 확인해야 한다.**

### 저장 안 한 임시 영상도 여기서 정리된다 (2026-09-08 추가, 2026-09-11 실배선)

미결 `jin` 24번(5조각까지 해소). 작업이 생긴 클립은 임시로 올라간다
(`video.kept=false`) — 2026-09-11 전에는 이 문서만 그렇게 적혀 있었고 실제
등록 코드는 늘 `kept=true` 였다(사용자가 "분석 실패한 영상이 안 지워진다"고
지적해서 발견·수정했다).
"내 프로필에 리포트 저장"을 안 누르고 떠나면 프론트가 `DELETE /videos/{id}` 를
부르지만(빠른 길), 브라우저가 죽으면 놓친다. 그래서 **`claim` 이 멈춘 작업 회수와
같은 자리에서** 백스톱을 돈다: `kept=false` 이고 `PROVISIONAL_VIDEO_TTL_HOURS`
(기본 24)보다 오래됐고 **진행 중인 작업(`queued`/`running`)이 없는** `video` 를
DB(연쇄)와 S3(`storage_key` + `reports/<user_id>/<video_id>/`, best-effort)에서
지운다. `queued` 를 제외하는 이유는 GPU 인스턴스가 꺼져 있으면 몇 시간 대기가
정상이기 때문이다.

---

## 3-9. 평가·신뢰 (2026-09-04 추가)

부록 D 도메인 ⑤. SFR-008. 스키마는 박민호가 09-03 에 냈고(`2649dd9`) 응용 계층은
정어진이 09-04 에 썼다.

### 🔴 설계가 강제하는 것 셋

| | |
|---|---|
| **평가는 선택형이다**(3.4) | `review` 에 총점·별점이 없다. 고른 것이 `review_selection` 에 **행으로** 남는다. 나쁜 평가 하나가 줄 수 있는 피해에 상한을 두기 위해서다 |
| **신뢰도는 저장하지 않는다**(D.4) | 집계로 나오는 파생값이다. **소급 생성이 불가능한 것은 원자료뿐**이라 평가자·시점·선택 결과만 남긴다 |
| **제재는 평가와 분리한다**(3.5) | `report`·`no_show` 는 `review` 와 이어지지 않는다. **평가를 안 해도 신고할 수 있다** |

### 정한 것 (2026-09-04, 정어진)

패킷 B 문서가 「정해야 할 것」으로 남겨 둔 셋이다. 🔴 **PM 판단이 다르면
`app/review/domain/rules/review_rules.py` 만 고치면 된다** — 숫자와 권한이 전부
거기 모여 있다.

| 무엇 | 정한 값 | 왜 |
|---|---|---|
| **평가 가능 기간** | 경기 후 **14일** | 용병 경기는 주말에 몰린다. 7일이면 토요일 경기를 다음 주말에 여는 사람이 놓친다. 무기한은 **기억이 흐려진 평가**를 받는데 그건 신뢰도 원자료의 질을 떨어뜨린다 |
| **불참 기록 권한** | **주최 팀 주장만** | 제재 기록이라 만들 수 있는 사람을 좁힌다. 누구나 붙이면 사이가 틀어진 상대에게 서로 붙일 수 있고, **스키마에 기록자 컬럼이 없어** 누가 붙였는지도 못 따진다 |
| **선택지 노출 순서** | `sort_order` 컬럼 | `ORDER BY category` 는 「주의」가 맨 앞에 온다. 코드에 순서를 박으면 마이그레이션과 두 곳이 된다. 🔴 **부록 D 에 없는 컬럼이라 ERD 갱신이 필요하다** |

### `GET /api/v1/review-options`

인증 필요. 선택지 전부.

```json
[{"code": "manner_time", "category": "manner", "label": "시간을 잘 지켰다"}, …]
```

🔴 **배열의 순서가 화면 노출 순서다**(매너 · 실력 · 재매칭 · 주의).
`category` 로 묶어 그리되 **순서는 서버가 준 것을 그대로** 쓸 것 — 알파벳순으로
정렬하면 `caution` 이 맨 앞에 온다.

### `POST /api/v1/matches/{match_id}/reviews`

```json
{"reviewee_id": "…", "option_codes": ["manner_time", "skill_teamplay"]}
```

`201` — `{id, match_id, reviewer_id, reviewee_id, submitted_at, selected_codes}`.
**점수 필드가 없다.**

| 에러 | code |
|---|---|
| 403 | `FORBIDDEN` — 내가 이 경기의 **확정** 참가자가 아니다 |
| 404 | `MATCH_NOT_FOUND` |
| 409 | `ALREADY_REVIEWED` — 경기당 1회 (**DB 유일 제약**, 부록 D.7) |
| 422 | `MATCH_NOT_PLAYED` · `REVIEW_WINDOW_CLOSED` · `SELF_REVIEW` · `NOT_A_PARTICIPANT` · `UNKNOWN_OPTION` · `NO_OPTION_SELECTED` |

⚠️ **「아직 안 끝났다」와 「기간이 지났다」를 가른다.** 화면이 다르게 안내해야 한다.

**확정된 참가자끼리만** 평가한다 — `match_application` 의 두 수락 시각이 다 찬
행이다(부록 D.5). 서로 평가하는 것은 둘 다 된다(유일 제약이 방향까지 본다).

### `POST /api/v1/matches/{match_id}/no-shows`

```json
{"user_id": "…"}
```

`201`. 🔴 **주최 팀 주장만.**

| 에러 | code |
|---|---|
| 403 | `FORBIDDEN` — 주장이 아니다 |
| 409 | `ALREADY_RECORDED` — 경기당 1인 1건 (DB 제약) |
| 422 | `MATCH_NOT_PLAYED` · `NOT_A_PARTICIPANT` |

### `POST /api/v1/reports`

```json
{"target_user_id": "…", "reason": "자유 텍스트"}
```

`201` — `{id, target_user_id, created_at}`.

⚠️ **신고 내용을 되돌려주지 않는다.** 신고자에게도 사본을 주면 그 응답이 떠돌고,
대상에게는 더더욱 보이면 안 된다.

**중복을 막지 않는다** — 같은 사람을 여러 번 신고할 수 있다. 그리고 **평가와
무관하다**: 참가자가 아니어도 신고할 수 있다.

### 아직 없는 것

- **신고 처리** — 접수만 한다. 관리자 화면이 생기면 붙인다
- **평가 조회** — 내가 받은 평가를 보는 경로. 신뢰도 표시 화면이 정해지면 낸다
- **불참 취소** — 잘못 기록한 것을 무르는 경로

---

## 3-10. 과금 (2026-09-08 추가)

부록 D 도메인 ⑥. 패킷 A(`docs/backend-work-split.md`). `paik` 브랜치에 있고,
공유 파일 배선(`app/main.py` 등)은 아직입니다 — 정어진이 병합하며 잇습니다.

### 🔴 잔량은 컬럼이 아니라 `SUM(delta)` 다

부록 D.4 가 `analysis_credit.balance`를 파생값이라 제거한 자리다. 지급은 양수,
차감은 음수 한 행이고, **크레딧 차감은 분석 경로(`POST /videos`)와 이어지지
않는다** — 컨텍스트 경계를 넘는 연결이라 그쪽은 정어진이 붙인다.

### 정하지 않은 것 (패킷 A 문서 「정해야 할 것」)

무료 크레딧 지급 시점·액수, 분석 1건당 차감액, `reason` 값 목록은 아직 미정이다.
그 전에도 조회·수동 지급은 가능하다 — 정책은 값이지 구조가 아니다.

### `GET /api/v1/credits`

인증 필요. 내 크레딧 잔량과 이력.

```json
{"balance": 70, "history": [
  {"id": "…", "delta": 100, "reason": "signup_bonus", "created_at": "…"},
  {"id": "…", "delta": -30, "reason": "analysis", "created_at": "…"}
]}
```

### `POST /api/v1/admin/credits/adjustments` — 관리자 전용

```json
{"user_id": "…", "delta": 100, "reason": "signup_bonus"}
```

`201` — 조정 뒤 대상 사용자의 `GET /credits`와 같은 형태.

| 에러 | code |
|---|---|
| 403 | 관리자가 아니다(`require_admin`, 계약 3-2절과 같은 게이트) |
| 404 | `USER_NOT_FOUND` |
| 422 | `INVALID_DELTA` — 증감액이 0이다 |

### `GET /api/v1/coaches` · `GET /api/v1/coaches/{coach_id}`

인증 필요. 페이지 형식은 `GET /admin/users`와 같다(`items`·`total`·`page`·`size`).

```json
{"id": "…", "name": "김도현", "contact": "…"}
```

⚠️ **종목·가격·소개 문장·대표 영상이 없다.** `www/src/lib/market.ts`의 `Coach`
타입(mock)은 이보다 훨씬 풍부하지만, 부록 D의 `coach`는 `id`·`name`·`contact`
셋뿐이다 — 화면과 스키마를 맞추는 것은 별도 결정이 필요해 미결 항목에 올렸다.
상세 없는 코치는 404 `COACH_NOT_FOUND`.

### `POST /api/v1/coaches/{coach_id}/referrals`

```json
{"fee": "50000.00"}
```

`201` — `{id, coach_id, fee, created_at}`. **중복을 막지 않는다** — 같은 코치에
여러 번 연결을 요청할 수 있다(상담을 여러 번 받는 흐름이 자연스럽다).

| 에러 | code |
|---|---|
| 404 | `COACH_NOT_FOUND` |
| 422 | `INVALID_FEE` — 수수료가 음수다 |

### 아직 없는 것

- **`market.ts`의 나머지 필드** — 가격·후기·레슨 장소 등은 부록 D에 대응
  컬럼이 없다. 필요해지면 부록 D 변경으로 이어진다
- **크레딧 자동 지급·차감** — 가입 보너스나 분석당 차감을 트리거하는 경로.
  지금은 관리자의 수동 조정뿐이다

---

## 3-11. 용병 후보 검색 (2026-09-10 추가 — 박민호, 아직 미배선)

🔴 **SFR-006(적합도)·SFR-007(추천)과는 별개 기능이다 — 그걸 대신하지 않는다.**
도메인 ④(매칭) ERD에 예약된 `fitness_score`·`recommendation` 테이블은 아직
안 만들었고, 이 기능은 그 테이블을 쓰지 않는다. 이름이 겹쳐 보여서 명시적으로
가른다:

| | 이 기능 (3-11절) | SFR-006 | SFR-007 |
|---|---|---|---|
| 언제 계산하나 | **지원 전** — 팀이 능동적으로 검색 | **지원(`match_application`) 후** | 팀에 후보 제시 시점 |
| 무엇을 내나 | 코사인 유사도 스칼라 1개 | **수준·역할·성향 3축** `fitness_score` | 후보 + **추천 사유** |
| 저장하나 | 안 함 — 매 요청 즉석 검색 | `fitness_score` 행 | `recommendation` 행 |
| 특정 경기(`match_id`)에 묶이나 | 아니다 — 포지션·종목 조건뿐 | 그렇다(지원 건 단위) | 그렇다 |

정어진이 나중에 SFR-006·007을 구현할 때, 여기 검색(`skill_embedding` 코사인
유사도)을 **`recommendation`의 검색(retrieval) 단계**로 재사용할지는 그쪽
판단이다 — 이 절은 그 결정을 선점하지 않는다. 관련: pending `min` 16번.

### 스키마 — `user` 테이블에 얹었다 (새 테이블 아님)

`fastapi/alembic/versions/28148877afc0_add_mercenary_matching_fields.py`
(pending `min` 16번)가 만든 6개 컬럼을 그대로 쓴다. `preferred_positions`는
`"<sport_code>:<code>"` 문자열로 인코딩한다 — 포지션 약칭이 종목 간 겹치기
때문이다(`position` 테이블과 같은 이유, 3장 「포지션 목록은 마이그레이션이
넣는다」 참고).

### `GET /api/v1/me/mercenary-profile`

인증 필요. 아직 한 번도 안 채웠으면 전부 기본값(빈 리스트·`is_searchable:
false`)인 프로필을 돌려준다 — 404가 아니다.

```json
{
  "user_id": "…",
  "preferred_positions": [{"sport_code": "football", "code": "GK"}],
  "available_slots": [{"day": "SAT", "start": "18:00", "end": "21:00"}],
  "location": "서울 강남",
  "skill_summary": "공중볼 처리에 강함",
  "is_searchable": true
}
```

### `PATCH /api/v1/me/mercenary-profile`

인증 필요. **보낸 필드만 바뀐다.** `null`은 "안 건드림", `location`·
`skill_summary`는 빈 문자열 `""`로 지운다. `preferred_positions`·
`available_slots`는 빈 배열이면 그대로 빈 배열로 저장된다(이 둘은 `null`과
`[]`을 코드가 구분할 수 있어 문자열과 같은 우회가 필요 없다).

```json
{
  "preferred_positions": [{"sport_code": "football", "code": "GK"}],
  "available_slots": [{"day": "SAT", "start": "18:00", "end": "21:00"}],
  "skill_summary": "공중볼 처리에 강함",
  "is_searchable": true
}
```

`200 OK` — 응답은 `GET`과 같다.

| 에러 | code | 언제 |
|---|---|---|
| 422 | `MERCENARY_PROFILE_INCOMPLETE` | `is_searchable`이 참이 되는데(요청에서 켜거나 이미 켜져 있는데) `preferred_positions`·`available_slots`·`skill_summary` 중 하나라도 비어 있다 |
| 503 | `EMBEDDING_NOT_CONFIGURED` | `GEMINI_API_KEY`가 없다. **`skill_summary`가 실제로 바뀌는 요청에서만** 뜬다 — 포지션·가능 시간만 바꾸는 요청은 임베딩이 필요 없어 이 에러가 나지 않는다 |
| 502 | `EMBEDDING_UPSTREAM_ERROR` | Gemini 임베딩 API 호출 실패 |

🔴 **`skill_embedding`은 응답에 안 실린다.** 768개 float을 클라이언트가 받을
이유가 없고, 저장·재계산에만 쓴다.

### `POST /api/v1/matching/search-candidates`

인증 필요(로그인만 하면 누구나 — 팀 주장 한정 여부는 박민호가 2026-09-10에
현행 유지로 결정했다, pending `min` 17번). `query_text`(자연어)를 서버가
Gemini 임베딩으로 바꿔 코사인 유사도로 검색한다.

```json
{
  "sport_code": "football",
  "position_code": "GK",
  "query_text": "주말 저녁 가능한 골키퍼, 공중볼 강한 사람",
  "limit": 10
}
```

`200 OK`:

```json
[
  {
    "user_id": "…",
    "nickname": "…",
    "location": "서울 강남",
    "skill_summary": "공중볼 처리에 강함",
    "similarity": 0.83
  }
]
```

`is_searchable = true`이고 `preferred_positions`에 `{sport_code, position_code}`가
있는 사람만, 유사도 내림차순으로 최대 `limit`명(1~50, 기본 10). 결과가
없으면 빈 배열(에러 아님).

🔴 **클라이언트가 벡터를 직접 만들어 보내지 않는다.** `query_text`만 받고
서버가 임베딩을 계산한다 — 임의 벡터를 받으면 검색 랭킹을 조작할 수 있어서다.

| 에러 | code | 언제 |
|---|---|---|
| 422 | `VALIDATION_ERROR` | `query_text`가 빈 문자열이다 |
| 503 | `EMBEDDING_NOT_CONFIGURED` | `GEMINI_API_KEY`가 없다 — 검색은 매번 임베딩이 필요해 이 경로엔 예외가 없다 |
| 502 | `EMBEDDING_UPSTREAM_ERROR` | Gemini 임베딩 API 호출 실패 |

### ✅ 배선·배포 끝났다 (2026-09-10, 박민호 — 정어진 몫을 대신 처리)

- `app/main.py`에 `mercenary_router`가 등록됐다. `openapi.json` 경로 목록을
  검사하는 `tests/user/adapter/test_auth_router.py`도 함께 맞췄다
- 배포 서버(`~/supersub/app/fastapi/.env`)에 fastapi 전용 `GEMINI_API_KEY`를
  넣고 `supersub-api`를 재시작해 `/health` 200을 확인했다. `www/`가 쓰는
  같은 이름의 키와는 여전히 별도 시크릿이다
- **실제 키로 호출해 보니 임베딩 모델 id가 틀려 있었다** —
  `text-embedding-004`는 이미 은퇴돼 `embedContent`에서 404(NOT_FOUND)가
  났다. `client.models.list()`로 `embedContent`를 지원하는 모델을 뽑아
  `gemini-embedding-001`로 정정하고 768차원 벡터 반환까지 확인했다
  (`gemini_embedding_adapter.py`). 가짜 키로는 이 오류가 잡히지 않았을
  것이다
- 팀 주장 한정 여부는 위 절 첫 문단대로 **현행 유지(로그인만 하면 누구나)**
  로 결정했다 — 코드 변경 없음

이 브랜치가 `main`에 병합·배포되기 전까지는 배포 서버가 아직 이 라우터를
서빙하지 않는다 — 위 배선은 로컬 코드 기준이고, 서버 쪽은 환경변수(2번째
항목)만 미리 준비해 둔 상태다.

### 아직 없는 것

- **SFR-006·007 자체(위 표 참고)** — 이 절이 대신하지 않는다
- **팀 관점 필터(가능 시간 겹침 등)** — 지금은 포지션·종목만 거른다

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
백성검 쪽 화면에서도 확인이 필요하다.

---

## 5. 이 범위에 넣지 않은 것

스프린트 2 화면 두 개에 필요 없어서 뺐다. 필요해지면 그때 추가한다.

- 카드 **수정** (`PATCH /me/card`) — 지금 카드에 사람이 고칠 값이 없다(닉네임은 `PATCH /me`). **생성(`POST /me/card`)은 2026-09-02에 3장으로 들어왔다**
- ~~**분석 리포트 조회**~~ — ✅ 2026-09-10 에 `GET /videos/{video_id}/report` 로
  들어왔다(3-1 「✅ 적재 경로(흐름 B)·읽기 엔드포인트」). 미결 `jin` 27번
- 매칭·평가·과금 — 스프린트 3 이후
- 비밀번호 **재설정**, 이메일 인증 — 메일 발송 인프라(SES 등)가 필요하다. 별건이다.
  로그인한 상태에서 바꾸는 **변경**(`PATCH /me/password`)은 2장에 있다
- 토큰 갱신 (`POST /auth/refresh`) — 액세스 토큰 하나로 시작하기로 했다
- 카카오·애플 로그인 — `user_identity.provider` 에 값을 하나 더 쓰면 붙는다 (구글은 08-26에 들어왔다)

---

## 6. 다음 단계

> **2026-09-01 갱신.** 이 절의 1~4번이 전부 끝나서 다시 썼다. 옛 내용은 스텁 시절
> (08-25)의 계획이라 **"지금은 스텁 토큰을 발급한다"처럼 사실과 반대인 서술**이
> 남아 있었다 — 문서 앞머리의 "전부 PostgreSQL에 붙었다"와 모순이었다.

끝난 것 — ✅ Pydantic 모델·라우트 · ✅ DDL과 실제 PostgreSQL(부록 D.6 삭제 연쇄는
외래키로, D.7 유일제약은 스키마로) · ✅ 스텁 → 실제 조회 교체 · ✅ bcrypt 해싱과
서명된 JWT(`app/core/security.py`) · ✅ 백성검에게 계약 공유.

남은 것은 셋이고 **둘은 사람 쪽 답을 기다린다.**

1. **분석 결과 적재** — 3-1절의 미결 넷, 그중 **지표 코드의 종목 처리가 먼저**다.
   합의 전에는 엔드포인트를 만들지 않는다. (미결 항목 「분석 결과 적재 규격」 · 담당 정상호)
2. **클라이언트 계약 반영** — `docs/client-contract-changes.md`.
   (미결 항목 「클라이언트의 백엔드 계약 반영」 · 담당 백성검)
3. **`player_vector`**(SFR-005) — `pgvector` 는 깔렸고 차원 수가 1번에 걸려 있다.

배포 준비는 `docs/deployment.md` 가 따로 다룬다.

> **토큰 값은 계약이 아니다.** 지금은 서명된 JWT 이고 형식은 언제든 바뀔 수 있다.
> 클라이언트는 로그인 응답의 `access_token` 을 **그대로 담아 보내기만** 하면 된다 —
> 값을 파싱하거나 하드코딩하지 말 것.
