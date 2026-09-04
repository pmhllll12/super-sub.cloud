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
| `POST /internal/analysis-jobs/claim` · `PATCH /internal/analysis-jobs/{id}` | **실제 DB** (2026-09-04 추가 — **워커 전용**, 3-8절) |

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
  ]
}
```

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

### `GET /api/v1/cards/{public_slug}`

**인증 불필요** — 공유용이다(SFR-009). 응답 형태는 위와 같되 `id`를 빼고
공개해도 되는 것만 담는다.

| 에러 | code |
|---|---|
| 404 | `CARD_NOT_FOUND` |

---

## 3-1. 분석 결과 적재 (규격 초안 — 정상호 회람용)

> **상태:** 진행 전 · 2026-08-28 작성
> **확인:** `grep -rn analyses fastapi/app/` → 결과가 없으면 미착수
> **메모:** 스키마(`40a4991`)는 들어갔고 **엔드포인트가 없다.** 아래는 합의용 초안이며,
> 3절까지와 달리 **아직 구현되지 않았다.**

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
상태 갱신 엔드포인트는 **아직 정하지 않았다** — 결과 제출과 같은 자리에서 받을지
따로 둘지가 미정이다(아래).

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

### 🔴 정해야 하는 것 — 합의 전에는 구현하지 않는다

| 무엇 | 왜 지금 못 정하나 |
|---|---|
| **지표 코드의 종목 처리 (A·B·C)** | 위 절. **이것이 정해지기 전에는 `metric_definition`을 채울 수 없고, 채우기 전에는 적재가 외래키에 전부 막힌다.** 나머지 셋보다 먼저다 |
| **서비스 인증 방식** | 에이전트는 사용자가 아니다. 사용자 토큰을 쥐게 할 수 없으므로 별도 자격증명이 필요하다. 값은 배포 환경에서 주입한다(5장 SEC-011). 형태 미정 |
| **지표 코드 목록의 주인** | 루브릭이 이미 이름을 갖고 있으므로 **에이전트가 정의하고 백엔드가 따라가는** 형태가 자연스럽다. 다만 새 종목을 열 때 누가 먼저 넣느냐(시드 스크립트 · 마이그레이션 · API)는 미정 |
| **실패 보고 경로** | 상태 갱신을 별도 엔드포인트로 둘지, 결과 제출에 합칠지 |
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
      "joined_at": "2026-09-02T01:00:00Z" }
  ]
}
```

소속이 아니어도 볼 수 있다 — 가입하려면 먼저 봐야 하고, 담기는 것은 팀 정보와
구성원 닉네임뿐이다.

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
| 해상도 | 1920x1080 |
| 형식 | `video/mp4` · `video/quicktime` |

🔴 **길이 상한이 에이전트의 프레임 상한과 아직 안 맞는다.**
`agent/src/supersub_agent/pose.py` 의
`max_frames=300` 은 `target_fps=15` 기준 **20초분**이라 60초 클립은 앞 20초만
분석된다. 미결 항목으로 올렸다 — 정해지면 여기 값이 바뀐다.

### `POST /api/v1/videos/upload-url`

```json
{ "content_type": "video/mp4", "size_bytes": 52428800 }
```

`200 OK`

```json
{
  "storage_key": "videos/3f1c.../9a2e....mp4",
  "upload_url": "https://<bucket>.s3.<region>.amazonaws.com/...",
  "expires_in": 900
}
```

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
  "side": "right"
}
```

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
  "analysis_status": "queued"
}
```

반려면 `passed: false` · `reject_reason: "해상도가 상한을 넘습니다: 3840x2160
(상한 1920x1080)"` · `analysis_job_id: null` 이다. **반려된 클립은 분석하지 않는다** —
규격 검사를 두는 이유가 그것이다.

`duration_ms`·`width`·`height` 는 **클라이언트가 잰 값**이다. 서버가 다시 재려면
원본을 내려받아야 하고 그러면 PER-002 가 무너진다. 용량만은 저장소에 물어 실측한다.

`side` 는 던지는 팔·차는 발이다. 자동 판별이 팔 종목에서 신뢰할 수 없어(5장
CON-007) 사람이 지정할 수 있게 열어 둔다. 생략하면 에이전트의 자동 판별을 쓴다.

