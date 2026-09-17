# 클라이언트가 반영할 백엔드 계약 변경 (2026-08-26 ~ 09-04)

> **받는 사람:** 백성검 (프론트·웹 — `www/`, `flutter/`)
> **보낸 사람:** 정어진 (백엔드 — `fastapi/`)
> **상태:** 전달 · 2026-09-01 (**10·11번을 09-02 에, 12번을 09-03 에 덧붙였다**)
> **확인:** 아래 각 항목의 "확인" 명령을 돌리면 반영 여부가 바로 나온다.

## 이 문서를 쓰는 법

`git pull` 로 받았다면 Claude 에게 이렇게 주면 된다.

```
fastapi/docs/client-contract-changes.md 를 읽고, 각 항목의 "먼저 확인"을 실제로
돌려봐. 이미 만족하는 항목은 손대지 말고 무엇이 이미 되어 있는지만 알려줘.
만족하지 않는 것만 고쳐줘.
```

## 🔴 고치기 전에 — **이미 되어 있는지 먼저 확인한다**

**이 문서는 2026-09-01 의 코드를 읽고 썼다.** 그 뒤에 **다른 방식으로 이미
해결됐을 수 있다.** 그래서 항목마다 **「만족해야 할 성질」과 「먼저 확인」** 을 두었다.

| 확인 결과 | 무엇을 하나 |
|---|---|
| **이미 만족한다** | 🔴 **손대지 않는다.** 형태가 아래 제안과 달라도 **목적이 달성됐으면 그대로 둔다** |
| 만족하지 않는다 | 그때만 고친다 |
| 판단이 애매하다 | 고치지 말고 **물어본다** (백엔드: 정어진) |

🔴 **아래에 적은 파일 이름·함수 이름·코드 조각은 예시지 규격이 아니다.**
지켜야 하는 것은 **「만족해야 할 성질」 한 줄뿐**이고, 그것을 어떻게 이루는지는
클라이언트 쪽 사정이다. **제안과 다르게 되어 있다는 이유로 고치지 말 것.**

> 이미 잘 도는 것은 `✅ 조치 불필요` 로 표시하고 왜 그런지도 적었다 — 멀쩡한 코드를
> 건드리는 것이 이 문서가 낼 수 있는 가장 나쁜 결과다.

---

## 한눈에

| # | 변경 | www | Flutter |
|---|---|---|---|
| 1 | **429 `TOO_MANY_REQUESTS`** (인증 3경로, 1분 10회) | 🔴 조치 필요 | 🔴 조치 필요 |
| 2 | **409 `CANNOT_DELETE_SELF`** (관리자 자기 강제탈퇴 금지) | 🟡 선택 (동작은 정상) | — |
| 3 | `GET /admin/users` 의 `q` 는 **패턴이 아니라 글자** | 🟡 선택 | — |
| 4 | Flutter 가 에러 `code` 를 버린다 | ✅ 조치 불필요 | 🔴 **1번의 선행 조건** |
| 10 | **`POST /me/card` 신설** — 카드는 이제 여기서만 생긴다 (09-02) | 🟡 선택 | 🟡 선택 |
| 11 | 🔴 **웹이 mock 에 고정돼 있다** — 실제 백엔드를 못 부른다 (09-02) | 🔴 조치 필요 | 🟡 절반 붙음 |
| 12 | **클립 업로드 신설** — 두 번 나눠 부른다. 반려도 201 (09-03) | 🟡 선택 | 🟡 선택 |
| 13 | **경기 탐색 신설** — 팀 id 없이 종목·지역으로 찾는다 (09-03) | 🟡 선택 | 🟡 선택 |
| 14 | **경기 수정·취소 신설** — `needs` 는 통째로 갈린다. 지원 붙으면 409 (09-03) | 🟡 선택 | 🟡 선택 |
| 15 | **지원 무르기·거절 신설** — 14번의 409 를 푼다. 되돌릴 수 없다 (09-04) | 🟡 선택 | 🟡 선택 |
| 16 | **평가·신뢰 신설** — 점수 없는 선택형. 순서 정렬 금지. 14일 (09-04) | 🟡 선택 | 🟡 선택 |
| 17 | **구성원에 카드 참조** — 스쿼드 등재가 열린다. 없으면 `null` (09-04) | 🔴 **paik 2번 해소** | 🟡 선택 |
| 18 | **카드 한 줄 꾸미기** — `PATCH /me/card`. 20자, 안 자름 (09-04) | 🔴 **paik 3번 해소** | 🟡 선택 |
| 5 | `PATCH /me/password` — 성공하면 **토큰 전부 폐기** | ⏳ 아직 안 쓴다 | ⏳ 아직 안 쓴다 |
| 6 | `DELETE /me` · `POST /auth/logout-all` | ⏳ 아직 안 쓴다 | ⏳ 아직 안 쓴다 |
| 7 | 401 `INVALID_TOKEN` 에 "폐기된 토큰"이 추가됐다 | ✅ 조치 불필요 | ✅ 조치 불필요 |
| 8 | 새 계정은 빈 상태 (`teams` `[]`, `/me/card` 404) | ✅ 조치 불필요 | ✅ 조치 불필요 |
| 9 | `/docs` 는 개발 환경에서만 열린다 | ✅ 정보 | ✅ 정보 |

---

## 1. 🔴 429 `TOO_MANY_REQUESTS` — 즉시 재시도하면 안 된다

`POST /auth/login` · `POST /auth/signup` · `POST /auth/google` 세 경로에
**같은 출처에서 1분에 10회** 제한이 걸렸다(커밋 `0e298e4`, 5장 SEC-009).

```json
{ "error": { "code": "TOO_MANY_REQUESTS", "message": "요청이 너무 잦습니다. 잠시 후 다시 시도해 주세요." } }
```

