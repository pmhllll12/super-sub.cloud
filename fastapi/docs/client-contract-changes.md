# 클라이언트가 반영할 백엔드 계약 변경 (2026-08-26 ~ 09-02)

> **받는 사람:** 백성검 (프론트·웹 — `www/`, `flutter/`)
> **보낸 사람:** 정어진 (백엔드 — `fastapi/`)
> **상태:** 전달 · 2026-09-01 (**10번을 09-02 에 덧붙였다**)
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

## 계약 문서

전체 규격은 `fastapi/docs/api-contract.md` 에 있다. 이 문서는 **바뀐 것만** 추린
것이다. 새로 붙이는 화면이 있으면 계약 문서 쪽을 본다.

질문이나 규격이 애매한 곳이 있으면 알려 주기 바란다 — 클라이언트가 쓰기 불편한
계약이면 백엔드를 고치는 편이 맞다.