| 에러 | code | 언제 |
|---|---|---|
| 403 | `FORBIDDEN` | 남에게 발급된 저장 키다 |
| 422 | `UNKNOWN_SPORT` | 지원하지 않는 종목 코드 |
| 422 | `FILE_NOT_UPLOADED` | 그 키에 올라온 파일이 없다 |
| 503 | `STORAGE_NOT_CONFIGURED` | 서버에 `S3_BUCKET` 이 없다 |

**저장 키에 업로더가 들어 있다**(`videos/<user_id>/<uuid>.<확장자>`). 등록할 때 그
접두사를 대조하므로 남이 올린 객체를 자기 영상으로 등록할 수 없다.

### `GET /api/v1/videos`

내 영상 목록. **최근 것이 앞에 온다.** 한 줄의 모양은 `POST /videos` 응답과 같다.

`analysis_status` 는 그 영상의 **가장 최근** 분석 작업 상태다(`queued` · `running` ·
`succeeded` · `failed`). 같은 영상을 다시 분석하면 작업이 여러 건이 되는데 목록은
최근 것만 보여준다. 반려된 클립은 작업이 없어 `null` 이다.

플러터 `/videos` 화면(영상 상세 펼침 + 규격 반려 사유 바텀시트)이 이 응답 하나로
그려진다.

### 아직 없는 것

- **삭제** — 올린 클립을 지우는 경로. S3 객체까지 함께 지워야 해서 순서를 정해야 한다
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
  "members": []
}
```

**멱등이다.** 두 번 불러도 스쿼드는 하나고 슬러그도 그대로다 — 클라이언트가
재시도해도 공유 링크가 바뀌면 안 된다(`POST /me/card` 와 같은 판단이다).

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
```

`201 Created` — **바뀐 스쿼드 전체**를 돌려준다(화면이 목록을 다시 그린다).

```json
{
  "id": "7c05...",
  "team_id": "3f1c...",
  "public_slug": "aB3xK9mQ2pL7vN4t",
  "members": [
    {
      "id": "1d4f...",
      "player_card_id": "9a2e...",
      "card_public_slug": "hong-gildong-4f2a",
      "nickname": "홍길동",
      "position_code": "GK",
      "position_label": "골키퍼"
    }
  ]
}
```

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

### `GET /api/v1/squads/{public_slug}`

**인증하지 않는다.** 공개 카드(`/cards/{slug}`)와 같은 결이다 — 슬러그가 96비트
난수라 그 자체가 유일한 접근 통제다(SEC-005).

### 아직 없는 것

- **스쿼드 삭제** — 팀 해체 시의 처리가 안 정해졌다(부록 D.6). `squad.team_id` 의
  삭제 규칙을 기본(RESTRICT)으로 둔 것도 같은 이유다
- **포지션 바꾸기** — 지금은 빼고 다시 넣어야 한다. 화면이 요구하면 낸다
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
  "sport_code": "baseball", "side": "right", "duration_ms": 4200
}
```

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
{ "status": "failed", "failure_reason": "품질 게이트 미달" }
```

`204 No Content`.

| 에러 | code | 뜻 |
|---|---|---|
| 404 | `JOB_NOT_FOUND` | 없는 작업이다 |
| 409 | `JOB_NOT_RUNNING` | 집지 않았거나 이미 끝났다. **재시도해도 소용없다** |
| 422 | `INVALID_JOB_STATUS` | `queued`·`running` 으로는 보고할 수 없다 |

**`finished_at` 을 받지 않는다.** 워커의 시계가 어긋나면 소요 시간이 음수가 된다 —
서버가 찍는다. 같은 이유로 `started_at` 은 `claim` 이 찍는다. 🔴 이 두 시각의 차이가
**PER-001 이 보려는 값**이라, `queued` 를 바로 끝낼 수 있게 두면 `started_at` 이 빈
채 `finished_at` 만 차서 그 값이 망가진다.

### 아직 없는 것

- 🔴 **적재(`POST /analyses`)** — 미결 `jin` 1번(적재 규격)이 먼저다.
  `metric_definition` 이 **0 행**이라 지금 만들면 외래키에서 전부 거부된다.
  그때까지 워커의 산출물은 `reports/` 의 JSON 이다
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
- **분석 리포트 조회** — 3-1은 **적재(쓰기)만** 다룬다. 선수가 자기 리포트를 보는
  경로(`GET /me/analyses/...`)는 화면이 정해진 뒤에 낸다
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