✅ **`Retry-After` 가 붙었다** (2026-09-01, 커밋은 아래 "바뀐 점"). **정수 초**이고
고정값이 아니라 **그 시점에 남은 시간**이다. 올림한 값이라 그만큼 기다리면 반드시
한 자리가 비어 있다. **자체 타이머를 만들 필요가 없다.**

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 37
```

> 🔴 **바뀐 점 — 앞서 "Retry-After 가 없다"고 전달한 것을 정정합니다.** 그때는
> 없었고 09-01 에 붙였습니다. 자체 타이머를 이미 만드셨다면 **서버 값을 쓰는 쪽으로
> 바꾸는 편이 낫습니다** — 서버 창과 어긋날 일이 없습니다.
>
> 같이 정정합니다: **"즉시 재시도하면 제한이 영영 안 풀린다"고 적었는데 과장이었습니다.**
> 거부된 요청은 카운터에 넣지 않아서 **재시도가 만료 시각을 밀지는 않습니다.** 다만
> 창이 지나기 전에는 계속 거부되므로 **무의미하고 서버 자원만 씁니다.**

### 만족해야 할 성질

> **인증 요청이 429 로 거부되면, `Retry-After` 가 지나기 전에는 같은 요청이 다시
> 나가지 않는다.**

방식은 상관없다 — 버튼 잠금 · 쿨다운 · 카운트다운 안내 · 전역 재시도 정책 어느
쪽이든 **"429 직후 재요청이 안 나간다"** 면 만족이다. 자동 재시도 로직이 있다면
429 에서 멈추기만 해도 된다.

**대기 시간은 서버가 준 `Retry-After` 를 쓴다.** 임의의 상수(예: 무조건 60초)를
넣으면 필요 이상으로 기다리게 된다 — 남은 시간은 그보다 짧은 경우가 대부분이다.

### 먼저 확인

```bash
grep -rnE "TOO_MANY_REQUESTS|\b429\b" www/src flutter/lib
```

> ⚠️ **`429` 를 단어 경계 없이 찾으면 오탐이 난다.** `www/src/lib/introInk.ts` 와
> `PlayerCardBrush.tsx` 의 난수 상수 `4294967296` 이 걸린다. 위처럼 `\b429\b` 로 찾는다.

- **결과가 있으면** → 그 코드를 읽고 **429 뒤 재요청이 막히는지** 본다.
  막힌다면 ✅ **손대지 않는다.**
- **결과가 없으면** → grep 에 안 걸리는 방식일 수도 있다. 로그인·가입·구글 로그인의
  제출 핸들러를 열어 **실패 후 버튼이 곧바로 다시 눌리는지** 확인한다.
  쿨다운이 이미 있으면(코드와 무관하게 걸려 있으면) ✅ 그대로 둔다.
- 둘 다 아니면 → 아래를 참고해 고친다.

### 아직이라면 — 참고용 제안 (규격 아님)

#### 🔴 www — `Retry-After` 는 **지금 브라우저까지 오지 않는다** (프록시가 버린다)

2026-09-01 에 확인한 것이다. `www` 는 프록시라 헤더가 세 곳을 지나야 하는데
**중간에 끊긴다.** 헤더를 쓰려면 이어 주어야 한다.

| 자리 | 지금 | 필요한 것 |
|---|---|---|
| `src/server/backend/errors.ts` | `BackendError` 가 `status`·`code`·`message` 만 갖는다 | 백엔드 응답의 `Retry-After` 를 함께 들고 온다 |
| `src/app/api/auth/*/route.ts` | `NextResponse.json(errorResponseBody(e), { status })` — **헤더를 안 싣는다** | 429 면 `Retry-After` 를 응답 헤더에 싣는다 |
| `src/lib/api/client.ts` | `send()` 가 `res.headers` 를 안 읽는다 | `res.headers.get('retry-after')` 를 `ApiCallError` 에 싣는다 |

**Flutter 는 백엔드를 직접 부르므로 헤더가 그대로 온다** — 이 문제가 없다.

> 💬 **세 곳을 고치는 게 번거로우면 말해 주세요.** 백엔드가 에러 본문에도
> `retry_after` 를 넣어 드릴 수 있습니다(프록시가 본문은 그대로 넘기므로 고칠 곳이
> 한 곳으로 줍니다). 헤더가 HTTP 표준이고 다른 헤더도 언젠가 필요할 것 같아
> **일단 헤더만** 두었습니다. 편한 쪽으로 맞추겠습니다.

#### 화면 쪽 — 참고용 예시

에러 문구까지는 이미 잘 나온다. `ApiCallError` 가 `status` 와 `code` 를 들고 있고
(`src/lib/api/client.ts`) 로그인 화면이 `apiErrorMessage(err)` 로 서버 문구를 띄운다.
**비어 있는 것은 "다시 누르지 못하게" 하는 쪽이다.**

```ts
// src/lib/api/client.ts — 판별 헬퍼 예시
/** 429. 대기 시간은 서버가 준 Retry-After(초)를 쓴다 — 임의의 상수를 두지 않는다. */
export function isRateLimited(err: unknown): boolean {
  return err instanceof ApiCallError && err.code === 'TOO_MANY_REQUESTS'
}
```

이걸 `src/app/login/page.tsx` · `src/app/signup/page.tsx` 의 `catch (err)` 와
`src/components/auth/GoogleSignInButton.tsx` 의 `onError` 에서 써서 제출을 잠근다.
잠그는 시간은 위 표대로 `Retry-After` 를 끌어온 뒤 그 값을 쓴다.

**Flutter 는 4번이 선행 조건이다** — `code` 를 버리고 있어 429 를 분기할 수단이 없다.

---

## 2. 🟡 409 `CANNOT_DELETE_SELF` — 관리자가 자기 자신을 지울 수 없다

`DELETE /api/v1/admin/users/{user_id}` 에 대상이 **자기 자신**이면 409 다(`72b322b`).
지운 사람이 사라지면 감사 기록의 상대가 없어지고 되돌릴 방법도 없어서 막았다.
관리자 본인의 탈퇴는 비밀번호를 확인하는 `DELETE /me` 가 맡는다.

### www — ✅ 동작은 이미 정상이다. 개선은 선택

`src/app/admin/users/[id]/ForceDeleteButton.tsx` 가 `catch` 에서
`setError(apiErrorMessage(err))` 를 하므로 **"자기 자신은 강제 탈퇴시킬 수 없습니다."
가 그대로 뜨고 버튼도 정상으로 돌아온다.** 고장 나지 않는다.

🟡 **원하면** 자기 자신일 때 버튼을 아예 그리지 않는 편이 낫다 — 지금은
`window.confirm` 까지 통과한 뒤에야 실패한다.

**먼저 확인** — 이미 감춰져 있으면 손대지 않는다.

```bash
grep -rn "currentUser\|CANNOT_DELETE_SELF" www/src/app/admin
```

없다면: 현재 로그인 사용자 id 는 `src/server/currentUser.ts` 로 얻을 수 있고,
상세 페이지가 서버 컴포넌트라 `ForceDeleteButton` 을 조건부로 렌더하면 된다.

---

## 3. 🟡 `GET /admin/users` 의 `q` 는 패턴이 아니라 글자다

`%` · `_` · `\` 를 그대로 **그 문자로** 찾는다. 와일드카드로 쓸 수 없다(`72b322b`).
전에는 `q=%` 하나로 전체가 걸렸는데 그게 버그였다.

덧붙여 계약에 명시한 것 둘 — 목록은 **`created_at` 내림차순**(최근 가입 순)이고,
`total` 은 페이지가 아니라 **검색 결과 전체**의 개수다.

### www — 🟡 선택

`src/app/admin/users/AdminSearchForm.tsx` 는 문자열을 그대로 넘기므로 **틀린 데가
없다.** 사용자가 `%` 를 와일드카드로 기대할 수 있다는 점만 안내 문구로 다루면 된다.

🔴 **검색어를 클라이언트에서 가공하지 말 것.** `%` 를 떼거나 이스케이프하면
오히려 어긋난다 — 백엔드가 이미 리터럴로 다룬다. 그런 처리가 들어가 있다면
그것이 고칠 대상이다.

```bash
grep -rn "replace\|encodeURI" www/src/app/admin/users/AdminSearchForm.tsx   # 가공이 있는지
```

---

## 4. 🔴 Flutter 가 에러 `code` 를 버린다 — 1번의 선행 조건

`flutter/lib/features/auth/data/auth_repository_api.dart` 의 `_decode` 가 이렇다.

```dart
final error = decoded['error'] as Map<String, dynamic>?;
throw AuthException(
  (error?['message'] as String?) ?? '알 수 없는 오류 (${response.statusCode})',
);
```

`message` 만 꺼내고 **`code` 를 버린다.** `AuthException`
(`flutter/lib/features/auth/data/auth_repository.dart`)도 `message` 하나만 갖는다.

문구를 보여주는 데는 문제가 없지만 **분기가 불가능하다.** 429 든 401 이든 화면 쪽에서
구별할 수 없다. 원래 주석에 "코드는 화면 쪽에서 필요해지면 그때 노출한다"고 적혀
있는데, **지금이 그때다.**

### 만족해야 할 성질

> **화면 코드가 에러의 종류(`code` 또는 HTTP 상태)를 구별할 수 있다.**

`AuthException` 에 필드를 더하든, 예외 타입을 나누든, 결과 객체로 바꾸든 상관없다.

### 먼저 확인

```bash
grep -n "code\|statusCode" flutter/lib/features/auth/data/auth_repository.dart
```

- **`code`·`statusCode` 를 들고 있거나 예외 타입이 나뉘어 있으면** → ✅ 이미 열려
  있다. **손대지 않는다.**
- 없으면 → 아래를 참고해 연다.

### 아직이라면 — 참고용 제안 (규격 아님)

- `auth_repository.dart` — `AuthException` 에 `code` 와 `status` 를 넣는다.
  기존 호출부(`auth_repository_mock.dart` 등)가 `const AuthException('문구')` 로
  부르고 있으므로 **새 필드를 선택 인자로** 두면 그쪽을 안 고쳐도 된다.
- `auth_repository_api.dart` — `_decode` 에서 `error['code']` 와
  `response.statusCode` 를 함께 실어 던진다.
- 그 다음 1번(429)을 처리한다.

---

## 5·6. ⏳ 아직 안 쓰는 API — 붙일 때 알아야 할 것

`www/src/server/backend/gateway.ts` 의 `Backend` 인터페이스를 보면 지금 쓰는 것은
signup · login · loginWithGoogle · getMe · updateMe · getMyCard · getPublicCard ·
listUsers · getUserDetail · forceDeleteUser 다. **아래 셋은 아직 없다.**

| API | 알아야 할 것 |
|---|---|
| `PATCH /me/password` | 🔴 성공하면 **그 사용자의 토큰이 전부 폐기된다.** 세션 쿠키를 지우고 재로그인으로 보내야 한다. 안 그러면 다음 요청이 401 로 떨어진다 (`35c66d2`) |
| `DELETE /me` | 204. **비밀번호를 본문에 실어야 한다** — 없으면 422 `PASSWORD_REQUIRED`, 틀리면 401 `INVALID_CREDENTIALS` (`35c66d2`) |
| `POST /auth/logout-all` | 204. 다른 기기 세션까지 끊는다 (`408f57e`) |

---

## 7·8·9. ✅ 조치 불필요 — 알고만 있으면 된다

- **401 `INVALID_TOKEN` 에 "폐기된 토큰"이 추가됐다**(`408f57e`). 비밀번호 변경 ·
  탈퇴 · `logout-all` 뒤의 옛 토큰이 여기로 떨어진다. **클라이언트가 할 일은 전과
  같다 — 토큰을 버리고 다시 로그인.** 그래서 서버도 사유를 구분하지 않는다.
- **새 계정은 빈 상태다.** `GET /me` 의 `teams` 가 빈 배열이고 `GET /me/card` 는
  **404 `CARD_NOT_FOUND`** 다. 오류가 아니라 정상이며, 빈 화면을 보여주면 된다.
- **`/docs` 와 `/openapi.json` 은 개발 환경에서만 열린다**(`4a97875`).
  배포 주소에서 404 가 나는 것은 고장이 아니다.

---

## 10. 🟡 `POST /me/card` 가 생겼다 — **카드는 이제 여기서만 생긴다** (2026-09-02 추가)

> 이 항목은 09-01 에 보낸 뒤 **나중에 덧붙인 것**이다. 고장 난 것을 고치라는 요청이
> 아니라 **새로 생긴 것을 알리는 항목**이다.

지금까지 카드를 만드는 경로가 **코드 어디에도 없었다.** 그래서 모든 계정이
`GET /me/card` 에서 404 였고, 공유 링크(SFR-009)가 끝에서 끝까지 성립하지 않았다.
카드가 언제 생기는지가 요구사항에 "미정"으로 남아 있어서다.

**요청할 때 생기는 것으로 정했다**(계약 문서 3장). `POST /api/v1/me/card` 는 멱등이라
두 번 불러도 카드는 하나고 슬러그도 그대로다 — 201(새로 만듦) 또는 200(이미 있음).

### 만족해야 할 성질

**사용자가 카드를 만들 수 있는 자리가 화면에 있을 것.** 어디에 어떤 모양으로 둘지는
클라이언트 쪽 사정이다.

- 404 `CARD_NOT_FOUND` 처리는 **그대로 두면 된다.** 여전히 정상 상태다 —
  기존 계정은 부르기 전까지 카드가 없다
- 응답 본문은 `GET /me/card` 와 **완전히 같다.** 파서를 새로 만들 필요가 없다
- 201 과 200 을 다르게 다룰 필요는 없다. 굳이 나눈다면 "만들었습니다" 안내 정도다

### 먼저 확인

```bash
grep -rn "me/card" www/src flutter/lib | grep -i "post\|create"
```

결과가 있으면 이미 붙인 것이다 — **손대지 않는다.**

### 하지 말아야 할 것

- 🔴 **화면을 열 때 자동으로 부르지 않는다.** 공개 링크가 생기는 것은 사용자의
  행위여야 한다. `GET` 이 쓰기를 하지 않도록 일부러 나눈 것이라, 조회 시점에
  자동 호출하면 그 구분이 무의미해진다
- `og_image_key` 를 이미지 주소로 **그리지 않는다.** 규칙대로 값은 채우지만
  **그 위치에 파일이 아직 없다** (생성기 미구현). 지금처럼 고정 장식 이미지를 쓰면 된다
- 슬러그를 클라이언트에서 만들지 않는다. 서버가 무작위로 만든다(SEC-005)

---

## 11. 🔴 웹이 **가짜 데이터에 고정**돼 있습니다 (2026-09-02 확인)

> 09-02 에 덧붙인 항목입니다. 고장이 난 것이 아니라 **아직 안 이어진 자리**를
> 적어 두는 것입니다 — 지금 어디에도 기록이 없어서 나중에 "웹이 왜 백엔드를 못
> 보지"를 다시 조사하게 됩니다.

백엔드가 2026-09-02 부터 EC2 에서 돕니다(계약: 이 폴더의 `api-contract.md`).
그런데 웹은 실제 백엔드를 **부를 수 없는 상태**입니다.

```ts
// www/src/server/backend/index.ts
export function getBackend(): Backend {
  if (process.env.USE_MOCK === '1') return mockBackend
  // Task 11 에서 fastapiBackend 로 바꾼다.
  return mockBackend        // ← 환경변수와 무관하게 언제나 mock
}
```

구조는 이미 다 있습니다 — 브라우저는 같은 오리진의 `/api/*` 만 부르고(`lib/api/client.ts`),
라우트 핸들러 8개가 `getBackend()` 를 거칩니다. **바꿔 끼울 자리 하나가 비어 있는 것**입니다.

### 만족해야 할 성질

**`USE_MOCK` 이 켜져 있지 않으면 실제 FastAPI 를 부를 것.** 파일 이름·구현 방식은
클라이언트 쪽 사정입니다(`fastapiBackend` 는 기존 주석의 이름일 뿐 규격이 아닙니다).

- 백엔드 주소는 **서버 전용 환경변수**로 받습니다. `NEXT_PUBLIC_` 을 붙이면 브라우저
  번들에 박혀서, 같은 오리진만 부른다는 지금 설계가 무너집니다
- 에러 봉투는 그대로입니다 — `{"error":{"code","message"}}`. `mock.ts` 가 던지는
  `BackendError(status, code, message)` 를 그대로 쓰면 화면 쪽은 고칠 것이 없습니다
- 🔴 **`Retry-After` 는 세 곳에서 버려집니다**(1번 항목). 실제 백엔드를 붙이는 김에
  함께 이으면 두 번 고치지 않습니다

### 먼저 확인

```bash
grep -c 'return mockBackend' www/src/server/backend/index.ts      # 2 면 아직 mock 고정
grep -rn 'BACKEND_URL\|API_BASE' www/src www/.env* 2>/dev/null | wc -l   # 0 이면 주소를 모른다
grep -rln 'fetch(' www/src/server/backend/ | grep -v mock | wc -l  # 0 이면 밖을 부르는 구현이 없다
```

2026-09-02 기준 **2 · 0 · 0** 입니다. 셋 다 바뀌면 붙은 것입니다.

### 앱(`flutter`)은 절반 붙어 있습니다

`apiBaseUrl`(`core/network/api_config.dart`)로 실제 호출을 하는데 **쓰는 곳이
`auth_repository_api.dart` 하나뿐**입니다 — 로그인만 실물이고 카드·팀·경기 화면은
아직 API 를 부르지 않습니다.

```bash
grep -rl 'apiBaseUrl' flutter/lib --include='*.dart' | wc -l   # 2 (정의 1 + 쓰는 곳 1)
```

기본 주소가 `http://127.0.0.1:8000/api/v1` 이라 **로컬에서 백엔드를 띄우면 지금도
로그인이 됩니다.** 다른 주소를 볼 때는 `--dart-define=API_BASE_URL=...` 입니다.

### 🔴 배포본끼리 붙는 것은 아직 막혀 있습니다

EC2 의 보안 그룹이 **22번만** 열려 있어 Vercel 의 웹도, 폰의 앱도 배포된 백엔드에
닿지 못합니다(미결 8번, 담당 박민호). 열리면 nginx·TLS 는 백엔드 쪽에서 잇겠습니다.

**다만 위 구현은 지금 해도 됩니다** — 로컬에서 `uvicorn` 을 띄우고 `USE_MOCK` 을 끄면
바로 확인됩니다. 포트 개방을 기다릴 필요가 없습니다.

### 하지 말아야 할 것

- `mock.ts` 를 **지우지 않습니다.** 계약 테스트가 DB 없이 도는 근거고, 백엔드가 없을
  때 화면을 보는 수단입니다. `USE_MOCK=1` 로 남겨 둡니다
- 브라우저에서 FastAPI 를 **직접 부르지 않습니다.** 지금 설계는 "브라우저는 같은
  오리진만" 이고, 바꾸면 CORS·쿠키·토큰 보관이 전부 딸려 옵니다

---

## 12. 🟡 클립 업로드가 열렸습니다 — **두 번 나눠 부릅니다** (2026-09-03 추가)

> 09-03 에 덧붙인 항목입니다. 고장 난 것을 고치라는 요청이 아니라 **새로 생긴
> 것을 알리는 항목**입니다. 화면(`/videos`, `/videos/upload`)이 설계에는 있고
> 붙일 백엔드가 이제 생겼습니다.

`POST /api/v1/videos/upload-url` · `POST /api/v1/videos` · `GET /api/v1/videos`.
전체 규격은 계약 문서 **3-6절**입니다.

```
(1) POST /videos/upload-url   {content_type, size_bytes} -> {storage_key, upload_url, expires_in}
(2) PUT  <upload_url>          파일 본문. Content-Type 을 (1)과 같게 보냅니다
(3) POST /videos               {sport_code, storage_key, duration_ms, width, height, side?}
```

원본은 **앱 서버를 지나지 않습니다**(PER-002). (2)는 S3 로 직접 갑니다.

### 🔴 반려는 실패가 아닙니다 — `201` 입니다

규격에 안 맞는 클립도 **201 로 등록되고** `passed: false` 와 `reject_reason` 이
옵니다. 사유를 값으로 남기는 것이 이 경로의 목적(SFR-001)이라 422 로 돌려보내지
않습니다.

**상태 코드로 분기하면 반려를 놓칩니다. `passed` 로 분기하십시오.**

### 만족해야 할 성질

1. **클립을 올릴 수 있는 자리가 화면에 있을 것.** 위 세 단계를 거치면 됩니다
2. **반려된 클립의 사유가 사용자에게 보일 것.** `reject_reason` 은 그대로 보여줄 수
   있는 한국어 문장입니다("해상도가 상한을 넘습니다: 3840x2160 (상한 1920x1080)")
3. **분석 상태를 목록에서 볼 수 있을 것.** `GET /videos` 의 `analysis_status`
   (`queued`·`running`·`succeeded`·`failed`, 반려면 `null`)

어디에 어떤 모양으로 둘지는 클라이언트 쪽 사정입니다. 플러터 설계 문서의
`/videos`(영상 상세 펼침 + 규격 반려 사유 바텀시트)에 맞춰 응답을 짰습니다.

### 먼저 확인

```bash
grep -rn "upload-url" www/src flutter/lib
```

결과가 있으면 이미 붙인 것입니다 — **손대지 않습니다.**

### 상한 (2026-09-03 결정)

| 항목 | 값 | 어디서 걸리나 |
|---|---|---|
| 용량 | 200MB | (1)에서 `FILE_TOO_LARGE`, (3)에서 실측 반려 |
| 길이 | 60초 | (3)에서 반려 |
| 해상도 | 1920x1080 | (3)에서 반려 |
| 형식 | mp4 · mov | (1)에서 `UNSUPPORTED_FORMAT` |

**올리기 전에 클라이언트에서 먼저 걸러 주시면** 200MB 를 올린 뒤 반려되는 일을
줄일 수 있습니다. 다만 **서버 검사를 대신하는 것은 아닙니다** — 상한이 바뀌면
서버만 고칠 수 있게 해 두었습니다.

### 하지 말아야 할 것

- 🔴 **`storage_key` 를 클라이언트에서 만들지 않습니다.** 키에 업로더가 들어 있고
  (`videos/<user_id>/<uuid>.mp4`) 서버가 등록할 때 대조합니다. 직접 지으면 403 입니다
- 🔴 **(2)의 `Content-Type` 을 바꾸지 않습니다.** 서명에 들어 있어 다르면 S3 가
  거절합니다. (1)에 보낸 값 그대로 보냅니다
- **`expires_in`(기본 900초)이 지난 URL 을 재사용하지 않습니다.** (1)부터 다시 받습니다
- 파일을 **앱 서버로 보내지 않습니다.** `POST /videos` 는 메타만 받습니다

### ✅ 서버에서 실제로 돕니다 (2026-09-03 오후 정정)

앞서 이 자리에 "서버에 버킷이 아직 없으면 503"이라고 적었는데, **같은 날 켰습니다.**
사전 서명 URL 발급 → S3 로 PUT → 등록 → 반려 → 목록까지 서버에서 확인했습니다.
**이제 붙이시면 됩니다.**

⚠️ `STORAGE_NOT_CONFIGURED`(503)가 오면 서버 설정이 빠진 것이지 클라이언트 잘못이
아닙니다 — 그때는 알려 주십시오.

---

## 13. 🟡 경기 탐색이 열렸습니다 — `/matches` 화면이 이제 그려집니다 (2026-09-03 추가)

`GET /api/v1/matches?sport_code=&region=&page=&size=`. 규격은 계약 문서 3-4절입니다.

**지금까지 경기 목록은 팀 id 를 알아야만 볼 수 있었습니다.** 그래서 플러터 설계의
`/matches`(경기 탐색) 화면을 그릴 데이터가 없었습니다. 이제 있습니다.

### 만족해야 할 성질

**종목·지역으로 경기를 찾을 수 있는 화면이 있을 것.** 한 줄에 필요한 값
(팀 이름·지역·종목·시각·장소·필요 포지션)이 **응답 하나에 다 들어 있습니다** —
팀을 따로 조회하지 않아도 됩니다.

### 먼저 확인

```bash
grep -rn '"/matches"\|/matches?' www/src flutter/lib
```

결과가 있으면 이미 붙인 것입니다 — **손대지 않습니다.**

### 알아 두실 것

- **다가오는 경기만** 옵니다. 이른 것이 앞입니다
- 페이지 형식이 `GET /admin/users` 와 **같습니다**(`items`·`total`·`page`·`size`) —
  페이지 처리를 재사용하시면 됩니다
- `region` 은 **부분 일치**입니다. "서울"로 "서울 강남구"가 걸립니다
- 🔴 **종목 코드가 틀리면 빈 배열이 아니라 422 `UNKNOWN_SPORT`** 입니다. 빈 배열로
  답하면 오타와 "경기가 없다"가 같아 보이기 때문입니다. 지역은 자유 문자열이라
  안 걸리면 그냥 빈 목록입니다

### 하지 말아야 할 것

- **포지션 필터를 서버에 요청하지 마십시오** — 아직 없습니다. `needs` 가 응답에
  실려 오니 **화면에서 거르시면 됩니다.** 목록이 길어져 서버 필터가 필요해지면
  말씀해 주십시오, 그때 냅니다
- `size` 는 **100 이 상한**입니다. 넘기면 422 입니다

---

## 14. 🟡 경기 수정·취소가 열렸습니다 (2026-09-03 추가)

`PATCH /api/v1/matches/{id}` · `DELETE /api/v1/matches/{id}`. **주장만** 쓸 수
있습니다. 규격은 계약 문서 3-4절입니다.

### 만족해야 할 성질

**주장이 자기 팀 경기를 고치고 취소할 수 있는 자리가 화면에 있을 것.** 어디에 어떤
모양으로 둘지는 클라이언트 쪽 사정입니다.

### 알아 두실 것 셋

1. **`PATCH` 는 보낸 것만 바꿉니다.** 다만 🔴 **`needs` 를 보내면 통째로 갈아
   끼웁니다** — 남길 포지션까지 전부 보내셔야 합니다. 하나만 빼려고 그것만 보내면
   나머지가 사라집니다
2. **취소는 `204` 입니다**(본문 없음). 그리고 🔴 **지원이 하나라도 붙었으면
   `409 MATCH_HAS_APPLICATIONS`** 입니다 — 취소가 행 삭제라서 생긴 경계입니다
3. **지난 경기는 수정도 취소도 `422 PAST_MATCH`** 입니다

### 🔴 정정 (2026-09-04) — **409 를 이제 풀 수 있습니다**

앞서 **"지원을 무르는 경로가 아직 없어 지원이 붙은 경기는 취소할 방법이 없다"**고
전달했습니다. **2026-09-04 에 그 경로를 냈습니다** — 아래 **15번**입니다.

**409 를 "영영 취소 불가"로 안내하셨다면 고쳐 주십시오.** 이제는 "지원을 먼저
정리하면 취소할 수 있다"가 맞습니다. 아직 안 붙이셨다면 15번 것만 보시면 됩니다.

화면에서는 여전히 **409 를 재시도로 풀리는 오류처럼 다루지 말아 주십시오** —
사람이 지원을 정리해야 풀립니다.

### 🔴 지원자에게 알림이 가지 않습니다

시각·장소를 바꿔도 **지원자는 모릅니다.** 알림 인프라가 없습니다. 수정 자체를 막지
않은 것은, 막으면 오타 하나를 못 고치게 되고 그쪽이 더 나쁘다고 봐서입니다.

**화면에서 "지원자에게 따로 알려 주세요" 정도의 안내를 붙여 주시면** 좋겠습니다 —
서버가 대신 알릴 수 없습니다.

### 먼저 확인

```bash
grep -rn "matches/" www/src flutter/lib | grep -i "patch\|delete"
```

결과가 있으면 이미 붙인 것입니다 — **손대지 않습니다.**

---

## 15. 🟡 지원 무르기·거절이 열렸습니다 — **14번의 409 가 이걸로 풀립니다** (2026-09-04 추가)

`DELETE /api/v1/matches/{match_id}/applications/{application_id}` → `204`.
규격은 계약 문서 3-5절입니다.

**한 경로가 둘을 겸합니다.** 지원 당사자가 부르면 **무르기**, 주최 팀 주장이 부르면
**거절**입니다 — 하는 일이 같아서(행을 지웁니다) 나누지 않았습니다.

### 만족해야 할 성질

1. **지원자가 자기 지원을 무를 수 있는 자리가 있을 것** — 지원 목록·내 지원 화면 등
2. **주장이 지원을 거절할 수 있는 자리가 있을 것** — 지원자 목록에서
3. **취소가 409 로 막혔을 때 무엇을 해야 하는지 화면이 알려 줄 것** — "지원을 먼저
   정리하세요"

어디에 어떤 모양으로 둘지는 클라이언트 쪽 사정입니다. **위 경로 이름은 예시가 아니라
규격이지만**, 화면 구성은 정해 드리지 않습니다.

### 알아 두실 것 넷

1. **되돌릴 수 없습니다.** 행을 지우므로 **거절 이력이 남지 않습니다.** 확인 창을
   두시는 편이 좋습니다
2. **확정된 건도 지워집니다**(양쪽 수락이 다 찬 것). 그렇지 않으면 취소가 다시
   막히기 때문입니다 — 화면에서 이 경우를 더 강하게 확인받으셔도 됩니다
3. 🔴 **지난 경기는 `422 PAST_MATCH`** 입니다. 확정된 행이 "누가 그 경기에
   뛰었나"의 유일한 근거라 경기 후에는 못 지웁니다
4. **당사자도 주장도 아니면 `403 FORBIDDEN`**, 없는 건은 `404 APPLICATION_NOT_FOUND`

### ⚠️ 상대에게 알림이 가지 않습니다

거절해도 **지원자는 모릅니다.** 알림 인프라가 없습니다(14번과 같은 사정입니다).
화면에서 "지원자에게 따로 알려 주세요" 정도의 안내를 붙여 주시면 좋겠습니다.

### ⚠️ 한 번에 지우는 경로는 없습니다

일부러 두지 않았습니다 — 알림이 안 가므로 **건별로 사람이 정리하는 편**이 맞다고
봤습니다. 필요하시면 말씀해 주십시오.

### 먼저 확인

```bash
grep -rn "applications/" www/src flutter/lib | grep -i "delete"
```

결과가 있으면 이미 붙인 것입니다 — **손대지 않습니다.**

---

## 16. 🟡 평가·신뢰가 열렸습니다 — 경기 후 화면이 그려집니다 (2026-09-04 추가)

부록 D 도메인 ⑤ 전부입니다. 규격은 계약 문서 **3-9절**.

| 경로 | 무엇 |
|---|---|
| `GET /api/v1/review-options` | 평가 선택지 목록 |
| `POST /api/v1/matches/{id}/reviews` | 평가 제출 |
| `POST /api/v1/matches/{id}/no-shows` | 불참 기록 (**주장만**) |
| `POST /api/v1/reports` | 신고 접수 |

### 만족해야 할 성질

**경기가 끝난 뒤 참가자가 서로 평가할 수 있는 자리가 화면에 있을 것.** 어디에 어떤
모양으로 둘지는 클라이언트 쪽 사정입니다.

### 🔴 알아 두실 것 넷

1. **평가에 점수가 없습니다.** 별점·슬라이더를 만들지 마십시오 — 선택지를 고르는
   형태입니다. 보내는 것은 `option_codes` 배열뿐입니다
2. 🔴 **`GET /review-options` 가 준 순서를 그대로 쓰십시오.** `category` 로 묶어
   그리시되 **정렬하지 마십시오** — 알파벳순이면 「주의」가 맨 앞에 옵니다
   (`caution` < `manner`). 서버가 매너 · 실력 · 재매칭 · 주의 순으로 줍니다
3. **평가 기간은 경기 후 14일**입니다. 지나면 `422 REVIEW_WINDOW_CLOSED` 입니다.
   ⚠️ **`422 MATCH_NOT_PLAYED`(아직 안 끝남)와 다릅니다** — 화면 안내를 나눠
   주십시오. "아직 평가할 수 없습니다" vs "평가 기간이 지났습니다"
4. **불참 기록은 주장만** 됩니다. 용병에게는 그 버튼을 아예 안 보이게 하는 편이
   낫습니다 — 눌러야 `403` 을 받습니다

### ⚠️ 신고는 응답에 내용이 없습니다

`{id, target_user_id, created_at}` 만 옵니다. `reason` 을 되돌려주지 않으니 화면에
다시 보여주려면 **보낸 값을 들고 계셔야** 합니다. 그리고 **접수만 됩니다** —
처리 경로는 아직 없습니다.

### 먼저 확인

```bash
grep -rn "review-options\|/reviews\|/no-shows\|/reports" www/src flutter/lib
```

결과가 있으면 이미 붙인 것입니다 — **손대지 않습니다.**

---

## 17. 🟡 구성원 목록에 **카드 참조**가 실립니다 — 스쿼드 등재가 열립니다 (2026-09-04 추가)

미결 `paik` 2번 그대로입니다. `GET /api/v1/teams/{team_id}` 의 `members[]` 에 두
값이 늘었습니다.

```json
{ "user_id": "…", "nickname": "홍길동", "role": "owner", "joined_at": "…",
  "player_card_id": "7b2d…", "card_public_slug": "brave-tiger-1234" }
```

| 값 | 쓰는 곳 |
|---|---|
| `player_card_id` | **스쿼드 등재** — `POST /teams/{id}/squad/members` 가 받는 값 |
| `card_public_slug` | **카드로 가는 링크** — `GET /cards/{slug}` |

말씀하신 대로 **등재에 쓸 값과 링크에 쓸 값을 나눠** 실었습니다. 하나만 주면
화면이 나머지를 얻을 경로가 없습니다.

### 🔴 카드가 없는 구성원은 둘 다 `null` 입니다

**그래도 목록에는 남습니다** — 「하지 말 것」에 적어 주신 그대로입니다. 화면에서
`player_card_id` 가 `null` 인 사람은 **등재 버튼을 비활성**으로 두시면 됩니다
(누르면 서버가 막지만, 눌러 보고 알게 하는 것보다 낫습니다).

### 먼저 확인

```bash
curl -s -H "Authorization: Bearer $T" $API/teams/$TEAM | jq '.members[0]'
```

`player_card_id` 가 보이면 반영된 것입니다.

⚠️ 스키마는 안 바꿨습니다 — `player_card` 를 조인해서 실어 주는 것뿐이라
**기존 필드는 그대로**입니다.

---

## 18. 🟡 카드를 **꾸밀** 수 있습니다 — 한 줄이 생겼습니다 (2026-09-04 추가)

미결 `paik` 3번. `PATCH /api/v1/me/card` 로 **사람이 정하는 한 줄**을 바꿉니다.

```json
{"tagline": "THREE LUNGS"}
```

응답은 `GET /me/card` 와 같은 형태이고, **`GET /cards/{slug}`(공개 카드)에도
실립니다.**

### 만족해야 할 성질

**사람이 정한 값이 카드에 실릴 것.** 지금 화면의 붙박이 상수(`THREE LUNGS`)를
이 값으로 갈아 끼우시면 됩니다. 안 정한 사람은 `null` 이니 그때 무엇을 보일지는
화면 쪽에서 정해 주십시오(빈 줄 / 기본 문구 / 안 그리기).

### 알아 두실 것 넷

1. **20자까지**입니다. 넘으면 `422` 입니다 — 🔴 **서버가 안 자릅니다.** 자르면 쓴
   것과 보이는 것이 달라져서, 입력란에서 미리 막아 주시는 편이 좋습니다
2. **`null` 이나 공백만 보내면 지웁니다.** "지우기" 버튼을 따로 만들 필요가 없습니다
3. **카드가 없으면 `404 CARD_NOT_FOUND`** 입니다. 수정이 생성을 겸하지 않습니다 —
   만드는 자리는 `POST /me/card` 하나 그대로입니다(10번)
4. `tagline` 은 `user.nickname`(이름)·`titles`(호칭)와 **다른 값**입니다. 호칭은
   분석이 주는 것이라 여전히 사람이 못 고칩니다

### 🔴 `public_slug` 는 못 바꿉니다

말씀하신 그대로입니다 — 요청 본문에 **자리를 아예 안 뒀습니다.** 보내셔도
무시됩니다. `og_image_key` 도 같습니다.

### ⚠️ 사진은 아직입니다

`og_image_key` 가 "규칙은 있는데 파일이 없는" 상태 그대로입니다. **저장 위치부터
정해야 한다**고 하신 것이 맞아서, 업로드는 이번에 안 넣었습니다.

### 먼저 확인

```bash
curl -s -X PATCH -H "Authorization: Bearer $T" -H 'Content-Type: application/json' \
  -d '{"tagline":"THREE LUNGS"}' $API/me/card | jq .tagline
```

---

## 19. 🟡 분석을 걸지 않고 클립만 올릴 수 있습니다 (2026-09-08 추가)

미결 `paik` 4번. `POST /videos` 요청 본문에 **`analyze: false`** 를 실으면 규격은
검사하되 분석 작업을 만들지 않습니다. 이미 그렇게 보내고 계신 그대로입니다.

```json
{ "sport_code": "football", "storage_key": "...", "duration_ms": 10200,
  "width": 1920, "height": 1080, "analyze": false }
```

### 만족해야 할 성질

`analyze: false` 로 등록한 클립은 응답의 **`analysis_job_id` 가 `null`** 입니다.
그러면 「업로드 영상」 갈래(가르는 기준이 `analysis_job_id`)에 들어갑니다.

### 알아 두실 것 셋

1. **생략하면 참입니다.** `analyze` 를 안 보내면 지금처럼 분석이 걸립니다 —
   분석 화면(`/analysis`)의 저장은 그 동작 그대로입니다. 기본값은 안 바뀌었습니다
2. **규격 검사는 그대로 돕니다.** `analyze: false` 라도 반려 사유가 있으면
   `passed: false` 와 `reject_reason` 이 옵니다. 반려된 클립은 원래 작업이 없습니다
3. **`analyze` 는 되돌릴 수 있는 값이 아닙니다** — 나중에 분석을 걸려면 재분석
   경로가 필요한데 아직 없습니다(계약 3-6 「아직 없는 것」)
4. 🟢 **`analyze: false` 면 해상도 상한(1920x1080)을 안 봅니다** (2026-09-08 추가).
   4K 로 찍은 클립도 기록용으로는 올라갑니다. 그 상한은 분석 워커를 지키는
   값이라(4K 는 host RAM 이 터집니다) 분석을 걸 때만 삽니다. 용량 200MB·길이 60초
   상한은 `analyze` 와 무관하게 그대로입니다

### 먼저 확인

```bash
curl -s -X POST -H "Authorization: Bearer $T" -H 'Content-Type: application/json' \
  -d '{"sport_code":"football","storage_key":"'"$KEY"'","duration_ms":10200,"width":1920,"height":1080,"analyze":false}' \
  $API/videos | jq '.passed, .analysis_job_id'
# true, null 이면 된 것입니다
```

---

## 20. 🟢 클립을 공개로 돌리고 제목을 달 수 있습니다 — 재생 주소도 생겼습니다 (2026-09-08 추가)

미결 `paik` 5번의 **네 조각 전부**. (1+2 를 먼저 내고 3+4 를 같은 날 이어 붙였습니다 —
아래 「3·4 조각」.)

| 무엇 | 상태 |
|---|---|
| 클립의 **공개 여부** | ✅ `PATCH /videos/{id}` `{"is_public": true}` |
| **공개 클립 목록** | ✅ `GET /videos/public` |
| **재생용 주소** | ✅ `GET /videos/{id}/playback-url` (사전 서명 GET URL) |
| **제목·한 줄 설명** | ✅ `PATCH /videos/{id}` `{"title": …, "description": …}` |

### 만족해야 할 성질

`PATCH /videos/{id}` 로 공개로 돌린 클립이 **다른 계정으로 로그인해도**
`GET /videos/public` 목록에 뜹니다. `GET /videos`(내 목록)의 각 줄에도 이제
`is_public` 이 실립니다.

### 알아 두실 것 넷

1. **기본은 비공개입니다.** 등록(`POST /videos`)으로는 공개 여부를 못 정합니다 —
   보내도 무시되고 항상 `false` 로 저장됩니다. 이미 올라간 클립도 전부 비공개입니다
2. **남의 클립·없는 클립은 `404 VIDEO_NOT_FOUND`** 입니다. "남의 것이라 안 된다"와
   "없다"를 구별해 주지 않습니다
3. **`GET /videos/public` 은 로그인이 필요합니다.** 익명(비로그인) 홈에서
   부르셔야 하면 알려 주세요 — 지금은 인증을 그대로 뒀습니다
4. **목록 한 줄은 `{id, sport_code, duration_ms, created_at, title, description}` 입니다.**
   저장 키·업로더는 안 옵니다(저장 키에 업로더 `user_id` 가 들어 있어서). 재생은
   아래 3조각으로 따로 받습니다

### 먼저 확인

```bash
# 공개로 돌린다
curl -s -X PATCH -H "Authorization: Bearer $T" -H 'Content-Type: application/json' \
  -d '{"is_public":true}' $API/videos/$VIDEO_ID | jq .is_public   # true

# 다른 계정 토큰으로 목록에 뜨는가
curl -s -H "Authorization: Bearer $OTHER_T" $API/videos/public | jq '.[].id'
```

### 3·4 조각 — 재생 주소와 제목·설명 (같은 날 이어서)

**제목·한 줄 설명**은 공개 여부와 같은 `PATCH /videos/{id}` 로 정합니다.

```json
{ "title": "우리 팀 첫 골", "description": "왼발 감아차기" }
```

- **셋(`is_public`·`title`·`description`) 중 보낸 것만 바뀝니다.** 공개 여부만
  토글할 때 제목이 지워지지 않습니다
- `title` 100자 · `description` 280자, 넘으면 `422`. **`null`·공백이면 지웁니다**
  (`tagline` 과 같은 규칙). 화면에서 미리 막아 주시는 편이 좋습니다
- `GET /videos`·`GET /videos/public` 응답에 `title`·`description` 이 실립니다

**재생 주소**는 클립마다 따로 받습니다 — `GET /videos/{id}/playback-url`.

```json
{ "url": "https://…s3….amazonaws.com/…?X-Amz-…", "expires_in": 900 }
```

- **공개 클립이면 남도**, 자기 클립이면 비공개여도 받습니다. 아니면 `404`
- `expires_in` 초 뒤 만료됩니다 — **캐시하지 말고 재생 직전에** 받으세요
- `MyVideos.tsx` 의 `previewSrc` 가 이 `url` 을 반환하도록 바꾸시면 됩니다.
  `lib/published.ts` 도 목록 id 로 이 엔드포인트를 부르면 재생이 붙습니다

```bash
curl -s -H "Authorization: Bearer $OTHER_T" $API/videos/$PUB_ID/playback-url | jq .url
```

---

## 21. 🟡 클립을 지울 수 있습니다 (2026-09-08 추가)

미결 `jin` 24번 1조각. `DELETE /videos/{id}` — 자기 클립만, `204`.

- DB 행 + 판정·분석 작업 연쇄 + S3 객체까지 지웁니다.
- 남의/없는 클립은 `404 VIDEO_NOT_FOUND`.
- ⚠️ **S3 삭제는 아직 실서버에서 안 됩니다** — EC2 역할에 `s3:DeleteObject` 를
  붙이는 중입니다(미결 `jin` 24번). DB 에서는 지금도 사라지므로 목록에서는
  즉시 빠집니다.
- `/analysis` 를 저장 없이 벗어날 때 이걸 부르시면 됩니다(`beforeunload` /
  `navigator.sendBeacon`). 놓쳐도 서버 백스톱 스윕이 24시간 뒤 정리합니다.

### `video.kept` (같은 조각)

`GET /videos`·`POST /videos` 응답에 `kept: boolean` 이 실립니다. **지금은 항상
`true`** — `/analysis` 분석을 임시(`kept:false`)로 두고 "저장"에서 켜는 전환은
프론트가 `keep` 을 부를 준비가 되면 함께 켭니다. 그때까지는 무시하셔도 됩니다.

### 🔴 `POST /videos/upload-url` 에 `filename` 을 실어 주세요 (2026-09-08 추가, 필수)

미결 `jin` 24번. 저장 키를 사람이 알아볼 수 있게 지으려고 **원본 파일 이름**을
받습니다.

```json
{ "content_type": "video/mp4", "size_bytes": 52428800, "filename": file.name }
```

- `file.name` 을 그대로 실으시면 됩니다. 공백·한글·이모지·문장부호가 있어도
  서버가 슬러그화하니 안전합니다. **필수 필드** — 안 보내면 `422` 입니다.
- 응답 `storage_key` 는 이제 `videos/<uuid>/<닉네임>-<이름>-<시각>-<8자>.mp4`
  모양입니다. **뜯어보지 말고 `POST /videos` 에 그대로 넘기세요** — 앞부분
  `<uuid>` 로 소유를 대조합니다.
- `POST /videos` 에도 `filename` 을 실어 주시면(선택) `original_filename` 으로
  온전히 저장됩니다. `upload-url` 에서 이미 받으므로 급하지 않습니다.

---

## 22. 🟡 과금이 생겼습니다 — 크레딧·코치 연결이 API로 됩니다 (2026-09-08 추가)

미결 `paik` 13번(패킷 A)입니다.

| 엔드포인트 | 뜻 |
|---|---|
| `GET /credits` | 내 크레딧 잔량(`balance`)·이력(`history`) |
| `POST /admin/credits/adjustments` | 관리자 전용 수동 지급·조정 |
| `GET /coaches` · `GET /coaches/{id}` | 코치 목록·상세 |
| `POST /coaches/{id}/referrals` | 코치 연결 요청 기록 |

### 🔴 `market/coaches` 화면의 mock을 그대로 걷어낼 수 없습니다

`www/src/lib/market.ts`의 `Coach` 타입은 `tagline`·`pricePerSession`·`levels`·
`titles`·`report`(영상·장면)·`verified`·`reviews`·`lesson`을 갖지만, 부록 D의
`coach` 테이블은 **`id`·`name`·`contact` 셋뿐**입니다. API가 주는 값은 이 셋
뿐이라, 화면의 나머지 필드는 **당분간 계속 mock으로 둬야 합니다** — 지우지
마십시오.

`sport`(종목)도 같은 이유로 없습니다. 패킷 A 문서의 「종목 코드가 다릅니다」
경고(`football` vs `soccer`)를 보고 확인했는데, 지금 스키마엔 애초에 종목
컬럼이 없어 **이번엔 해당하는 변환이 없습니다.** 종목별로 코치를 거르는 화면을
실제 데이터로 채우려면 `coach`에 종목 컬럼을 추가하는 **부록 D 변경이 먼저**
필요합니다 — 혼자 정하지 않고 미결 항목(`paik` 구역)으로 올려 뒀습니다.

### 크레딧은 자동으로 쌓이지 않습니다

가입 보너스·분석당 차감 같은 자동 지급/차감은 아직 없습니다(정책 미정).
`POST /admin/credits/adjustments`로 **관리자가 수동으로만** 조정합니다 — `/credits`
화면을 미리 만드셔도 됩니다만 지금은 값이 항상 `{"balance": 0, "history": []}`로
비어 있을 것입니다.

### 먼저 확인

```bash
git -C fastapi log --oneline main -- app/billing   # main에 배선됐는지
```

상세: `fastapi/docs/api-contract.md` **3-10절** · `fastapi/docs/backend-work-split.md` 「패킷 A」

---

## 23. 🟡 관리자 영상 목록·삭제가 생겼습니다 (2026-09-08 추가)

미결 `jin` 24번 6조각. **관리자 웹**(`www/src/app/admin/`)용입니다 — Flutter 는
해당 없음. 🔴 **"문제 영상"을 일일히 사람이 관리하는 최종 설계는 아닙니다**
(2026-09-08 사용자 확인) — 지금은 사람이 확인·삭제할 수 있게 열어 둔 임시 경로이고,
자동/에이전트 정리는 나중 과제입니다. 읽을 수 있는 S3 키(21번 `filename`)와
자동 스윕이 원래 방향입니다.

| 엔드포인트 | 뜻 |
|---|---|
| `GET /admin/videos?user=<uid\|email>` | 그 사람의 영상 **전부**(임시 `kept:false` 포함), 최근순 |
| `DELETE /admin/videos/{id}` | 아무 영상이나 삭제(소유 검사 없음) — DB 연쇄 + S3 best-effort |

- `?user=` 는 **필수**입니다. `user.id`(UUID) 또는 이메일(대소문자 무시) 중 하나.
  없는 사람이면 `404 USER_NOT_FOUND`.
- 목록 한 줄: `id`·`sport_code`·`original_filename`·`storage_key`·`created_at`·
  `kept`·`is_public`·`passed`·`reject_reason`·`analysis_status`·`report_prefix`.
  응답 최상위에 그 사람의 **현재** `nickname`·`email` 이 옵니다(닉네임을 바꿔도
  DB 조인이라 따라갑니다 — 저장 키에 얼어붙은 글자와 다릅니다).
- **재생·리포트 링크는 목록에 안 실립니다.** 객체마다 사전 서명하지 않으려는
  것이라, `storage_key`(재생)와 `report_prefix` 아래
  `report.json`·`impact.jpg`·`tracked.webm`(리포트)를 콘솔이나 별도 사전 서명으로
  짚으시면 됩니다.
- 같은 관리자 게이트(`ADMIN_EMAILS` 화이트리스트, `403 FORBIDDEN`)입니다.
- ⚠️ 21번과 같은 이유로 **S3 삭제는 아직 실서버에서 안 됩니다**(EC2 역할에
  `s3:DeleteObject` 미부착). DB 에서는 즉시 사라집니다.

### 먼저 확인

```bash
git -C fastapi grep -n "admin/videos" -- app/main.py app/analysis   # 라우트가 배선됐는지
```

상세: `fastapi/docs/api-contract.md` **3-2절**

---

## 24. 🟡 "내 프로필에 리포트 저장" 이 서버에 붙었습니다 (2026-09-08 추가)

미결 `jin` 24번 2조각. `POST /videos/{id}/keep` — `/analysis` 의 분석 결과를
"내 프로필에 리포트 저장" 할 때 부릅니다.

- `200 OK`, 응답은 `GET /videos` 한 줄과 같은 모양. `kept: true` 가 실려 옵니다.
- 서버가 **임시 원본을 `videos/…` 에서 `reports/<user_id>/<video_id>/source.<ext>`
  로 옮깁니다.** 옮긴 뒤 `storage_key` 가 바뀌므로, 저장 직후 재생·목록은
  응답의 새 `storage_key` 를 쓰세요(옛 키로 `playback-url` 을 부르면 404 는
  아니지만 없는 객체를 가리킵니다).
- **멱등** — 이미 저장된 클립에 다시 불러도 `200`.
- 남의/없는 클립은 `404 VIDEO_NOT_FOUND`.

### 아직 안 켜진 것 — 임시-저장 전환 (5조각)

지금은 `POST /videos` 로 등록되는 **모든** 클립이 `kept: true` 로 시작합니다
(동작 보존). `/analysis` 업로드를 임시(`kept: false`)로 두고 `keep` 을 눌러야
프로필에 남는 전환은, **프론트가 아래 둘을 다 갖추면** 함께 켭니다.

1. `/analysis` "저장" 버튼이 `POST /videos/{id}/keep` 호출
2. `/analysis` 를 저장 없이 벗어날 때 `DELETE /videos/{id}` 호출
   (`beforeunload` / `sendBeacon`)

그 전에 서버에서 켜면 저장 안 한 `/analysis` 업로드가 프로필에서 사라지므로,
**프론트 준비가 됐다고 알려 주시면** 서버 쪽을 켜겠습니다.

### 먼저 확인

```bash
git -C fastapi grep -n "videos/{video_id}/keep" -- app/analysis   # 라우트가 배선됐는지
```

상세: `fastapi/docs/api-contract.md` **3-6절**

---

## 25. 🟢 홈 스쿼드 판의 배치를 서버에 저장할 수 있습니다 (2026-09-09 추가, 미결 `paik` 9번)

판 크기·카드가 선 칸·손으로 정한 포지션이 지금은 그 브라우저의 `localStorage`
에만 있어 **다른 기기에서는 처음 판으로 열립니다.** 세 값을 담을 자리를
`squad`·`squad_member` 에 넣었습니다.

### 만족해야 할 성질

- 다른 기기(또는 다른 브라우저)로 로그인해도 **같은 판이 열린다.**
  `www/src/lib/squadBoard.ts` 가 `localStorage` 대신 API 를 쓴다.
- 판을 되살리는 데 필요한 세 값이 서버에 남는다:
  - **판 크기** — `SquadResponse.formation` (`"3:3"`·`"5:5"`·`"7:7"`, 안 정했으면 `null`).
    저장: `PATCH /api/v1/teams/{team_id}/squad` `{ "formation": "5:5" }`
  - **칸** — `SquadMemberResponse.grid_col` · `grid_row` (판에 안 올렸으면 `null`).
    저장: 등재할 때 `POST .../squad/members` 에 실어도 되고, 나중에
    `PATCH /api/v1/teams/{team_id}/squad/members/{member_id}` 로 옮겨도 된다.
  - **포지션** — 이미 있던 `position_code`. 같은 `PATCH .../members/{member_id}` 로 바꾼다
    (전에는 빼고 다시 넣어야 했습니다 — 계약 3-7 「아직 없는 것」 해소).
- 세 엔드포인트 모두 **바뀐 스쿼드 전체**를 돌려준다 — 화면이 판을 다시 그리면 된다.

### 🔴 하지 말아야 할 것

- **칸을 화면 픽셀로 보내지 마세요** — 격자 번호입니다(지금 **열 0\~2 · 행 0\~3**,
  행이 포지션 라인: 0 FW · 1 MF · 2 DF · 3 GK). `0~15` 밖이면 422.
- `grid_col`·`grid_row` 는 **함께 보내거나 함께 비웁니다**(한쪽만 = 422). 둘 다
  `null` = 등재는 남기고 판에서만 뺌.
- 포지션을 칸에서 역산하지 마세요 — 손으로 정한 값이라 자리와 다를 수 있습니다.
- 관리(저장·이동)는 **주장만**. 아니면 403.

### 먼저 확인

```bash
git -C fastapi grep -n "squad_member.grid_col\|def set_formation\|def update_member" -- app
grep -n "localStorage" www/src/lib/squadBoard.ts   # 안 걸리면 갈아 끼운 것
```

상세: `fastapi/docs/api-contract.md` **3-7절** (「홈 판 격자」 · 새 PATCH 둘)

---

## 26. 🟢 「이 사람으로 분석」 박스를 `POST /videos` 에 실을 수 있습니다 (2026-09-09 추가, 미결 `paik` 6번)

분석 화면이 「이 사람으로 분석」에서 받은 박스를 보낼 자리가 없었습니다.
`POST /api/v1/videos` 본문에 두 필드를 더했습니다.

### 만족해야 할 성질

- `www/src/lib/uploadClip.ts` 가 등록할 때 `subject_box`·`subject_at_ms` 를 함께 보낸다.
  - `subject_box`: `[x, y, w, h]` — **정규화 0~1**. 🔴 손으로 그린 네모가 아니라
    「예」를 누른 순간 **추적기가 잡고 있는 박스**(항목에 적힌 대로).
  - `subject_at_ms`: 그 박스를 그린 영상 시각(ms).
- 이 값은 `analysis_job` 에 저장되고 워커의 claim 응답으로 흘러갑니다 —
  화면이 더 할 일은 없습니다(응답에는 안 실립니다).

### 🔴 하지 말아야 할 것

- **화면 픽셀을 보내지 마세요** — `[0,1]` 밖이면 422. (조용히 클램프하지 않습니다.)
- `subject_box` 와 `subject_at_ms` 는 **함께 보내거나 함께 생략**합니다(한쪽만 = 422).
- **지정이 없을 때 억지로 채우지 마세요** — 생략하면 「자동으로 고르기」이고
  그게 정식 경로입니다. 지정 없음을 실패로 만들지 않습니다.
- 기하: `w·h > 0`, `x+w ≤ 1`, `y+h ≤ 1`, `subject_at_ms ≤ duration_ms`.

### 먼저 확인

```bash
grep -n "subject_box" www/src/lib/uploadClip.ts        # 화면 쪽이 실었는지
git -C fastapi grep -n "subject_box" -- app/analysis    # 백엔드 쪽(이미 됨)
```

⚠️ 트랙이 도중에 다른 사람으로 갈아타는 문제(정상호 님 실측: 63%)는 이 항목이
고치지 못합니다 — 화면 몫은 **닻을 최대한 좋은 것으로 주는 것**까지입니다.

상세: `fastapi/docs/api-contract.md` **3-6절** (`POST /videos`) · **3-8절** (claim 응답)

---

## 27. 🟢 「나를 보여주는 대표 영상」 — 세우기·남의 것 읽기 (2026-09-09 추가, 미결 `paik` 10번)

대표 영상이 지금은 브라우저 `localStorage` 에만 있어 **남의 것은 자리 표시
클립 그대로**입니다. 서버에 자리를 만들었습니다.

### 만족해야 할 성질

- **세우기** — `PATCH /api/v1/videos/{video_id}` 에 `{"is_featured": true}`.
  응답(`GET /videos` 한 줄과 같은 모양)에 `is_featured` 가 실려 옵니다.
  🔴 **사람당 하나** — 새로 세우면 옛 대표는 서버가 자동으로 내립니다. 내리려면
  `{"is_featured": false}`.
- **남의 것 읽기** — `GET /api/v1/cards/{card_public_slug}/featured-video`
  (로그인 필요). `{ video_id, url, expires_in, sport_code, duration_ms }` 를 줍니다.
  `url` 은 **사전 서명 GET URL**(만료됨 — `videoId` 로 다시 물어보세요, 5번과 같음).
  대표가 없으면 `404 NO_FEATURED_VIDEO`.
- `www/src/lib/featuredClip.ts` 가 `localStorage` 대신 이 둘을 씁니다 — 부르는
  쪽(`MyVideos` · `SquadSuggest`)은 함수 시그니처만 알면 됩니다.

### 🔴 하지 말아야 할 것

- **대표를 여러 개 만들려 하지 마세요** — 서버가 하나만 남깁니다(부분 유일 인덱스).
- **반려된 클립(`passed: false`)을 대표로 세우지 마세요** → `422 CANNOT_FEATURE`.
- 읽기는 **카드 슬러그**로 합니다 — 내부 `user_id` 가 아닙니다(카드와 같은 원칙).
- 저장 키를 그대로 `<video src>` 에 넣지 마세요 — `url`(사전 서명)을 씁니다.

### 먼저 확인

```bash
grep -n "localStorage" www/src/lib/featuredClip.ts       # 안 걸리면 갈아 끼운 것
git -C fastapi grep -n "is_featured\|featured-video" -- app/analysis   # 백엔드(됨)
```

⚠️ 추천 판 후보의 자리 표시 클립(`/coach-c00N.mp4`)은 그대로 두세요 — **영상
파일을 더 넣지 마세요**(셋이 이미 16MB). 실제 후보에 카드 슬러그가 붙는 시점에
이 경로로 갈아 끼우면 됩니다.

상세: `fastapi/docs/api-contract.md` **3-6절** (`PATCH /videos` · `GET /cards/{slug}/featured-video`)

---

## 28. 🟢 포지션 목록 API — 하드코딩 걷어낼 수 있습니다 (2026-09-09 추가)

`GET /api/v1/positions?sport_code=` (로그인 필요) 가 종목별 포지션
(`[{sport_code, code, label}]`, `sport_code` 순) 을 줍니다. 지금 아래 셋이 각자
`football: GK DF MF FW …` 를 하드코딩하고 있어 마이그레이션이 바뀌면 조용히
낡습니다 — 이걸로 갈아 끼우면 됩니다.

| 지금 하드코딩하는 곳 | 갈아 끼울 것 |
|---|---|
| `www/src/app/api/chat/route.ts` 시스템 프롬프트의 포지션 목록 (min 7 흐름 B) | 대화 시작 시 `GET /positions?sport_code={팀 종목}` 한 번 불러 넣기 |
| 스쿼드 등재 UI (`SquadPanel` 류) 의 포지션 드롭다운 | 같은 호출 |
| 모집 등록 UI 의 `needs[]` 포지션 선택 | 같은 호출 |

### 🔴 하지 말아야 할 것

- 없는 `sport_code` 로 부르면 빈 배열이 아니라 `422 UNKNOWN_SPORT` 입니다 —
  `GET /matches` 와 같습니다.
- `code` 는 **종목 안에서만** 유일합니다. 전 종목을 받으면 야구 `C`·농구 `C` 가
  둘 다 옵니다 — `sport_code` 로 구분하세요.

### 먼저 확인

```bash
git -C fastapi grep -n "positions_router\|/positions" -- app
grep -rn "GK.*DF.*MF.*FW\|골키퍼.*수비수" www/src   # 하드코딩이 남았는지
```

상세: `fastapi/docs/api-contract.md` **3-3절** (`GET /positions`)

---

## 29. 🟢 「집중해서 볼 항목」(focus)을 `POST /videos` 에 실을 수 있습니다 (2026-09-09 추가, 미결 `paik` 8번)

분석 화면의 `www/src/lib/rubricFocus.ts` 가 고른 항목을 보낼 자리가 없었습니다.
`POST /api/v1/videos` 본문에 `focus` 를 더했습니다 (`subject_box` 와 같은 축 —
`analysis_job` 에 저장 → claim 응답 → 워커 `--focus`).

### 만족해야 할 성질

- `www/src/lib/uploadClip.ts` 가 등록할 때 `focus` 를 함께 보낸다 — 루브릭의
  `criteria[].id` 목록(예: `["follow_through", "guide_hand"]`).
- 이 값은 저장돼 워커까지 흘러갑니다. 응답에는 안 실립니다.

### 🔴 하지 말아야 할 것

- **빈 목록·생략을 실패로 만들지 마세요** — 「전체적으로」가 기본이자 가장 흔한
  경우입니다. `focus: []` 든 아예 생략이든 `201` 입니다.
- **한글 항목 이름을 보내지 마세요** — `criteria[].id`(예: `follow_through`)입니다.
  `팔로스루` 같은 표시 이름이 아닙니다. 서버는 실재 여부를 못 봅니다(루브릭은 `agent/`).
- 항목 40자·목록 24개 상한. 서버가 공백·중복은 정리하지만 형식만입니다.

### 먼저 확인

```bash
grep -n "focus" www/src/lib/uploadClip.ts        # 화면 쪽이 실었는지
git -C fastapi grep -n "focus" -- app/analysis    # 백엔드 쪽(이미 됨)
```

상세: `fastapi/docs/api-contract.md` **3-6절** (`POST /videos`) · **3-8절** (claim 응답)

---

## 30. ✅ 용병 후보 검색 신설 — 배선·배포 끝났습니다 (2026-09-10 추가·정정, 박민호, pending `min` 17번)

처음 낼 때는 "아직 호출 불가(배선 전)"이라고 적었는데, **이후 같은 날 배선까지
마쳤습니다 — 앞서 드린 안내를 정정합니다.** `app/main.py`에 `mercenary_router`가
등록됐고, 배포 서버 `GEMINI_API_KEY`도 넣어 재시작·확인까지 끝났습니다(로컬
코드 기준 — 이 브랜치가 `main`에 병합·배포되기 전까지 실제 배포 서버는 아직
이 라우터를 서빙하지 않습니다).

`GET`·`PATCH /api/v1/me/mercenary-profile`(내 용병 프로필) ·
`POST /api/v1/matching/search-candidates`(후보 검색, 자연어 → 서버가 임베딩
계산 → pgvector 코사인 유사도) 가 추가됩니다.

🔴 **SFR-006·007(적합도·추천)과는 별개입니다** — 그걸 대신하지 않습니다. 자세한
구분은 상세 링크의 표 참고.

### www 쪽 연동도 이미 했습니다

`www/src/components/MatchBot.tsx`(pending `min` 7번, 흐름 B)가 흐름 D로
`search_candidates` 도구를 갖게 됐고, `www/src/app/api/chat/route.ts`가 이
검색 API를 부른 뒤 결과를 다시 Gemini에 넣어 소개 문장으로 엮습니다(RAG의
검색+생성). 코드·테스트는 이미 브랜치에 있고, 이 브랜치가 배포되면 바로
동작합니다.

### 먼저 확인

```bash
git -C fastapi grep -n "mercenary_router" -- app/main.py   # 있어야 정상
curl -s -o /dev/null -w '%{http_code}\n' https://<API 호스트>/api/v1/me/mercenary-profile
```

상세: `fastapi/docs/api-contract.md` **3-11절**

---

## 31. 🟢 분석 리포트 조회 API — 하드코딩 `REPORT` 를 걷어낼 수 있습니다 (2026-09-10 추가, 미결 `jin` 27번 · `paik` 7번)

분석이 끝나면 워커의 `report.json` 이 DB 에 적재되고, 화면은 그 리포트를 API 로
읽습니다. 지금 `www/src/components/analysis/AnalysisStage.tsx` 안에 리포트 객체가
하드코딩돼 있다면 이 API 호출로 바꿀 수 있습니다.

### 만족해야 할 성질

- 분석 리포트 화면이 **서버에서 받은 값**을 그린다. 특징 문장(`summary`)·항목별
  근거(`breakdown[]` 의 `name`·`grade`·`title`·`evidence`)·본 장면(`scenes[]`)이
  하드코딩이 아니다.
- 아직 적재 전이면(`404 REPORT_NOT_READY`) "분석 중" 같은 대기 상태를 보인다 —
  화면이 깨지지 않는다.

### API

`GET /api/v1/videos/{video_id}/report` (인증 필요, 자기 영상만)

| 상태 | 뜻 |
|---|---|
| `200` | 아래 형태의 리포트 |
| `404 VIDEO_NOT_FOUND` | 없는 영상이거나 남의 영상 |
| `404 REPORT_NOT_READY` | 영상은 있으나 아직 리포트가 적재 전 |

```json
{
  "video_id": "3f1c...", "analyzed_at": "2026-09-10T12:00:00Z",
  "summary": "디딤발 무릎 굽히기가 강점입니다.", "provisional": true,
  "breakdown": [
    { "criterion_id": "plant_knee_flexion", "name": "디딤발 무릎 굽히기",
      "grade": 2, "title": "흔들리지 않는 축", "evidence": "안정적으로 놓였습니다.",
      "metric_ref": "plant_knee_angle_at_impact", "skipped": false }
  ],
  "scenes": [ { "metric_code": "impact_frame", "label": "임팩트 프레임", "at_seconds": 2.07 } ],
  "previews": { "impact": "s3://.../impact.png" },
  "keypoint_quality": { "known": true, "swing_side_valid_ratio": 0.9 }
}
```

### 🔴 하지 말아야 할 것

- **총점·별점·항목별 점수 숫자를 화면에서 지어내지 마세요** — 응답에 없습니다.
  `summary` 는 문장뿐이고(3장 4 — 리포트 본문에 수치 금지) 수치는 카드 경로가
  따로 줍니다. `grade` 는 0~2 등급이지 점수가 아닙니다.
- **`grade: null` 을 0 으로 그리지 마세요** — `skipped: true` 와 짝이고 "이 항목은
  평가 대상이 아니었다" 는 뜻입니다.
- `band`·`stat`·`weight` 를 기대하지 마세요 — 허용목록에서 뺐습니다(검수 전
  임계값 · 수치는 카드 경로).

### 먼저 확인

```bash
grep -n "REPORT\s*=\|/report" www/src/components/analysis/AnalysisStage.tsx
git -C fastapi grep -n "videos/{video_id}/report" -- app/analysis   # 백엔드 쪽(이미 됨)
```

상세: `fastapi/docs/api-contract.md` **3-1절** 「✅ 적재 경로(흐름 B)·읽기 엔드포인트」

---

## 32. ✅ 정정 — 31번의 「하지 말 것」 두 줄이 틀렸습니다. `GET /videos/{id}/report` 가 이제 총점·오버롤 등급·항목별 `stat` 도 줍니다 (2026-09-11 추가·반영 완료, `ho` 28번)

**앞서 31번에서 "총점·별점 숫자는 응답에 없다", "`band`·`stat`·`weight` 를
기대하지 마세요" 라고 전달한 것을 정정합니다.** `stat` 은 이제 나갑니다 —
`band`·`weight`·`contribution` 은 여전히 안 나갑니다.

31번을 이미 반영하셨다면(응답 파싱을 이미 만드셨다면) **필드를 더 읽기만 하면
됩니다** — 기존 필드는 그대로입니다.

### 만족해야 할 성질

- 오버롤(등급 A/B/C/D·총점 0~100)을 화면에 보여줄 수 있다. **영상 하나(=분석
  1회)의 값**이다 — "이 선수의 오버롤"이 아니라 "이 클립의 오버롤"이라고 씁니다.
- 레이더 차트를 그린다면 각 항목의 `stat`(0~100)을 축 값으로 쓴다. **`stat`이
  `null`인 항목은 축에서 뺍니다** — 0으로 그리면 "그 항목을 못했다"로 잘못
  읽힙니다(`skipped: true`인 항목이 그렇습니다).
- `total_score`·`overall_grade`가 `null`이면(리포트가 이 필드가 생기기 전에
  적재된 옛 것) 오버롤 표시를 건너뜁니다 — 문장·항목별 등급은 그대로 보여줄 수
  있습니다.

### 바뀐 응답 모양

```json
{
  "video_id": "3f1c...", "analyzed_at": "2026-09-10T12:00:00Z",
  "summary": "디딤발 무릎 굽히기가 강점입니다.", "provisional": true,
  "total_score": 71, "overall_grade": "B",
  "breakdown": [
    { "criterion_id": "plant_knee_flexion", "name": "디딤발 무릎 굽히기",
      "grade": 2, "title": "흔들리지 않는 축", "evidence": "안정적으로 놓였습니다.",
      "stat": 88.5, "metric_ref": "plant_knee_angle_at_impact", "skipped": false }
  ],
  "scenes": [ { "metric_code": "impact_frame", "label": "임팩트 프레임", "at_seconds": 2.07 } ],
  "previews": { "impact": "s3://.../impact.png" },
  "keypoint_quality": { "known": true, "swing_side_valid_ratio": 0.9 }
}
```

`total_score`·`overall_grade`·`breakdown[].stat` **셋만 추가**입니다. 나머지
필드 이름·모양은 31번 그대로입니다.

### 🔴 하지 말아야 할 것

- **`total_score`를 `stat` 값들의 평균으로 다시 계산하지 마세요** — 총점은
  등급의 가중합이고 `stat`과 무관합니다. 화면에 총점과 레이더를 나란히 둘 때
  "축 점수 평균이 총점"으로 읽히지 않게 캡션을 답니다.
- **`overall_grade`를 카드(`player_card`, 스쿼드 화면 등)에 올리지 마세요** —
  부록 D.5가 막은 결정입니다. 이 등급은 **리포트 화면 전용**입니다.
  `GET /cards/*` 계열 응답에는 이 필드가 없습니다.
- 여전히 `band`·`weight`·`contribution`·`out_of_band`·`view_dependent` 는
  기대하지 마세요 — 개발 확인용이고 허용목록 밖입니다.
- 근거 문장(`evidence`)에서 등급·점수를 정규식으로 뽑지 마세요 — 문장에는
  숫자가 없습니다(그대로 유효, 23·24번).

### 먼저 확인

```bash
git -C fastapi diff a1c9f7b2e034 8a765b42e48e -- app/analysis/adapter/inbound/api/schemas/video_schema.py
```

위가 안 걸리면(즉 이미 병합돼 있으면) 서버가 이미 이 필드들을 내고 있는
것입니다 — `curl` 로 실제 응답을 보고 파싱만 늘리면 됩니다.

상세: `fastapi/docs/api-contract.md` **3-1절** · 같은 구역 31번(원래 계약) ·
pending `ho` 28번

**✅ 반영 완료 (2026-09-11)** — `www/src/server/backend/types.ts`(타입)·
`src/lib/savedReports.ts`(옮김터)·`src/components/analysis/ReportView.tsx`
(등급 칩·SVG 레이더)에 넣었다. 차트 라이브러리는 새로 안 넣었다. `npm test`
571 passed.

---

## 33. 🔴 정정 — 업로드 해상도 상한이 1080p 가 아니라 4K 입니다 (2026-09-11 추가)

**앞서(계약 문서·CCC 4번 등에서) "해상도 상한 1920x1080"이라고 전달했던 것을
정정합니다.** `POST /videos`(`analyze: true`)의 해상도 반려 기준이 4K(긴 변
3840 · 짧은 변 2160, 방향 무관)로 올라갔습니다 — `ho` 9번이 2026-09-08에 이미
메모리로 안전하다고 확정했는데 이 상한만 안 풀려 있던 것을 사용자가 발견했습니다.

### 만족해야 할 성질

- 화면·안내 문구 어디선가 "1080p까지만 지원", "해상도가 너무 높습니다(1920x1080
  이하로)" 같은 문구를 **하드코딩**했다면 4K 기준으로 고칩니다. `grep -rn "1920\|1080"
  www/src`로 찾아본 결과 지금은 그런 문구가 없는 것 같습니다 — 서버 `reject_reason`
  문장을 그대로 보여주는 구조라면 손댈 것이 없을 수 있습니다.
- 업로드 전 클라이언트 쪽 사전 검증(있다면)도 같은 기준으로 맞춥니다.

### 곁가지 — 4K 와 무관한 별개 버그도 같이 풀렸습니다

옛 상한이 `width`·`height`를 그대로 비교해서, **세로로 찍은 보통 1080p 영상
(1080×1920, 스마트폰 기본 방향)도 방향 때문에 반려되고 있었습니다.** 이제 방향
무관하게 통과합니다 — 세로 영상 업로드가 갑자기 되기 시작했다면 이게 이유입니다.

### 하지 말아야 할 것

- 🔴 **60초 길이 상한은 그대로입니다** — 이건 별개 미해결 항목(에이전트 프레임
  상한과 안 맞음, `agent/`)이라 이번 정정과 무관합니다.

### 먼저 확인

```bash
git -C fastapi log --oneline -1 -- app/analysis/domain/rules/video_rules.py
grep -rn "1920\|1080" www/src --include="*.ts" --include="*.tsx"
```

상세: `fastapi/docs/api-contract.md` 3-6절 · pending `## ho` 9번

---

## 34. ✅ `GET /videos/{id}/report` 에 새 에러 코드 `ANALYSIS_FAILED` — 이미 반영 완료 (2026-09-11 추가)

**사용자가 화면에서 직접 겪은 버그.** 분석이 `failed`로 끝나도 이 엔드포인트가
`REPORT_NOT_READY`만 내서, "다시 확인"을 눌러도 영원히 "아직 분석이 끝나지
않았습니다"만 보였습니다 — 실패는 다시 물어봐도 절대 안 바뀌는데 곧 될 것처럼
보인 것이 문제였습니다.

### 바뀐 것

| 코드 | 뜻 | 다시 물어보면 |
|---|---|---|
| `REPORT_NOT_READY` | 아직 `queued`·`running` | 바뀔 수 있다 |
| `ANALYSIS_FAILED` (신설) | `failed`로 끝남, `message`에 실패 사유 | **절대 안 바뀐다** |

### ✅ 반영 완료

`www/src/lib/savedReports.ts`(`ReportResult`에 `{state:'failed', reason}` 추가)·
`AnalysisStage.tsx`·`MyVideos.tsx`(실패 사유 표시, "다시 확인" 버튼 숨김)·
`mock.ts`까지 이미 넣었습니다(`2206bb6`). `npm test` 576 passed.

상세: `fastapi/docs/api-contract.md` 3-1절 · 같은 구역 31번(원래 계약)

---

## 35. ✅ 카드 꾸미기가 서버에 저장됩니다 — `style` 신설, `text`는 `tagline`과 합쳤습니다 — 이미 반영 완료 (2026-09-11 추가, 미결 `paik` 3번 나머지)

**사용자가 화면에서 직접 겪은 문제.** 카드 편집기(`CardEditor.tsx`)에서 바탕 ·
로고 · 글자 · 글자 색을 바꾸고 「저장」을 눌러도 **이 브라우저에만**
(`localStorage`) 담겨서, 다른 기기에서 안 보이고 **공개 카드 링크(`/c/{slug}`)
에도 안 실렸습니다. 이번엔 `www/`까지 같이 고쳤습니다(남의 영역이라
`www/AGENTS.md` 먼저 읽었습니다).

### 바뀐 것

```json
PATCH /me/card
{
  "tagline": "THREE LUNGS",
  "style": {
    "bg": "#91ea92", "logo": "#0b0b0b", "text_color": "#0b0b0b",
    "text_x": 50, "text_y": 34, "brush": 0, "brush_color": "#0b0b0b",
    "brush_scale": 1, "brush_x": 0, "brush_y": 0
  }
}
```

`GET /me/card`·`GET /cards/{slug}` 양쪽 응답에 `style`(안 꾸몄으면 `null`)이
실립니다. `tagline`과 **따로** 바뀝니다(`model_fields_set`) — `style`만
보내도 `tagline`은 그대로고 반대도 마찬가지입니다. 값이 하나라도 모자라거나
색이 `#rrggbb` 형식이 아니면 `422`입니다 — 부분 병합을 하지 않으므로 화면은
늘 들고 있는 **전체 값**을 보냅니다.

### 🔴 `style.text`는 없습니다 — `tagline`과 합쳤습니다

**이미 18번에서 낸 `tagline`이 같은 것이었습니다.** `cardStyle.tsx`의
`DEFAULT_CARD_STYLE.text` 기본값(`"THREE LUNGS"`)이 18번 예시와 같은 문구인
것이 그 증거입니다 — `www`가 04-09 이후 `tagline`을 모른 채 같은 개념을
`style.text`로 새로 만들었던 것으로 보입니다. 합쳤습니다: 편집기의 "글자"
입력란은 이제 `tagline`을 바꾸고(20자 상한, 서버와 같습니다), `PlayerCardView`
의 가운데 큰 글자도 `card.tagline`을 읽습니다.

### 여기 없는 것 — `style.photo`·`photoScale`·`photoX`·`photoY`·`mode`

사진 자체와 그에 딸린 자리 · 크기 · 모드는 여전히 서버에 없습니다.
`og_image_key`가 "규칙은 있는데 파일이 없는" 상태인 것과 같은 이유입니다
(18번 「사진은 아직입니다」). 이 다섯은 지금처럼 브라우저에만, **이 세션
동안만** 남습니다 — 서버로 보내면 `422`입니다(`CardStyleSchema`가
`extra="forbid"`).

### ✅ 반영 완료

`www/src/app/(app)/me/cardStyle.tsx`(서버 값으로 초기화, `save()`가
`PATCH /me/card`를 부름) · `CardEditor.tsx`("글자" 입력란이 `tagline`을
바꿈, 20자 상한) · `StyledCard.tsx`(편집 중 미리보기) · `PlayerCardView.tsx`
(`look`을 안 받아도 `card.style`·`card.tagline`을 스스로 읽어 그림 — 편집
중이 아닐 때도, 공개 카드 화면도 손댈 것 없이 자동으로 꾸며진 대로 그려집니다)
· `server/backend/{types,gateway,fastapiBackend,mock}.ts` · `api/me/card/route.ts`
(PATCH 신설)까지 이미 넣었습니다. `cardStyleStore.ts`(옛 `localStorage` 저장소)
는 지웠습니다 — 그 파일 자신의 주석이 예고했던 그대로입니다.

`npx tsc --noEmit`·`npx eslint`(둘 다 무관한 기존 항목 외 없음) ·
`npx vitest run` 574 passed(1 skipped, 무관) · `pytest -q` 776 passed.

### 먼저 확인

```bash
curl -s -X PATCH -H "Authorization: Bearer $T" -H 'Content-Type: application/json' \
  -d '{"style":{"bg":"#91ea92","logo":"#0b0b0b","text_color":"#0b0b0b","text_x":50,"text_y":34,"brush":0,"brush_color":"#0b0b0b","brush_scale":1,"brush_x":0,"brush_y":0}}' \
  $API/me/card | jq .style
```

상세: `fastapi/docs/api-contract.md` 3절(선수 카드) · 같은 구역 18번(`tagline`,
같은 계열) · `fastapi/alembic/versions/20260911_player_card_style.py`
---

## 36. 🔴 분석에 실패한 영상이 DB·S3 에 안 남습니다 — `kept` 기본값 정정, `POST /videos/{id}/keep` 필수로 바뀝니다 (2026-09-11 추가)

**사용자가 화면에서 직접 겪은 문제** — 분석에 실패한 클립이 프로필의 「업로드
영상」에 계속 남아 있었습니다. 원인은 미결 `jin` 24번 5조각이 안 켜져 있던
것이었습니다: 문서(`api-contract.md`)는 "작업이 생긴 클립은 임시(`kept:false`)
로 시작한다"고 이미 적혀 있었는데, **실제 등록 코드는 늘 `kept:true` 로
등록해서** 어떤 클립도(성공·실패·저장 여부와 무관하게) `DELETE /videos/{id}`
로 지워지지 않는 한 24시간 백스톱에도 안 걸리고 영영 안 지워졌습니다.

### 바뀐 것

`POST /videos` 응답의 `kept` 기본값이 바뀝니다.

| 클립 | 이전 | 지금 |
|---|---|---|
| `analyze: false`(기록용 업로드) | `true` | `true`(안 바뀜) |
| 반려(작업 자체가 안 생김) | `true` | `true`(안 바뀜) |
| 정상 등록, 작업이 생김 | `true` | **`false`** |

작업이 생긴 클립은 이제 **등록만으로는 `GET /videos`(본인 목록)·`GET
/videos/public`·`GET /cards/{slug}/featured-video` 등 어디에도 안 뜹니다.**
`POST /videos/{id}/keep` 을 불러야 뜹니다 — 이미 있던 엔드포인트라 새로 배울
것은 없고, **이제부터 실제로 안 부르면 안 됩니다.**

### 만족해야 할 성질

**분석 결과를 볼 생각이 있는 클립만 프로필에 영구로 남고, 나머지(특히 분석에
실패한 클립)는 사용자가 명시적으로 남기지 않는 한 결국 사라질 것.**

### 먼저 확인

```
grep -rn "videos/.*keep\|keepVideo" <클라이언트 소스>
```

안 걸리면 아직 `keep` 을 안 부르고 있는 것이고, 지금 바로 고쳐야 합니다 —
안 그러면 방금 분석을 마친 클립이 새로고침 한 번에 목록에서 사라집니다
(정상 동작입니다 — `keep` 을 안 불렀을 뿐입니다).

### ✅ `www` 는 이미 반영 완료

`www/src/components/analysis/AnalysisStage.tsx` 의 「내 프로필에 리포트 저장」
단추가 리포트 상태가 `ready` 일 때만 `POST /videos/{id}/keep` 을 부르도록
배선했습니다(`server/backend/{gateway,fastapiBackend,mock}.ts` ·
`api/videos/[id]/keep/route.ts` 신설). 분석이 실패·반려로 끝났으면 그 단추가
잠긴 채로 남고, 화면을 벗어나면 곧(또는 늦어도 24시간 뒤 백스톱으로) 지워집니다.

### 🔴 Flutter 는 아직입니다

같은 명령(`grep -rn "keep" flutter/lib`)으로 확인해 주세요. 안 걸리면 지금은
`/analysis` 화면에서 저장 없이 나가는 모든 클립이 결국 사라집니다 — 성공한
분석까지 포함해서입니다. 별도 항목으로 올릴지는 담당자 판단에 맡깁니다.

상세: `fastapi/docs/api-contract.md`(`POST /videos` · `POST /videos/{id}/keep`
절, "저장 안 한 임시 영상도 여기서 정리된다" 절) · 같은 구역 20번(공개·재생,
같은 `kept` 필터를 씀)

## 37. 지인 검색·상호 신청·폴링 알림이 새로 생겼습니다 (2026-09-15 추가, 미결 `jin` 35번)

`www/src/components/SquadFriends.tsx`의 "지인 찾기" 판이 지금 하드코딩 배열을
쓰고 있는 것을 확인했습니다("계약에 지인·친구 엔드포인트가 없다"는 그 파일
주석 그대로입니다). 백엔드에 실제 엔드포인트를 만들었습니다 — 계약 3-12절.

### 만족해야 할 성질

1. **지인 찾기 판이 실제 사용자를 닉네임으로 검색할 수 있을 것.**
2. **찾은 사람에게 "지인 신청"을 보낼 수 있고, 상대가 수락해야 지인이 될
   것** — 일방적으로 등록되는 게 아니라 **상호** 관계입니다(신청→수락).
3. **수락 대기 중인 신청·새 알림을 볼 수 있는 곳이 있을 것** — 알림은
   지금은 폴링(`GET /me/notifications`)뿐입니다, 실시간 아닙니다.

파일·컴포넌트 이름은 예시지 규격이 아닙니다 — 지켜야 하는 것은 위 성질뿐입니다.

### 먼저 확인

```
grep -n "FRIENDS = \[" www/src/components/SquadFriends.tsx
```

걸리면 아직 하드코딩 배열 그대로입니다.

### 새 엔드포인트 (계약 3-12절에 요청/응답 전체가 있습니다)

| 엔드포인트 | 용도 |
|---|---|
| `GET /users/search?q=` | 닉네임으로 사람 찾기(최대 20명, 본인 제외) |
| `POST /me/contacts` | 지인 신청(`target_user_id`, 선택적 `note`) |
| `POST /me/contacts/{id}/accept` | 내가 대상인 신청 수락 |
| `GET /me/contacts` | 수락된 지인 목록 |
| `GET /me/contacts/requests` | 나에게 온 대기중 신청 |
| `GET /me/notifications?unread_only=` | 알림 목록(폴링) |
| `PATCH /me/notifications/{id}/read` | 알림 읽음 처리 |

### 함께 바뀐 것 — `PATCH /me`

`is_nickname_searchable`(boolean, 선택) 필드가 늘었습니다 — 안 보내면 안
바뀝니다. 지인 검색에 내 닉네임이 노출될지를 사용자가 프로필에서 끌 수 있게
하는 스위치입니다(기본값 `true`). `GET /me` 응답에도 이 필드가 옵니다.

### 🔴 하지 말 것

- **닉네임 중복 처리를 프론트에서 미리 막으려 하지 마십시오.** `user.nickname`
  에 유일 제약이 새로 붙어서, 가입·닉네임 변경이 겹치면 서버가
  `409 NICKNAME_ALREADY_EXISTS`를 냅니다 — 그 코드로만 분기하십시오.
- **알림에 문구가 없습니다.** `type`(`contact_request`/`contact_accepted`)·
  `actor_user_id`·`subject_type`만 옵니다 — 문장은 화면에서 조립해야 합니다.
  서버가 문장을 보낼 거라고 가정하지 마십시오.
- 지인 목록 응답의 `note`는 **내가 신청자일 때만** 옵니다 — 상대 시점에서는
  항상 `null`입니다. 버그가 아닙니다.

### 아직 없는 것 — 이번 범위 밖

매칭 수락·팀 가입 성공 등 **다른 흐름에서 알림을 만드는 것**은 이번에 안
했습니다(알림 인프라 자체만 만들었습니다). 필요해지면 별도로 요청해 주십시오.
`flutter/`도 필요하면 같은 방식으로 반영해 주십시오.

상세: `fastapi/docs/api-contract.md`(3-12절) · 부록 D 도메인 ①
(`user_contact`·`notification`)

## 38. "자동으로 고르기"를 실제로 부를 수 있습니다 — `POST`/`GET /videos/{id}/detect` (2026-09-15 추가, 미결 `ho` 44번)

분석 걸기 전 화면(영상에서 분석할 사람을 드래그로 묶는 판)의 "자동으로
고르기" 버튼이 지금 실제 API를 부를 수 있게 됐습니다.

### 만족해야 할 성질

1. **"자동으로 고르기"를 누르면 검출을 요청할 수 있을 것.**
2. **결과가 바로 안 와도(폴링) 화면이 자연스러울 것** — GPU가 꺼져 있으면
   몇 초~몇 분 걸릴 수 있습니다. 지금 분석 진행 체크리스트가 이미 같은 방식
   (`GET /videos/{id}/report` 폴링)으로 도는 것과 같은 패턴입니다.
3. **검출된 사람이 0명이어도 실패로 보이지 않을 것** — 그럴 땐 지금 하시던
   대로 드래그로 넘어가면 됩니다.

### 먼저 확인

```
grep -n "자동으로 고르기" www/src/components/analysis/AnalysisStage.tsx
```
걸리면 그 버튼이 아직 아무 API도 안 부르는 상태인지 확인해 주십시오.

### 흐름

1. `POST /videos/{video_id}/detect` — `202` + `{job_id, status:"queued", ...}`
2. `GET /videos/{video_id}/detect`를 몇 초 간격으로 폴링 — `status`가
   `succeeded`가 될 때까지
3. `succeeded`면 `detection_result.people[].box`(정규화 `[x,y,w,h]`, 0~1)를
   후보로 보여주고, 사용자가 고르면 **그 값을 그대로** 기존 분석 요청의
   `subject_box`로 넘기면 됩니다 — 좌표 변환 없습니다

상세(요청/응답 전체 예시): `fastapi/docs/api-contract.md`의
`POST`/`GET /videos/{video_id}/detect` 절.

### 🔴 하지 말 것

- **검출 결과 0명을 오류로 다루지 마십시오.** `succeeded` + `people: []`가
  정상입니다 — 드래그 경로로 넘기면 됩니다.
- **`video_id`마다 검출 요청을 재사용하려 하지 마십시오.** 호출할 때마다
  새 작업이 생깁니다(분석 작업과 같은 정책) — `GET`은 항상 **가장 최근**
  것만 봅니다.
- 워커(정상호 영역) 배선은 아직입니다 — 실제로 검출이 도는지는 그쪽 작업이
  끝난 뒤에 확인 가능합니다. 지금은 API 형태만 붙이셔도 됩니다.

---

## 계약 문서

## 39. `GET /videos/public`에 업로더가 실립니다 (2026-09-15 추가, 미결 `paik` 16번)

공개 클립 목록이 **누가 올렸는지 안 줘서, 남의 공개 영상도 보는 사람 자기
닉네임으로 그려지던 버그**를 고쳤습니다(`HomeFeed.tsx`/`feed.ts`가 원인일
것 같다고 `paik` 16번에 적혀 있던 그 문제입니다).

### 만족해야 할 성질

1. **공개 영상 목록 한 줄에 그 영상을 올린 사람이 누군지 표시될 것.**
2. 카드를 만든 사람은 **눌러서 그 사람 카드로 갈 수 있을 것.**

### 새로 실리는 필드 (`GET /videos/public` 응답 각 행)

| 필드 | 값 |
|---|---|
| `uploader_nickname` | 항상 있습니다 — 그대로 표시하면 됩니다 |
| `uploader_card_slug` | 카드를 만든 사람만, 없으면 `null`. 있으면 `GET /cards/{slug}`로 링크 걸 수 있습니다 |

### 먼저 확인

```
grep -n "uploader_nickname" www/src/lib/feed.ts www/src/components/HomeFeed.tsx
```

걸리면 이미 반영된 것입니다.

### 🔴 하지 말 것

- **저장 키(`storage_key`)나 raw `user_id`는 여전히 안 옵니다** — 카드 링크는
  `uploader_card_slug`로만 거십시오.
- `uploader_card_slug`가 `null`일 때 링크를 안 그리는 것으로 충분합니다 —
  "카드 없음"을 별도로 안내할 필요는 없습니다(`paik` 16번 본문 참고).

상세: `fastapi/docs/api-contract.md`(공개 클립 목록 절)

---

## 40. 경기 조건·지역·"맞는 상대" 후보가 생겼습니다 (2026-09-15 추가, 미결 `paik` 18·19·20·21번)

`www/src/lib/matchPrefs.ts`(브라우저에만 저장)·`regions.ts`(60곳 하드코딩)·
`teamMatch.ts`(mock 후보 7팀)를 실제 서버 경로로 바꿀 수 있게 됐습니다.
`teamMatch.ts`의 `applyToTeam`(경기 신청)은 **이번 범위가 아닙니다** — `paik`
17번(팀↔팀 경기 신청·수락·알림)에서 따로 냅니다.

### 만족해야 할 성질

1. **지역 선택지가 서버 목록(60곳)에서 올 것** — 자유 입력 대신.
2. **팀 조건은 팀장만 정할 수 있고, 개인 조건과 안 섞일 것.**
3. **"맞는 상대" 후보 목록에 유사도 점수 대신 사실값 근거가 올 것** — 화면이
   `whyMatches()`로 직접 겹침을 계산할 필요가 없어집니다, 서버 응답의
   `reasons[].detail`을 그대로 보여주면 됩니다("토요일 11:00~12:00 겹침"처럼
   이미 문장입니다).

### 먼저 확인

```
grep -n "REGIONS: string\[\]" www/src/lib/regions.ts
grep -n "TEAMS: Omit<MatchTeam" www/src/lib/teamMatch.ts
```

걸리면 아직 하드코딩/mock 그대로입니다.

### 새 엔드포인트 (계약 3-13절)

| 엔드포인트 | 용도 |
|---|---|
| `GET /regions` | 지역 목록 |
| `PUT/GET /teams/{team_id}/match-preferences` | 팀 조건(팀장만 `PUT`) |
| `PUT/GET /me/match-preferences` | 내 조건(지역·시간·포지션) |
| `GET /teams/{team_id}/members/match-preferences` | 팀원 조건 열람(팀장만) |
| `GET /teams/{team_id}/match-candidates` | "맞는 상대" 후보(이미 정렬됨) |

### 🔴 하지 말 것

- **`whyMatches()`로 다시 계산하지 마십시오** — 서버가 이미 겹침·지역 계층을
  계산해서 `reasons`로 줍니다. 화면에서 다시 계산하면 서버와 다른 답이 나올
  수 있습니다.
- **`match-candidates` 응답에 점수·유사도가 없다고 당황하지 마십시오** — 의도된
  것입니다. 순서는 이미 서버가 정렬했습니다(`reasons`가 근거).
- 시작 시각이 끝 시각보다 늦은 슬롯을 보내면 `422 INVALID_TIME_SLOT`입니다 —
  화면에서 미리 막아 주십시오(사용자 경험상), 서버도 어차피 막습니다.
- 팀 조건 `PUT`은 **통째로 교체**입니다 — 기존 지역·시간에 하나만 추가하고
  싶어도 전체 목록을 다시 보내야 합니다.

상세: `fastapi/docs/api-contract.md`(3-13절) · 부록 D 도메인 ①·④

---

## 41. 선수·내 영상의 관절(skeleton)을 읽을 수 있습니다 (2026-09-15 추가, 미결 `paik` 29번)

「선수와 비교하기」가 지금 브라우저(MoveNet)로 직접 관절을 뽑고 있는 것을
서버 값으로 바꿀 수 있습니다 — 받는 자리가 한 곳(`www/src/lib/motion/
source.ts`)이라고 `paik` 29번에 적혀 있어서, 그 파일만 바꾸면 될 것입니다.

### 만족해야 할 성질

1. **선수 목록을 서버에서 받아올 수 있을 것** — 이름만입니다.
2. **선수·내 영상 양쪽의 관절 시계열을 같은 모양으로 받을 수 있을 것.**

### 🔴 이번 범위에서 안 한 것 — 재생 주소

선수 원본 영상은 S3에 없습니다(EC2 역할이 `videos/` 접두사에 쓰기 권한이
없어 못 올렸습니다). **화면은 계속 지금처럼 정적 파일(`www/public/
compare/`의 Pexels 클립)로 재생해 주십시오** — 서버가 재생 주소를 안
줍니다. 필요하면 별도로 요청해 주시면 됩니다.

### 새 엔드포인트 (계약 3-14절)

| 엔드포인트 | 용도 |
|---|---|
| `GET /reference-players` | 선수 목록(`id`·`name`만, `id`는 `AnalysisStage.tsx`의 `COMPARE` id와 같습니다) |
| `GET /reference-players/{player_id}/skeleton` | 그 선수의 관절 시계열 |
| `GET /videos/{video_id}/skeleton` | **내 영상만**의 관절 시계열 |

관절 응답 모양은 `agent/report-contract.md`의 `skeleton` 절과 완전히
같습니다(에이전트 값을 그대로 통과시킵니다) — `joints`(프레임당 COCO-17)·
`fps`·`moments`(before/impact/after)·`swing_leg` 등.

### 🔴 하지 말 것

- **못 잡은 프레임(`joints[i] === null`)을 배열에서 건너뛰지 마십시오** —
  인덱스가 곧 프레임 번호입니다. 건너뛰면 그다음 프레임이 다 한 칸씩
  밀립니다.
- **좌표를 0~1로 자르지 마십시오** — 화면 밖으로 나간 관절은 실제로 범위를
  벗어난 값입니다. 자르면 발이 가장자리에 붙어 있는 것처럼 그려집니다.
- `known: false` 응답(리포트는 있는데 관절 데이터가 없는 옛 리포트)을
  에러로 다루지 마십시오 — `200`입니다. `why` 문구만 있고 나머지 필드는
  없습니다.
- `GET /videos/{id}/skeleton`은 `GET /videos/{id}/report`와 같은 에러
  셋(`VIDEO_NOT_FOUND`·`ANALYSIS_FAILED`·`REPORT_NOT_READY`)을 씁니다 —
  이미 처리하고 계신 분기를 그대로 재사용하시면 됩니다.

상세: `fastapi/docs/api-contract.md`(3-14절) · 부록 D 도메인 ②(`reference_player`)

## 42. 팀↔팀 경기 신청·알림·수락이 생겼습니다 (2026-09-15 추가, 미결 `paik` 17번)

`www/src/lib/teamMatch.ts`의 `applyToTeam()`이 1.4초 뒤 `{accepted: true}`를
돌려주는 가짜였고, `lib/bookedMatches.ts`가 잡힌 경기를 브라우저에만 남기던
것을 실제 API로 바꿀 수 있습니다. 🔴 **기존 `POST /matches/{id}/applications`
(개인이 경기에 지원)와는 다른 새 엔드포인트입니다** — 이건 팀이 팀에게 겁니다.

### 만족해야 할 성질

1. **우리 팀이 상대 팀에 경기를 걸 수 있을 것.**
2. **그 사실이 상대 팀장에게 닿을 것** — 알림(`GET /me/notifications`,
   `jin` 35번)으로 옵니다.
3. **수락하면 양쪽 모두에게 확정된 경기 하나가 생길 것** — 기존
   `GET /teams/{id}/matches`에 그대로 뜹니다(새 목록 아님).

### 새 엔드포인트 (계약 3-15절에 요청/응답 전체가 있습니다)

| 엔드포인트 | 용도 |
|---|---|
| `POST /teams/{team_id}/match-requests` | 경기 걸기(대상 팀 id·시각·장소) |
| `GET /teams/{team_id}/match-requests` | 보낸 것 + 받은 것 목록 |
| `POST /teams/{team_id}/match-requests/{id}/accept` | 수락 → 확정 경기 생성 |
| `POST /teams/{team_id}/match-requests/{id}/reject` | 거절 |
| `DELETE /teams/{team_id}/match-requests/{id}` | 신청 팀이 스스로 무르기 |

### 먼저 확인

```
grep -n "applyToTeam" www/src/lib/teamMatch.ts
```

걸리면 아직 가짜 그대로입니다.

### 🔴 하지 말 것

- **한 팀이 여러 신청을 동시에 걸어도 됩니다**(막지 않습니다) — 다만
  **하나가 수락되면 그 팀의 다른 대기중 신청은 서버가 알아서
  `cancelled`로 정리합니다**(이중 예약 방지). 화면에서 따로 막을 필요
  없습니다 — 취소된 신청도 알림·목록 조회로 보입니다.
- **`GET /matches/{id}` 응답에 `opponent_team_id`가 새로 생겼습니다** —
  이 필드가 있으면 팀 대 팀 확정 경기라 **모집(`needs`)이 항상 빈
  배열**입니다. 기존 모집 경기와 같은 화면으로 그리면 빈 모집란이
  어색해 보일 수 있으니 구분해 주십시오.
- **경기 취소는 기존 `DELETE /matches/{id}`를 그대로 씁니다** — 새
  엔드포인트가 아닙니다. 다만 이제 **상대 팀 주장도** 취소할 수
  있습니다(전엔 주최 쪽만).
- 신청을 스스로 무르는 것(`DELETE .../match-requests/{id}`)은 알림이
  안 갑니다 — 자기 행동을 자기에게 알릴 이유가 없어서입니다. 버그가
  아닙니다.

상세: `fastapi/docs/api-contract.md`(3-15절) · 부록 D 도메인 ④
(`team_match_request`·`match.opponent_team_id`)

---

## 43. 남의 표시 등급(`S`~`F`)을 실제로 읽을 수 있습니다 (2026-09-16 추가, 미결 `paik` 25·26번)

`www/src/components/SquadSuggest.tsx`의 `SUGGESTIONS[].grade`와 `gradeOfPlayer()`가
mock이던 자리입니다. `www/src/lib/playerGrade.ts`가 이미 이 규칙을 문서화해
두었는데(2026-09-11, `GRADES = ['S','A','B','C','D','F']`), 지금까지는 부를 경로가
없어 **화면에 보이는 등급이 전부 지어낸 값**이었습니다. 이제 실제로 계산해 줍니다.

### 만족해야 할 성질

**AI 추천 후보(카드 슬러그가 있는 사람)의 표시 등급을 읽을 수 있을 것.**
`playerGrade.ts`의 눈금(`S`~`F` 여섯)과 그대로 맞습니다 — 경계 계산은 **서버가
다 했으니 화면에서 다시 계산하지 않습니다.**

### 새 엔드포인트

```
GET /api/v1/cards/{card_public_slug}/grade
→ { "grade": "S" | "A" | "B" | "C" | "D" | "F" | null, "provisional": bool | null }
```

로그인하면 누구나(`featured-video`와 같은 원칙). `grade`가 `null`이면 대표
영상이 없거나 아직 분석 전이라는 뜻입니다 — 이때는 `averageGrade()`가 이미
하듯 그 사람을 등급 계산에서 빼면 됩니다(0이나 `F`로 치지 않습니다).

### 먼저 확인

```
grep -n "gradeOfPlayer\|SUGGESTIONS" www/src/components/SquadSuggest.tsx
```

걸리면 아직 mock 그대로입니다 — 걸리는 함수째 지우고 위 엔드포인트로 바꾸면 됩니다.

### 🔴 하지 말 것

- **`provisional`이 `true`인 동안 등급 옆에 "검수 전"을 답니다.** 서버가 등급
  문자와 `provisional`을 같이 내려주는 이유가 이것입니다 — 등급만 떼어 쓰면
  검수 전 값인지 알 방법이 없어집니다(남의 화면에 박힌 등급은 나중에 회수가
  안 됩니다).
- **경계를 화면에서 다시 긋지 않습니다.** `S`·`F`가 어떻게 갈리는지는 서버
  계산이고, `playerGrade.ts`의 `GRADES`·`gradeValue`·`averageGrade`는 그대로
  쓰되 **등급을 직접 계산하는 코드는 없어야 합니다.**
- 리포트 전체(근거 문장·항목별 점수)는 이 경로로 안 옵니다 — 필요해지면
  별도로 올려 주십시오, 지금은 등급 한 칸만입니다.

상세: `fastapi/docs/api-contract.md`(3-6절, `featured-video` 다음)

---

## 44. AI 추천 후보를 실제로 읽을 수 있습니다 (2026-09-16 추가, 미결 `paik` 27번)

`www/src/components/SquadSuggest.tsx`의 `SUGGESTIONS`가 mock이던 자리입니다.
43번(등급)과 짝입니다 — 여기는 "누구를 추천하나"이고 43번은 "그 사람 등급을
어떻게 읽나"입니다.

### 만족해야 할 성질

1. **빈 자리를 누르면 그 포지션에 맞는 실제 후보 목록이 올 것.**
2. **위쪽에 `S`~`F` + "등급 상관없음" 거르개를 두면, 상관없음일 때 서버가
   이미 "팀 평균과 비슷한 순"으로 정렬해서 줄 것** — 화면이 다시 계산하지
   않습니다.

### 새 엔드포인트

```
GET /api/v1/teams/{team_id}/squad/candidates?position_code=GK&grade=B
→ [{ "user_id", "nickname", "card_public_slug", "grade", "provisional" }, ...]
```

`grade`는 생략하거나 `"any"`를 주면 거르지 않고 정렬만 됩니다. 응답은 43번의
등급 응답과 필드가 같습니다(`grade`·`provisional`).

### 먼저 확인

```
grep -n "SUGGESTIONS\s*:" www/src/components/SquadSuggest.tsx
```

걸리면 아직 mock 그대로입니다.

### 🔴 하지 말 것

- **거리·유사도 점수를 서버에 요구하지 마십시오.** 순서는 이미 정렬돼서
  옵니다 — `averageGrade()`로 다시 계산하지 않습니다.
- **`card_public_slug`가 `null`인 후보가 있습니다** — 아직 카드를 안 만든
  사람입니다. 링크를 안 그리는 것으로 충분합니다(39번과 같은 원칙).
- `clip`(대표 장면 영상)·`title`·`notes`(말로 적은 특징)는 이 응답에 없습니다
  — 그건 별도 범위입니다. 지금은 mock 클립·문구를 그대로 쓰고, 이름·등급만
  이 응답으로 바꿔 주십시오.

상세: `fastapi/docs/api-contract.md`(3-16절)

---

## 45. `GET /coaches`에 종목이 실립니다 — 필터도 됩니다 (2026-09-16 추가, 미결 `paik` 14번)

`market/coaches` 화면의 종목 탭·필터가 실제로 걸리게 됐습니다.

### 만족해야 할 성질

**코치 목록을 종목별로 거를 수 있을 것.**

### 바뀐 것

| | |
|---|---|
| 응답에 추가 | `sport_code`(`GET /coaches`·`GET /coaches/{id}` 둘 다) |
| 새 쿼리 | `GET /coaches?sport_code=football` — 안 주면 전체 종목 |
| 새 에러 | 모르는 `sport_code`면 422 `UNKNOWN_SPORT` |

### 먼저 확인

```
grep -n "Coach.sport\b" www/src/lib/market.ts
```

이미 `sport` 필드로 모델링해 뒀다면 mock을 지우고 그대로 흘려 넣으면 됩니다.

### 🔴 하지 말 것

- **가격·소개 문장·후기·레슨 장소·대표 영상은 아직 안 옵니다** — `market.ts`의
  나머지 mock 필드는 그대로 두십시오. 별도 결정(부록 D 변경)이 필요합니다.
- 종목 코드는 기존 종목 목록(`GET /positions`가 쓰는 것과 같은 `sport_code`
  값)을 그대로 씁니다 — 새로 짓지 않습니다.

상세: `fastapi/docs/api-contract.md`(코치 절)

---

## 46. `GET /videos/public`에 화면 비율이 실립니다 (2026-09-16 추가, 미결 `paik` 15번)

세로 영상이 16:9로 가정돼 그려지던(좌우가 검게 남는) 문제입니다.

### 만족해야 할 성질

**공개 클립 목록에서 각 영상의 실제 화면 비율을 알 수 있을 것** — 영상을
읽어서 알아내지 않고 목록 응답만으로.

### 바뀐 것

응답 각 행에 `width`·`height`(정수, px)가 추가됩니다. **이 컬럼이 생기기
전 등록분은 둘 다 `null`**입니다 — `lib/feed.ts`의 `aspect: '16 / 9'` 기본값을
그대로 쓰면 됩니다.

### 먼저 확인

```
grep -n "aspect.*16.*9\|aspect: '16" www/src/lib/feed.ts
```

### 🔴 하지 말 것

- **저장 키는 그대로 안 옵니다** — 비율만 추가된 것이지 재생 방식은 안
  바뀌었습니다.
- `width`·`height`가 `null`인 행을 에러로 다루지 마십시오 — 옛 등록분입니다.

상세: `fastapi/docs/api-contract.md`(공개 클립 목록 절)

---

## 47. `GET /videos/{id}/report`의 `breakdown[]`에 `title_earned`가 실립니다 (2026-09-16 추가, 미결 `ho` 40번)

`title`이 있으면 「받은 호칭」으로 읽고 있었다면, 0등급 항목에도 「무너지는
축」 같은 문구가 있어서 **잘못 그려지고 있었을 것입니다.**

### 만족해야 할 성질

**참인 `title_earned`가 있는 항목의 `title`만 「받은 호칭」으로 그릴 것.**

### 먼저 확인

`title`의 유무로 「받은 호칭」을 가르는 코드가 있는지 화면 쪽을 보십시오
— 있다면 `title_earned`로 바꿔야 합니다.

### 🔴 하지 말 것

- `grade === 2`로 대신 긋지 마십시오 — 지금은 같은 답이 나오지만, 조건에
  "루브릭이 그 등급의 문구를 실제로 적었을 것"이 같이 걸려 있어서 칭호를
  안 쓴 루브릭이 들어오면 갈립니다.
- `title_earned`가 `null`인 항목(제외됐거나 옛 리포트)을 거짓으로 그리지
  마십시오 — 흐린 칭호·자물쇠·「미달」 전부 미달 표식입니다. **아무것도
  안 그리는 것이 맞습니다.**

상세: `fastapi/docs/api-contract.md`(리포트 조회 절)

---

## 48. `POST /videos` 응답에 `duplicate_of_video_id`·`duplicate_status`·`duplicate_failure_reason`이 실립니다 (2026-09-16 추가, `ho` 41번)

같은 사람이 같은 내용의 영상을 다시 올리면(예: 게이트 미달로 떨어진 영상을
그대로 재업로드) 서버가 **새 분석 작업을 안 만들고** 이전 결과를 이 응답에
바로 실어 줍니다 — `analysis_job_id`는 `null`입니다.

### 만족해야 할 성질

등록 직후 `duplicate_of_video_id`가 있으면 **"이 영상은 앞서 같은 이유로
분석되지 않았습니다"** 류의 안내를 그 자리에서 보여줄 것. `duplicate_status`가
`"failed"`면 `duplicate_failure_reason`(에이전트 사유 문구, 정상호 몫)을 같이
보여주고, `"succeeded"`면 이미 성공했다는 사실만 알리거나 `duplicate_of_video_id`로
`GET /videos/{id}/report`를 불러 그 결과를 보여줘도 됩니다.

### 🔴 하지 말 것

- 재업로드 자체를 막지 마십시오 — 촬영을 다시 해서 올린 것일 수 있습니다.
  이건 **안내**지 차단이 아닙니다.
- 이 셋은 **등록 응답에만** 실립니다. 나중에 `GET /videos`로 같은 영상을
  다시 읽으면 셋 다 `duplicate_of_video_id`를 빼고 전부 `null`입니다(그
  영상 자신은 애초에 작업이 없어서 `analysis_status`도 `null`) — 이 응답을
  놓치면 다시 볼 방법이 `duplicate_of_video_id`를 따라가는 것뿐이니, 화면에
  받는 즉시 반영해 주십시오.
- 「이 사람으로 분석」·「집중해서 볼 항목」을 지정해서 올린 경우는 대상에서
  빠집니다(항상 새로 분석합니다) — 그런 업로드에서 이 필드들이 안 와도
  버그가 아닙니다.

상세: `fastapi/docs/api-contract.md`(영상 등록 절)

---

## 49. 팀 초대·수락 경로가 생겼습니다 (2026-09-16 추가, `min` 20번)

챗봇 용병 검색 결과에서 **후보를 고를 수가 없다**(목록만 보여주고 끝)던
것이 `min` 20번이었습니다. 이제 초대를 보내고 받은 사람이 수락하는
경로가 열렸습니다.

**앞서 `api-contract.md` 3-3절에 「초대·승인 테이블이 부록 D 에 없어
신청-승인 흐름은 넣지 않았다」고 적었던 것을 정정합니다** — `team_invitation`
테이블을 새로 두었습니다.

### 만족해야 할 성질

1. **검색 결과에서 「초대」를 누르면** `POST /teams/{team_id}/invitations`
   (본문 `{"invited_user_id": "..."}`)가 불린다. 주장만 부를 수 있다.
2. **받은 사람 화면에 초대가 뜬다** — `GET /me/invitations`(아직 답 안 한
   것만) 또는 알림 목록의 `team_invitation_sent`.
3. **받은 사람이 수락/거절한다** —
   `POST /me/invitations/{id}/accept` · `.../reject`. 수락하면 그때
   `GET /teams/{id}` 의 `members[]` 에 실제로 들어갑니다.
4. **주장이 무를 수 있다** — `DELETE /teams/{team_id}/invitations/{id}`.
   🔴 `204` 가 아니라 무른 초대를 본문으로 돌려줍니다(다른 응답과 같은
   모양이라 같은 파서를 쓸 수 있습니다).

화면 위치·문구는 예시일 뿐 규격이 아닙니다. `paik` 22번(팀 매칭 mock
표시)의 초대함 mock 이 있다면 이제 실물로 바꿀 수 있습니다.

### 🔴 하지 말 것

- **`POST /teams/{id}/members` 로 바로 넣지 마십시오** — 2026-09-10 박민호
  결정(동의 없이 꽂지 않는다)과 정반대입니다. 그 경로는 본인이 스스로
  가입할 때만 씁니다.
- **거절을 「실패」로 그리지 마십시오** — `200` 이고 정상 흐름입니다.
  아무것도 안 바뀐 것이 맞는 결과입니다.
- 무르기(cancel)에는 **알림이 없습니다** — 보낸 쪽이 스스로 하는 것이라
  알릴 상대가 없습니다. 알림이 안 온다고 실패로 보지 마십시오.

상세: `fastapi/docs/api-contract.md`(3-3절 「팀 초대」)

---

## 50. 야구·농구로는 **새로 못 만듭니다** — `SPORT_NOT_AVAILABLE` (2026-09-16 추가, `ho` 39번)

에이전트가 축구 단일 종목으로 정리되면서 야구·농구 루브릭이 사라졌습니다.
그동안 백엔드는 그대로 받아 줬고, **워커가 나중에 거부**했습니다 — 사용자
입장에서는 올린 뒤에야 실패했습니다. 이제 올리기 전에 막습니다.

- **팀 만들기**(`POST /teams`)·**영상 등록**(`POST /videos`)에서
  `sport_code` 가 야구·농구면 `422 SPORT_NOT_AVAILABLE`
- **조회·거르기는 그대로 돕니다** — `GET /positions?sport_code=baseball`,
  경기·코치 목록의 종목 필터는 내려간 종목도 계속 돕니다. 이미 그 종목으로
  올라간 과거 데이터를 계속 볼 수 있어야 해서입니다

### 만족해야 할 성질

**`UNKNOWN_SPORT` 와 다르게 안내할 것.** 앞의 것은 오타(입력을 고쳐야
함)이고, 이것은 **입력은 맞는데 지금 안 받는 것**입니다 — 「지금은 축구만
받습니다」 쪽이 맞는 문구입니다.

### 먼저 확인

`www` 는 이미 2026-09-14에 종목 선택지를 축구 하나로 좁히셨으니 **화면에서는
이 에러가 안 날 것입니다.** 확인해 보실 곳은 `flutter/lib/core/mock/mock_db.dart`
— 목 데이터에 아직 세 종목이 있습니다. 거기서 야구·농구로 등록을 시도하면
이제 422 입니다.

### 🔴 하지 말 것

- **종목 목록을 코드에 다시 고정하지 마십시오** — 되살릴 때 `sport.active`
  를 올리면 되게 해 뒀습니다(행은 안 지웠습니다). 클라이언트가 고정 목록을
  들고 있으면 그때 또 배포가 필요해집니다.
- `SPORT_NOT_AVAILABLE` 을 **「서버 오류」로 그리지 마십시오** — 정상적인
  거절이고, 사용자가 할 일은 축구를 고르는 것뿐입니다.

상세: `fastapi/docs/api-contract.md`(3-3절 팀 만들기 · 영상 등록 절)

---

## 51. 호칭을 **사람이 직접 적는 칸**이 열렸습니다 (2026-09-16 추가, `paik` 36번)

요청하신 대로 `PATCH /me/card` 에 `titles` 를 열었습니다. 읽는 자리는 **이미
있던 `titles[]` 그대로**라, 말씀하신 대로 화면은 손댈 것이 거의 없습니다.

```jsonc
// 적기 — 보낸 목록이 그대로 남습니다(부분 병합 아님)
PATCH /me/card   { "titles": ["시야가 넓은", "왼발잡이"] }
// 지우기
PATCH /me/card   { "titles": [] }      // 또는 null
```

- **3개까지, 한 개당 20자까지**(`tagline` 과 같은 길이). 넘으면 422 입니다 —
  🔴 **조용히 자르지 않습니다**
- 앞뒤 공백은 서버가 털고, 빈 글자는 버리고, **같은 글은 하나만** 남깁니다
- 안 보내면 안 건드립니다(`tagline` 만 고치는 요청이 호칭을 지우지 않습니다)

### 🔴 `category` 가 `null` 일 수 있습니다 — 여기가 유일하게 손볼 자리입니다

그전에는 `titles[].category` 가 **항상 문자열**이었는데, 직접 적은 호칭은
`null` 입니다. 분류는 부록 D 가 정의한 셋뿐이고 그건 부여되는 호칭의
것이라, 말씀하신 「분류를 요구하지 말 것」을 이렇게 지켰습니다.

| | 부여된 호칭 | 직접 적은 호칭 |
|---|---|---|
| `code` | `sharp_shooter` 같은 정의 코드 | **`custom:` 으로 시작** |
| `category` | `강점`·`활동`·`용병` | **`null`** |

둘을 갈라 그리셔야 하면 `category === null` 이나 `code.startsWith("custom:")`
중 아무거나 쓰시면 됩니다.

### 먼저 확인

```bash
grep -n 'category' www/src/**/*.tsx | grep -i title
```

`category` 를 **문자열이라고 가정하고** 쓰는 자리가 있으면 `null` 을 견디게
해 주세요(칩 색을 분류로 고르는 식이면 기본값이 필요합니다).

### 🔴 하지 말 것

- **`tagline` 에 겹쳐 쓰지 마십시오** — 말씀하신 그대로입니다. 카드 가운데
  큰 글자가 이미 그 칸을 씁니다.
- **빈 배열을 표식으로 만들지 마십시오** — 아직 안 적은 것이 정상입니다.
- `title_definition` 에 행이 늘지 않습니다 — 자유 문자열이라 별도 테이블
  (`user_custom_title`)에 담습니다. 코드로 가리킬 값이 아닙니다.

상세: `fastapi/docs/api-contract.md`(3장 `PATCH /me/card` 의 「`titles`」 절)

---

## 52. 팀 이름·지역을 **고칠 수 있게 됐습니다** — `PATCH /teams/{id}` (2026-09-16 추가)

그전에는 팀을 만들 때 적은 값이 **영영 고정**이었습니다. 고칠 경로가 아예
없었습니다.

**이게 왜 급한가**: 「사람을 찾는 팀」 판이 지역으로 거르는데
(`GET /matches?region=`), 그 값이 `team.region` 입니다. 오타를 내거나
연고를 옮기면 **그 팀 경기가 검색에서 통째로 빠지는데 고칠 방법이
없었습니다.**

```jsonc
PATCH /teams/{team_id}   { "region": "부산 해운대구" }   // 주장만
PATCH /teams/{team_id}   { "name": "천둥FC" }
PATCH /teams/{team_id}   { }                            // 아무것도 안 바뀜
```

응답은 `GET /teams/{id}` 와 같은 모양이라 화면이 쓰던 파서를 그대로 쓰면
됩니다.

### 만족해야 할 성질

**주장이 팀 설정에서 이름·지역을 고칠 수 있을 것.** 화면 위치는 예시지만
자연스러운 자리는 팀 화면의 「설정 수정」입니다 — 「사람을 찾는 팀」 판에
이미 그 단추가 있습니다.

### 🔴 하지 말 것

- **`null` 을 보내 지우려 하지 마십시오** — 422 입니다. 둘 다 NOT NULL 이라
  「안 정한 상태」가 없습니다. 안 바꿀 필드는 **아예 빼십시오**
  (`PATCH /me/card` 의 `tagline` 과 다릅니다. 그쪽은 `null` 이 「지우기」예요).
- **`sport_code` 를 보내지 마십시오** — 본문에 자리가 없어 무시됩니다.
  포지션·스쿼드·경기가 전부 그 값에 매달려 있어서 바꾸면 이미 앉힌
  포지션이 다른 종목 것이 됩니다. 종목을 바꿔야 하면 팀을 새로 만드는
  쪽이 맞습니다.
- 구성원에게 수정 UI 를 보이지 마십시오 — **주장만** 됩니다(403).

상세: `fastapi/docs/api-contract.md`(3-3절 `PATCH /teams/{team_id}`)

---

## 53. 받은 초대 한 줄에 **팀 이름·부르는 자리·스쿼드 슬러그**가 실립니다 (2026-09-17 추가, `paik` 37번)

`GET /me/invitations` 가 주던 것이 id 뿐이라, 받은 사람 화면이 「어느 팀이
무엇으로 부르는지」를 그릴 값이 없었습니다.

```jsonc
GET /me/invitations
[
  {
    // 지금까지 주던 칸 — 그대로입니다
    "id": "0d2f...", "team_id": "7c05...", "invited_user_id": "9a2e...",
    "status": "pending", "created_at": "...", "responded_at": null,

    // 늘어난 칸
    "position_code": "GK",          // null 일 수 있습니다
    "position_label": "골키퍼",      // null 일 수 있습니다
    "team_name": "번개FC",
    "team_region": "서울 강남",
    "team_sport_code": "football",
    "squad_public_slug": "sq-abc123" // null 일 수 있습니다
  }
]
```

🔴 **기존 칸은 자리가 안 바뀝니다** — `team` 객체로 감싸지 않았습니다. 지금
`row.team_id` 를 읽는 코드는 **그대로 둬도 됩니다.** 늘어난 칸만 더 읽으면
됩니다.

### 초대를 보낼 때 자리를 함께 정할 수 있습니다

```jsonc
POST /teams/{team_id}/invitations   { "invited_user_id": "...", "position_code": "GK" }
POST /teams/{team_id}/invitations   { "invited_user_id": "..." }   // 자리 안 정함
```

`position_code` 는 **선택**입니다. 이 팀 종목에 없는 약칭이면 `422
UNKNOWN_POSITION` 입니다 — 목록은 `GET /positions?sport_code=` 입니다.
약칭은 **종목 안에서만** 유일합니다(축구 `FW` ≠ 농구 `FW`).

### 🔴 앞서 미결 항목에 적힌 두 가지를 정정합니다

1. **「받는 사람은 소속이 아니라 `GET /teams/{id}` 가 403」은 사실이 아닙니다.**
   그 경로에는 소속 검사가 없습니다 — 인증만 있으면 누구나 읽습니다(가입하려면
   먼저 봐야 하니까요). 즉 팀 이름은 **그전에도** 얻을 수 있었습니다. 이번에
   실어 준 것은 목록에서 줄마다 부르지 않아도 되게 하려는 것입니다.
   자체 우회를 이미 만드셨다면 걷어내셔도 됩니다.
2. **경기 시각·구장은 안 줍니다.** 초대가 경기에 묶이지 않기 때문입니다 —
   「우리 팀에 오세요」이지 「이 경기에 와 달라」가 아닙니다(`team_invitation`
   에 경기를 가리키는 칸이 없습니다). 경기 쪽은 `team_match_request`(팀 대 팀)가
   따로 담습니다. **그 두 칸은 빼고 그리시면 됩니다.**

### 만족해야 할 성질

1. **초대 한 줄만 보고 수락 여부를 정할 수 있을 것** — 팀 이름·지역, 부르는
   자리(있으면), 그리고 판.
2. **`squad_public_slug` 로 작은 스쿼드 판을 그릴 것** — `GET /squads/{slug}`
   는 누구나 읽습니다. 새 경로도 새 부품도 필요 없습니다(`SquadPanel` 재사용).

### 🔴 하지 말 것

- **`position_*` 가 `null` 인 것을 실패로 보지 마십시오** — 자리를 안 정한
  초대가 정상입니다. 그때는 자리 줄을 안 그리면 됩니다.
- **`squad_public_slug` 가 `null` 인 것도 정상입니다** — 스쿼드를 아직 안 만든
  팀입니다. 판 대신 「아직 판이 없습니다」로 두시면 됩니다.
- **`position_code` 만 보고 이름을 지어내지 마십시오** — `position_label` 이
  같이 갑니다. 종목마다 같은 약칭이 다른 뜻이라 클라이언트가 표를 갖고
  있으면 갈립니다.

### 확인

```bash
# 늘어난 칸이 실제로 나가는가 (로그인 토큰 필요)
curl -s -H "Authorization: Bearer $TOKEN" "$API/api/v1/me/invitations" | jq '.[0]'
```

상세: `fastapi/docs/api-contract.md`(3-3절 「팀 초대」)

---

## 54. **마지막 주장이 팀을 버릴 수 있게 됐습니다** — 해체와 주장 세우기 (2026-09-17 추가, `paik` 35번)

혼자 만든 팀을 **영영 못 버리던 것**이 풀렸습니다. 길이 둘입니다.

```jsonc
DELETE /teams/{team_id}                          // 해체 (주장만) → 204
PATCH  /teams/{team_id}/members/{member_id}      // 주장 세우기 (주장만)
       { "role": "owner" }                       // → 200, 갱신된 팀
