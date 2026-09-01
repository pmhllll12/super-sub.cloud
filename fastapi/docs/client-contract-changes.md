# 클라이언트가 반영할 백엔드 계약 변경 (2026-08-26 ~ 09-01)

> **받는 사람:** 백성검 (프론트·웹 — `www/`, `flutter/`)
> **보낸 사람:** 정어진 (백엔드 — `fastapi/`)
> **상태:** 전달 · 2026-09-01
> **확인:** 아래 각 항목의 "확인" 명령을 돌리면 반영 여부가 바로 나온다.

## 이 문서를 쓰는 법

`git pull` 로 받았다면 Claude 에게 이렇게 주면 된다.

```
fastapi/docs/client-contract-changes.md 를 읽고 "조치 필요"로 표시된 것만 처리해줘.
```

**"조치 필요"만 골라 놓았다.** 이미 잘 도는 것은 `✅ 조치 불필요` 로 표시하고
왜 그런지도 적었다 — 멀쩡한 코드를 건드리지 않기 위해서다.

---

## 한눈에

| # | 변경 | www | Flutter |
|---|---|---|---|
| 1 | **429 `TOO_MANY_REQUESTS`** (인증 3경로, 1분 10회) | 🔴 조치 필요 | 🔴 조치 필요 |
| 2 | **409 `CANNOT_DELETE_SELF`** (관리자 자기 강제탈퇴 금지) | 🟡 선택 (동작은 정상) | — |
| 3 | `GET /admin/users` 의 `q` 는 **패턴이 아니라 글자** | 🟡 선택 | — |
| 4 | Flutter 가 에러 `code` 를 버린다 | ✅ 조치 불필요 | 🔴 **1번의 선행 조건** |
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

⚠️ **`Retry-After` 헤더는 아직 없다.** 언제 풀리는지 서버가 알려주지 않으므로
클라이언트가 **자체적으로 간격을 두어야** 한다. 창은 60초다.

🔴 **여기서 즉시 재시도하면 제한이 영영 안 풀린다.** 창이 60초라서, 재시도가
창 안에 계속 들어오면 카운터가 계속 차 있다. 자동 재시도 로직이 있다면 **429 에서는
반드시 멈춰야 한다.**

### www — 조치 필요

에러 자체는 이미 화면에 뜬다. `ApiCallError` 가 `status` 와 `code` 를 들고 있고
(`src/lib/api/client.ts`) 로그인 화면이 `apiErrorMessage(err)` 로 서버 문구를
그대로 보여준다. **부족한 것은 "다시 누르지 못하게" 하는 쪽이다.**

- `src/lib/api/client.ts` — `apiErrorMessage` 옆에 판별 헬퍼를 하나 둔다.

  ```ts
  /** 429. 창은 60초이고 Retry-After 는 없다 — 그 안에 다시 부르면 계속 막힌다. */
  export function isRateLimited(err: unknown): boolean {
    return err instanceof ApiCallError && err.code === 'TOO_MANY_REQUESTS'
  }
  ```

- `src/app/login/page.tsx` · `src/app/signup/page.tsx` — `catch (err)` 에서
  `isRateLimited(err)` 면 제출 버튼을 **일정 시간 잠근다.** 지금은 `setError` 만 하고
  버튼이 바로 다시 눌린다.
- `src/components/auth/GoogleSignInButton.tsx` — `onError` 로 문구만 올린다.
  같은 처리가 필요하다.

**확인**

```bash
grep -rn "TOO_MANY_REQUESTS" www/src        # 지금은 결과 없음
```

### Flutter — 조치 필요 (4번을 먼저 해야 한다)

`code` 를 버리고 있어서 **429 를 분기할 수단이 없다.** 4번을 먼저 처리한다.

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
`window.confirm` 까지 통과한 뒤에야 실패한다. 현재 로그인 사용자 id 는
`src/server/currentUser.ts` 로 얻을 수 있고, 상세 페이지가 서버 컴포넌트라
`ForceDeleteButton` 을 조건부로 렌더하면 된다.

---

## 3. 🟡 `GET /admin/users` 의 `q` 는 패턴이 아니라 글자다

`%` · `_` · `\` 를 그대로 **그 문자로** 찾는다. 와일드카드로 쓸 수 없다(`72b322b`).
전에는 `q=%` 하나로 전체가 걸렸는데 그게 버그였다.

덧붙여 계약에 명시한 것 둘 — 목록은 **`created_at` 내림차순**(최근 가입 순)이고,
`total` 은 페이지가 아니라 **검색 결과 전체**의 개수다.

### www — 🟡 선택

`src/app/admin/users/AdminSearchForm.tsx` 는 문자열을 그대로 넘기므로 **틀린 데가
없다.** 사용자가 `%` 를 와일드카드로 기대할 수 있다는 점만 안내 문구로 다루면 된다.

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

### 조치

- `auth_repository.dart` — `AuthException` 에 `code` 와 `status` 를 넣는다.
  기존 호출부(`auth_repository_mock.dart` 등)가 `const AuthException('문구')` 로
  부르고 있으므로 **새 필드는 선택 인자로** 두면 그쪽을 안 고쳐도 된다.
- `auth_repository_api.dart` — `_decode` 에서 `error['code']` 와
  `response.statusCode` 를 함께 실어 던진다.
- 그 다음 1번(429)을 처리한다.

**확인**

```bash
grep -rn "code" flutter/lib/features/auth/data/auth_repository.dart   # 지금은 없다
```

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

## 계약 문서

전체 규격은 `fastapi/docs/api-contract.md` 에 있다. 이 문서는 **바뀐 것만** 추린
것이다. 새로 붙이는 화면이 있으면 계약 문서 쪽을 본다.

질문이나 규격이 애매한 곳이 있으면 알려 주기 바란다 — 클라이언트가 쓰기 불편한
계약이면 백엔드를 고치는 편이 맞다.
