# 웹앱 설계 — `www/` (Next.js)

> **상태:** 설계 승인됨, 구현 전 · 2026-08-28
> **담당:** 백성검 (프론트·웹)
> **도메인:** `supersub-ai.com` (가비아, 2026-08-28 등록)
> **배포:** Vercel — Root Directory `www`
> **백엔드 계약:** `fastapi/docs/api-contract.md`

## 0. 정해진 것

| | |
|---|---|
| 스택 | Next.js (App Router) + React |
| 위치 | 저장소 루트의 `www/` — `flutter/`·`fastapi/`·`agent/`와 같은 레벨 |
| 접근 | **mock 우선** — 화면을 mock 데이터로 먼저 세우고, 백엔드가 배포되면 갈아끼운다 |
| 인증 | 액세스 토큰을 **httpOnly 쿠키**에, 호출은 Next.js Route Handler가 중계한다 |

## 1. 왜 Flutter 웹이 아닌가

Flutter도 웹 빌드는 된다. 그런데 지금 `flutter/lib/core/design_scale.dart`가

```dart
const double _kDesignWidth = 1080;
double d(double designPx) => MediaQuery.sizeOf(this).width * designPx / _kDesignWidth;
```

처럼 **화면 폭 하나로 모든 좌표를 환산한다.** 1080px 세로 목업 기준이라 1920px 브라우저에서는 모든 요소가 1.78배로 부푼다. 이 `d()`에 8개 파일이 물려 있어서, Flutter 웹으로 가도 화면은 어차피 다시 짜야 한다.

다시 짤 거라면 웹은 웹 스택으로 짜는 편이 낫다. 특히 `GET /cards/{public_slug}` 공개 선수 카드는 **링크로 공유될 때 미리보기 이미지가 떠야** 의미가 있는데, 이건 서버 렌더링이 되는 Next.js가 공짜로 해준다.

## 2. 위치와 빌드 경계

`www/`는 Jekyll 사이트의 콘텐츠가 아니라 소스 코드다. `_config.yml`의 `exclude:`에 한 줄 추가한다 — `demo/`·`agent/`·`flutter/`·`fastapi/`가 이미 같은 이유로 제외돼 있다.

```yaml
exclude:
  - demo/
  - agent/
  - flutter/
  - supersub-preview.service
  - fastapi/
  - www/      # ← 추가
```

넣지 않으면 Jekyll이 `www/node_modules`까지 빌드하려 든다.

> `_config.yml`을 바꿨으므로 로컬 미리보기는 한 번 재시작해야 한다:
> `sudo systemctl restart supersub-preview.service`

## 3. 라우트

| 경로 | 내용 | 인증 | 렌더링 |
|---|---|---|---|
| `/` | 랜딩 — 제품 소개, 로그인 진입 | – | 정적 |
| `/login` | 이메일+비밀번호, 구글 | – | 클라이언트 |
| `/signup` | 회원가입 | – | 클라이언트 |
| `/me` | 내 프로필, 닉네임 수정 | 필요 | 서버 |
| `/me/card` | 내 선수 카드 | 필요 | 서버 |
| `/c/[slug]` | **공개 선수 카드** — 공유 미리보기(OG 태그) | – | 서버 |
| `/analysis` | 영상 분석 | 필요 | mock 전용 |

`/analysis`는 **백엔드 API가 아직 없다** (`api-contract.md` 5절 "이 범위에 넣지 않은 것"). 화면 자리만 잡아두고 mock으로 둔다.

## 4. 데이터 레이어

Flutter 앱이 이미 인터페이스 하나 + 구현 둘로 갈라 놓았다 (`auth_repository.dart` / `_mock.dart` / `_api.dart`). **웹도 같은 모양으로 간다** — 팀 안에서 용어가 통하고, 백엔드 배포 전후로 전환하는 지점이 한 군데로 모인다.

다만 5절의 BFF 때문에 층이 하나 더 있다. **브라우저는 FastAPI를 모른다.**

```
www/src/lib/api/            # 브라우저 쪽. 같은 오리진 /api/* 만 부른다 (얇다)
www/src/server/backend/     # 서버 쪽. Route Handler 가 쓴다
  auth.ts                   #   인터페이스
  auth.mock.ts              #   mock 구현
  auth.fastapi.ts           #   실제 FastAPI 호출
  index.ts                  #   USE_MOCK 으로 둘 중 하나를 고른다
```

mock/실제 전환은 **서버에서만** 일어난다. 환경변수는 `USE_MOCK` — `NEXT_PUBLIC_`을 붙이지 않는다. 붙이면 클라이언트 번들에 박히고, 백엔드 주소까지 따라 나갈 수 있다.

브라우저 입장에서는 mock이든 실제든 부르는 주소가 `/api/...`로 똑같다. 그래서 화면 코드는 백엔드 배포 여부와 무관하게 한 번만 짜면 된다.

## 5. 인증 — Next.js를 BFF로 쓴다

브라우저가 FastAPI를 직접 부르지 않는다. `www/src/app/api/*`의 Route Handler가 받아서 서버에서 FastAPI로 중계한다.

```
브라우저 → (같은 오리진) www/app/api/... → (서버-서버) FastAPI
```

이렇게 하는 이유 두 가지:

**CORS 설정이 필요 없다.** 브라우저는 같은 오리진만 부르고, 서버끼리의 호출에는 CORS가 적용되지 않는다. 백엔드(정어진)에 부탁할 일이 하나 줄어든다.

**액세스 토큰이 JS에 노출되지 않는다.** 계약서 0절에 적힌 대로 지금은 **액세스 토큰 하나뿐이고 refresh 토큰이 없다.** 이 토큰이 `localStorage`에 있으면 XSS 한 번에 통째로 새고, 만료 전까지 되돌릴 방법이 없다. httpOnly 쿠키에 두면 JS가 읽지 못한다.

쿠키 속성: `httpOnly`, `secure`, `sameSite=lax`, 만료는 토큰 만료에 맞춘다.

## 6. 이 범위에 넣지 않은 것

- **영상 분석 실동작** — 백엔드 API 자체가 없다
- **팀/스카우팅 검색** — 계약서에 없다
- **토큰 갱신** — 백엔드가 아직 `POST /auth/refresh`를 안 만들었다
- **Flutter 앱과의 코드 공유** — Dart와 TypeScript다. 공유하는 것은 API 계약 문서뿐이다
- **다국어**

## 7. 배포

1. Vercel 프로젝트 생성 → **Root Directory = `www`**
2. Vercel Settings → Domains → `supersub-ai.com` 추가
3. Vercel이 보여주는 DNS 레코드를 **가비아 DNS 관리툴**에 그대로 입력
4. 전파 후 Vercel이 HTTPS 인증서를 자동 발급

> Vercel GitHub 연동은 `pmhllll12/super-sub.cloud`에 접근 권한이 필요하다 —
> 저장소 주인이 박민호이므로 승인이 필요할 수 있다. 막히면 `www/`에서
> `vercel` CLI로 직접 올린다 (권한 불필요).

**첫 배포는 mock으로 돈다.** 배포된 사이트는 https인데 백엔드는 `http://127.0.0.1:8000`이라 붙지 못한다. 실 연동은 FastAPI가 어딘가에 배포된 뒤다.

## 8. 다음 단계

1. 구현 계획 작성 → `www/docs/plans/`
2. `www/` 스캐폴딩 + `_config.yml` 한 줄
3. mock 데이터로 라우트 뼈대
4. Vercel 배포 + 도메인 연결
5. (백엔드 배포 후) `USE_MOCK` 끄고 `auth.fastapi.ts` 연결