```

### 🔴 해체는 **행을 지우지 않습니다** — 화면이 알아야 할 것

`GET /teams/{id}` 는 해체 뒤에도 **200** 입니다. 지난 경기·평가가 그 팀
이름을 가리키기 때문입니다. 대신 응답에 칸이 하나 생겼습니다.

```jsonc
{ "id": "...", "name": "번개FC", "region": "서울 강남", "sport_code": "football",
  "members": [],                    // 해체되면 빈 배열입니다
  "disbanded_at": "2026-09-17T…Z"   // 살아 있는 팀은 null
}
```

- **해체하면 그 팀은 `GET /me` 의 `teams` 에서 사라집니다** — 구성원을 전부
  내보내기 때문입니다. 목록 화면은 따로 거를 것이 없습니다.
- 대기 중이던 **초대·경기 신청은 자동으로 `cancelled`** 가 됩니다.
- 해체된 팀에는 **못 들어가고 못 고치고 못 초대합니다** — 전부 409
  `TEAM_DISBANDED` 입니다.

### 🔴 앞으로 있을 경기가 있으면 해체가 **막힙니다**

409 `TEAM_HAS_UPCOMING_MATCH` 입니다. 상대 팀에는 약속이라, 경기를 먼저
정리하고 해체해 달라는 안내가 필요합니다. **지난 경기는 세지 않습니다.**

### 주장 세우기 — `LAST_OWNER` 안내가 이제 실행 가능합니다

`DELETE /teams/{id}/members/{id}` 의 409 `LAST_OWNER` 메시지가 "다른 주장을
먼저 세워야 합니다"라고 말하는데, **그전에는 세울 경로가 없었습니다.** 이제
있습니다.

🔴 **기존 주장은 그대로 주장입니다** — 주장은 여럿일 수 있습니다. 「넘기고
나가기」는 세운 다음 나가는 **두 번의 호출**입니다. 한 번에 묶지 않은 것은
「넘기기만」 하려는 경우를 표현할 수 없게 되기 때문입니다.

### 만족해야 할 성질

1. **혼자인 팀의 주장이 그 팀을 정리할 수 있을 것** — 팀 설정에 「팀 해체」.
   되돌릴 수 없으므로 확인 한 번은 받는 편이 좋습니다.
2. **여럿인 팀의 주장이 나갈 수 있을 것** — 구성원 목록에서 「주장으로
   세우기」를 누르고 나갑니다.
3. **`disbanded_at` 이 찬 팀을 살아 있는 팀처럼 그리지 말 것.**

### 🔴 하지 말 것

- **해체를 「삭제」로 말하지 마십시오** — 지난 경기 기록은 그대로 남습니다.
  「팀 해체」가 정확합니다.
- **해체된 팀을 404 로 가정하지 마십시오** — 200 이고 `members` 가 빈
  배열입니다. 경기 이력에서 팀 이름을 읽으려면 그래야 합니다.
- **`role` 에 `owner`·`member` 밖의 값을 보내지 마십시오** — 422 입니다.
- **홈 팀 쿠키**(`www/src/lib/homeTeam.ts`)가 해체된 팀을 가리킬 수 있습니다.
  서버가 그 값을 안 믿고 소속 기준으로 떨어뜨리므로 깨지진 않지만, 해체 직후
  그 쿠키를 비워 주시면 한 번 헛도는 것을 줄일 수 있습니다.

### 확인

```bash
# 해체 뒤에도 읽히는가 · disbanded_at 이 차는가
curl -s -H "Authorization: Bearer $TOKEN" "$API/api/v1/teams/$TEAM_ID" | jq '.disbanded_at, .members'
```

상세: `fastapi/docs/api-contract.md`(3-3절 `DELETE /teams/{team_id}` ·
`PATCH /teams/{team_id}/members/{member_id}`)

---

## 55. 경기 신청에 **두 팀의 이름·지역**이 실립니다 (2026-09-17 추가, `paik` 31번)

`TeamMatchRequestResponse` 에 넷이 더 붙습니다. 알림 판이 「**망원
유나이티드**가 경기를 걸었습니다」를 그대로 쓸 수 있습니다.

```jsonc
{
  // 지금까지 주던 칸 — 그대로입니다
  "id": "...", "requester_team_id": "...", "target_team_id": "...",
  "proposed_played_at": "...", "proposed_place": "강남 풋살장",
  "status": "pending", "created_at": "...", "responded_at": null, "match_id": null,

  // 늘어난 칸
  "requester_team_name": "번개FC",        "requester_team_region": "서울 강남",
  "target_team_name": "망원 유나이티드",   "target_team_region": "서울 마포구"
}
```

🔴 **기존 칸은 자리가 안 바뀝니다** — 감싸지 않고 덧붙였습니다. 생성·목록·
수락·거절·무르기 **다섯 경로가 전부 같은 모양**이라 파서 하나로 읽힙니다.

### 🔴 먼저 정정합니다 — 「팀 하나를 읽는 경로가 없다」는 사실이 아니었습니다

항목에 *"`GET /teams/{id}` 가 없고"* 라고 적혀 있었는데 **있습니다.** 계약
문서 3-3절에 있고(1180줄) **소속이 아니어도 읽힙니다**(인증만 필요).

그리고 항목의 「확인」 명령이 **오탐이었습니다**:

```bash
grep -n 'requester_team_name\|GET /api/v1/teams/{team_id}$' fastapi/docs/api-contract.md
```

끝의 `$` 가 문제입니다 — 실제 줄은 ``### `GET /api/v1/teams/{team_id}` `` 로
**백틱으로 끝나서** 안 걸립니다. 「없다」가 아니라 **「패턴이 안 맞았다」**
였습니다. 앞으로 그 자리는 이렇게 보시면 됩니다.

```bash
grep -n 'GET /api/v1/teams/{team_id}' fastapi/docs/api-contract.md
```

**그래도 넷을 실은 이유**는 「경로가 없어서」가 아니라 **목록에서 줄마다
부르지 않아도 되게** 하려는 것입니다. 받은 신청이 N 건이면 `GET /teams/{id}`
를 N 번 부르게 됩니다.

### 만족해야 할 성질

**받은 경기 신청 줄에 상대 팀 이름·지역이 그대로 보일 것.**
`www/src/components/NotifyPanel.tsx` 가 이 값을 쓰고,
`www/src/lib/teamMatch.ts` 의 붙박이 목록 폴백(`teamById`, 못 찾으면
「상대 팀」)은 **걷으시면 됩니다.**

### 🔴 하지 말 것

- **이 값을 캐시하지 마십시오** — 항목에 적어 두신 그대로입니다. 서버는
  매번 `team` 에서 읽으므로 팀 이름이 바뀌면(`PATCH /teams/{id}`) 다음
  조회에 바로 반영됩니다. 캐시하면 그 이점이 사라집니다.
- **id 칸을 지우지 마십시오** — 이름은 표시용이고, 팀을 가리키는 것은 여전히
  id 입니다(스쿼드·팀 화면으로 넘어갈 때 씁니다).

### 확인

```bash
grep -n 'requester_team_name' fastapi/docs/api-contract.md
```

상세: `fastapi/docs/api-contract.md`(3-15절)

---

## 56. 추천 판 카드의 **불릿 한두 줄**이 진짜가 됩니다 (2026-09-17 추가, `paik` 33번)

`SquadSuggest.tsx` 의 `FLAVOR` 에 붙박이로 있던 그 문장입니다. 두 자리에서
같은 값을 받습니다 — **같은 리포트에서 온 값**이라 어느 쪽을 써도 같습니다.

```jsonc
GET /teams/{team_id}/squad/candidates     // 추천 판 — 여기 이미 실립니다
[ { "user_id": "...", "nickname": "김선우", "card_public_slug": "kim-abc1",
    "grade": "A", "provisional": false,
    "notes": ["차는 다리를 끝까지 뻗습니다", "디딤발을 공 옆에 붙입니다"] } ]

GET /cards/{card_public_slug}/grade       // 슬러그만 아는 자리
{ "grade": "S", "provisional": false, "notes": ["..."] }
```

🔴 **추천 판은 후보마다 `/grade` 를 다시 부르지 않아도 됩니다** — 목록 응답에
이미 들어 있습니다.

### 🔴 셋 다 정상값입니다 — 실패로 보지 마십시오

| 받는 값 | 뜻 | 화면 |
|---|---|---|
| 두 줄 | 보통 | 불릿 둘 |
| **한 줄** | **정상** — 두 줄을 채우려고 지어내지 않는 것이 규칙입니다 | 불릿 하나 |
| `null` | `card` 칸이 없던 봉투(1.4 이하)로 적재됐거나 분석 전 | 그 줄을 안 그림 |

### 만족해야 할 성질

**후보 카드의 불릿이 서버가 준 문장일 것.** `FLAVOR` 의 붙박이 문장은
걷으시면 됩니다.

### 🔴 하지 말 것

- **화면에서 문장을 짓지 마십시오** — 분석이 낸 것만 씁니다. 「반대편 빈
  공간을 자주 찾습니다」류는 **잴 수 있는 근거가 없습니다**(정상호 확인,
  `ho` 50번).
- **두 줄이라고 가정하지 마십시오** — 한 줄이 정상입니다.
- **경기 기록 줄(활동량·출전 수)과 섞어 한 목록에 두지 마십시오** — 분석이
  잰 것과 아닌 것이 섞이면 어디까지가 측정인지 사라집니다(`ho` 50번의
  「출처를 화면에서 구분해 주세요」). 지금 카드에는 **사람이 적은 호칭**
  (계약 51번)과 **분석이 낸 불릿**이 나란히 놓입니다.
- **이름 아래 한 줄로 쓰지 마십시오** — 그 자리는 사람이 적는 호칭입니다
  (계약 51번, `paik` 36번). 이건 그 아래 불릿입니다.

### 확인

```bash
grep -n '"notes"' fastapi/docs/api-contract.md
```

상세: `fastapi/docs/api-contract.md`(3-6절 `GET /cards/{slug}/grade` ·
3-14절 `GET /teams/{id}/squad/candidates`)

## 57. 지인 목록·닉네임 검색에 **카드 슬러그**가 실립니다 (2026-09-17 추가, 미결 `paik` 39번)

홈 스쿼드 판이 앉은 사람의 **진짜 카드**를 그리는데, **지인으로 앉힌 사람만**
찾아갈 값이 없어 이름표로 남았습니다 — 같은 판 안에서 어디서 앉혔느냐에 따라
카드가 뜨기도 안 뜨기도 했습니다.

```jsonc
GET /me/contacts
{ "items": [ { "contact_id": "...", "user_id": "...", "nickname": "김철수",
               "note": null, "accepted_at": "...",
               "card_public_slug": "kim-chulsoo-1a2b" } ] }

GET /users/search?q=김
[ { "id": "...", "nickname": "김철수", "card_public_slug": "kim-chulsoo-1a2b" } ]
```

추천 후보(`/squad/candidates`)가 이미 주던 것과 **같은 모양**입니다.

### 🔴 셋 다 정상값입니다

| 받는 값 | 뜻 | 화면 |
|---|---|---|
| 슬러그 | 카드를 만든 사람 | `GET /cards/{slug}` 로 그 카드를 그림 |
| `null` | **카드를 아직 안 만든 사람** — 정상입니다 | 이름표만 |

🔴 **칸이 빠지는 것이 아니라 `null` 입니다** — 그래야 화면이 「아직 못 받았다」와
「카드가 없다」를 가릅니다.

### 🔴 하지 말 것

- **내부 `user_id` 로 카드를 찾지 마십시오** — 밖으로 나가는 것은 슬러그뿐입니다
  (카드·스쿼드가 지켜 온 원칙). 서버가 여기서 바꿔 줍니다.
- **카드가 없는 사람을 목록에서 빼지 마십시오** — 지인은 지인입니다.

### 누가 고쳤나

🔴 **백성검이 고쳤습니다**(정어진 승인, 2026-09-17). 마이그레이션은 없습니다 —
응답 필드만 늘었고 `player_card` 는 기존 관례대로 **원시 쿼리**로 읽습니다
(`user` 가 `card` 를 임포트하지 않도록 — `has_card` 와 같은 방식). 사람마다 따로
읽지 않고 **한 번에** 읽습니다.

- 확인: `.venv/bin/pytest -q` → 766 passed (새 시험 3)

## 58. 보낸 초대에 **초대받은 사람**이 실립니다 (2026-09-17 추가)

`GET /teams/{team_id}/invitations` 의 각 줄에 둘이 더 붙습니다.

```jsonc
{ "...": "지금까지 주던 칸 그대로",
  "invited_user_nickname": "정상호",
  "invited_user_card_slug": "jung-1a2b" }
```

🔴 **왜 필요했나.** 주장이 스쿼드 판에 앉힌 사람은 **초대로 남는데**,
`invited_user_id` 만으로는 새로고침 뒤에 **누구인지도 무슨 카드인지도** 그릴
수가 없었습니다. 받는 쪽(`GET /me/invitations`)에 팀 넉 칸을 실어 준 것과
**같은 이유·같은 방식**입니다 — 줄마다 `GET /users/...` 를 부르지 않게.

| 받는 값 | 뜻 |
|---|---|
| 닉네임 | 늘 있습니다 |
| 카드 슬러그 | 카드를 만든 사람만. **없으면 `null`** — 이름표로 그리면 됩니다 |

### 누가 고쳤나

🔴 **백성검이 고쳤습니다**(정어진 승인, 2026-09-17). 계약 57번과 같이
**마이그레이션 없이** 응답 필드만 늘렸고, `player_card` 는 기존 관례대로
원시 쿼리로 바깥 조인합니다.

- 확인: `.venv/bin/pytest -q` → 767 passed

---

전체 규격은 `fastapi/docs/api-contract.md` 에 있다. 이 문서는 **바뀐 것만** 추린
것이다. 새로 붙이는 화면이 있으면 계약 문서 쪽을 본다.

질문이나 규격이 애매한 곳이 있으면 알려 주기 바란다 — 클라이언트가 쓰기 불편한
계약이면 백엔드를 고치는 편이 맞다.
