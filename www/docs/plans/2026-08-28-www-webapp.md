# Super-Sub 웹앱 (`www/`) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Flutter 앱과 같은 기능(인증·프로필·선수 카드)을 브라우저에서 쓰는 Next.js 웹앱을 `www/`에 만들고 `supersub-ai.com`에 배포한다.

**Architecture:** 브라우저는 FastAPI를 직접 부르지 않는다. Next.js Route Handler가 같은 오리진에서 요청을 받아 서버에서 FastAPI로 중계한다(BFF). 액세스 토큰은 httpOnly 쿠키에 두고 JS에 노출하지 않는다. 백엔드 게이트웨이는 인터페이스 하나에 구현 둘(mock / fastapi)이고 서버 환경변수 `USE_MOCK`으로 고른다 — 화면 코드는 백엔드 배포 여부와 무관하다.

**Tech Stack:** Next.js (App Router) · TypeScript · Tailwind CSS · Vitest + React Testing Library · Vercel

**Spec:** `www/docs/2026-08-28-www-webapp-design.md`

## Global Constraints

- **베이스 경로**: FastAPI는 `/api/v1`. 기본값 `http://127.0.0.1:8000/api/v1`, 환경변수 `BACKEND_BASE_URL`로 덮어쓴다.
- **필드명은 `snake_case`** — 계약서 형태를 그대로 쓴다. camelCase로 바꾸지 않는다. 팀이 계약 문서 하나만 보고 이야기하게 한다.
- **시각은 RFC 3339 UTC** 문자열(`2026-08-25T10:30:00Z`)로 받는다.
- **에러는 `code`로 분기한다. `message`로 분기하지 않는다.** 형태는 `{ "error": { "code": ..., "message": ... } }`.
- **`401 UNAUTHORIZED`와 `401 INVALID_TOKEN`을 나눠 다룬다.** 전자는 로그인 화면으로, 후자는 쿠키를 지우고 재로그인으로 보낸다.
- **카드에 수치를 절대 넣지 않는다** (계약서 4절 / 부록 D.5). 점수·등급·별점·진행률 바를 만들지 않는다.
- **호칭은 받은 것만 그린다.** `earned: false` 같은 미달 표식을 만들지 않는다.
- **사용자 간 비교·정렬 화면을 만들지 않는다.** 순위표 없음.
- **`NEXT_PUBLIC_` 접두사를 백엔드 관련 값에 붙이지 않는다.** 클라이언트 번들에 박힌다.
- **닉네임 1~20자**, **비밀번호 8자 이상** — 서버가 검증하지만 화면에서도 같은 값으로 막는다.
- `_config.yml`의 `exclude:`에 `- www/`는 **이미 들어가 있다**(커밋 `9ecf398`). 다시 넣지 않는다.

---

### Task 1: 스캐폴딩 + 테스트 하네스 + 랜딩

**Files:**
- Create: `www/` (create-next-app 산출물 전체)
- Create: `www/vitest.config.ts`
- Create: `www/vitest.setup.ts`
- Create: `www/.env.example`
- Modify: `www/package.json` (test 스크립트)
- Modify: `www/src/app/page.tsx`
- Test: `www/src/app/page.test.tsx`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: `npm test` / `npm run dev` / `npm run build`가 도는 `www/` 프로젝트

- [ ] **Step 1: Next.js 프로젝트 생성**

`create-next-app` 은 **대상 폴더가 비어 있지 않으면 거부한다.** `www/docs/` 에 설계 문서와 이 계획이 들어 있으므로, 잠깐 저장소 밖으로 비켜뒀다가 되돌린다.

```bash
cd /Users/psg/project/super-sub.cloud
mv www/docs ../supersub-www-docs-tmp
rmdir www

npx create-next-app@latest www \
  --ts --app --src-dir --tailwind --eslint \
  --import-alias "@/*" --use-npm --yes

mv ../supersub-www-docs-tmp www/docs
```

되돌아왔는지 반드시 확인한다 — 여기서 놓치면 설계 문서가 사라진다:

```bash
ls www/docs/2026-08-28-www-webapp-design.md www/docs/plans/2026-08-28-www-webapp.md
git status --short www/docs/   # 아무것도 안 나와야 한다 (삭제로 잡히면 안 된다)
```

- [ ] **Step 2: 테스트 도구 설치**

```bash
cd www
npm i -D vitest @vitejs/plugin-react jsdom \
  @testing-library/react @testing-library/dom @testing-library/jest-dom
```

- [ ] **Step 3: Vitest 설정 파일 작성**

`www/vitest.config.ts`:

```ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'node:path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    globals: true,
  },
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
})
```

`www/vitest.setup.ts`:

```ts
import '@testing-library/jest-dom/vitest'
```

- [ ] **Step 4: test 스크립트 추가**

`www/package.json`의 `"scripts"`에 넣는다:

```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 5: 실패하는 테스트를 쓴다**

`www/src/app/page.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import Home from './page'

describe('랜딩 페이지', () => {
  it('서비스 이름을 보여준다', () => {
    render(<Home />)
    expect(screen.getByRole('heading', { name: /Super-Sub/i })).toBeInTheDocument()
  })

  it('로그인으로 가는 링크가 있다', () => {
    render(<Home />)
    expect(screen.getByRole('link', { name: '로그인' })).toHaveAttribute('href', '/login')
  })
})
```

- [ ] **Step 6: 테스트가 실패하는지 확인한다**

Run: `cd www && npm test`
Expected: FAIL — create-next-app 기본 페이지에는 해당 heading과 링크가 없다.

- [ ] **Step 7: 랜딩 페이지를 쓴다**

`www/src/app/page.tsx` 전체를 교체한다:

```tsx
import Link from 'next/link'

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center gap-8 px-6">
      <div className="space-y-4">
        <h1 className="text-5xl font-bold tracking-tight">Super-Sub</h1>
        <p className="text-lg text-neutral-500">
          생활체육 경기 영상을 분석해 용병을 찾고, 실력을 검증합니다.
        </p>
      </div>
      <div className="flex gap-3">
        <Link
          href="/login"
          className="rounded-lg bg-neutral-900 px-5 py-2.5 text-white dark:bg-white dark:text-neutral-900"
        >
          로그인
        </Link>
        <Link href="/signup" className="rounded-lg border px-5 py-2.5">
          회원가입
        </Link>
      </div>
    </main>
  )
}
```

- [ ] **Step 8: 테스트가 통과하는지 확인한다**

Run: `cd www && npm test`
Expected: PASS (2 tests)

- [ ] **Step 9: 빌드가 되는지 확인한다**

Run: `cd www && npm run build`
Expected: 성공. 실패하면 다음 태스크로 넘어가지 않는다 — Vercel 배포가 같은 빌드를 쓴다.

- [ ] **Step 10: `.env.example` 작성**

`www/.env.example`:

```
# 서버 전용. NEXT_PUBLIC_ 을 붙이지 않는다 — 클라이언트 번들에 박힌다.
BACKEND_BASE_URL=http://127.0.0.1:8000/api/v1

# 1 이면 FastAPI 대신 mock 게이트웨이를 쓴다.
USE_MOCK=1
```

- [ ] **Step 11: 커밋**

```bash
cd /Users/psg/project/super-sub.cloud
git add www/
git commit -m "feat(www): Next.js 웹앱 뼈대 — 랜딩 한 장과 Vitest 하네스"
```

---

### Task 2: Vercel 배포 + `supersub-ai.com` 연결

오늘의 목표다. 기능을 쌓기 전에 도메인을 먼저 띄운다 — 배포가 막히는 문제를 코드가 커지기 전에 만난다.

**Files:**
- Create: `www/vercel.json`

**Interfaces:**
- Consumes: Task 1의 빌드되는 `www/`
- Produces: `https://supersub-ai.com` 에서 랜딩이 뜬다

- [ ] **Step 1: `vercel.json` 작성**

Next.js는 라우팅을 스스로 처리하므로 rewrite는 필요 없다. 리전만 서울로 당긴다.

`www/vercel.json`:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "regions": ["icn1"],
  "framework": "nextjs"
}
```

- [ ] **Step 2: 커밋**

```bash
git add www/vercel.json
git commit -m "chore(www): Vercel 설정 — 서울 리전"
```

- [ ] **Step 3: Vercel CLI 설치 및 로그인**

```bash
npm i -g vercel
vercel login
```

- [ ] **Step 4: 프로젝트 연결 및 배포**

`www/`에서 실행한다. Root Directory를 묻거든 `./`로 둔다 (이미 `www/` 안이다).

```bash
cd /Users/psg/project/super-sub.cloud/www
vercel          # 최초 1회 — 프로젝트 이름은 supersub-ai 로 한다
vercel --prod
```

> GitHub 연동으로 붙이려면 Vercel 앱이 `pmhllll12/super-sub.cloud`에 접근 권한을 받아야 하고, 저장소 주인이 박민호라 승인이 필요하다. 그 경우 Vercel 대시보드에서 **Root Directory = `www`** 로 지정한다. CLI로 올리면 권한이 필요 없다.

- [ ] **Step 5: 환경변수 등록**

배포된 환경에는 FastAPI가 없다. mock으로 돈다.

```bash
vercel env add USE_MOCK production   # 값: 1
```

- [ ] **Step 6: `.vercel.app` 주소에서 뜨는지 확인한다**

Expected: 랜딩 페이지가 뜨고 "로그인" 링크가 보인다. 여기서 안 뜨면 도메인을 붙이지 않는다.

- [ ] **Step 7: Vercel에 도메인 추가**

Vercel 대시보드 → 프로젝트 → **Settings → Domains** → `supersub-ai.com` 입력 → Add.
Vercel이 **넣어야 할 DNS 레코드를 화면에 보여준다.**

- [ ] **Step 8: 가비아에 DNS 레코드 입력**

My가비아 → **DNS 관리툴** → `supersub-ai.com` → DNS 설정.
**Vercel 화면에 뜬 값을 그대로** 넣는다. 통상 아래와 같지만 프로젝트마다 다를 수 있다.

| 타입 | 호스트 | 값 |
|---|---|---|
| A | `@` | `76.76.21.21` |
| CNAME | `www` | `cname.vercel-dns.com.` |

가비아 CNAME은 끝에 점(`.`)이 필요한 경우가 있다.

- [ ] **Step 9: 전파와 인증서를 확인한다**

Run: `dig +short supersub-ai.com`
Expected: Vercel이 알려준 A 레코드 값

전파 후 Vercel이 HTTPS 인증서를 자동 발급한다. 대시보드 Domains에 **Valid Configuration**이 뜰 때까지 기다린다 (10분~1시간).

Run: `curl -sI https://supersub-ai.com | head -1`
Expected: `HTTP/2 200`

---

### Task 3: 계약 타입과 에러 변환

**Files:**
- Create: `www/src/server/backend/types.ts`
- Create: `www/src/server/backend/errors.ts`
- Test: `www/src/server/backend/errors.test.ts`

**Interfaces:**
- Consumes: 없음
- Produces:
  - 타입 `AuthToken`, `User`, `Team`, `PlayerCard`, `PublicPlayerCard`, `Title`
  - `class BackendError extends Error { code: string; status: number; message: string }`
  - `parseErrorBody(status: number, body: unknown): BackendError`
  - `errorResponseBody(e: BackendError): { error: { code: string; message: string } }`

- [ ] **Step 1: 계약 타입을 쓴다**

`www/src/server/backend/types.ts` — 계약서 2·3절 그대로. **`snake_case`를 유지한다.**

```ts
export type AuthToken = {
  access_token: string
  token_type: 'bearer'
  expires_in: number
}

export type Team = {
  team_id: string
  name: string
  region: string
  sport_code: string
  role: string
  joined_at: string
}

export type User = {
  id: string
  email: string
  nickname: string
  created_at: string
  teams: Team[]
}

/** POST /auth/signup 의 201 응답. teams 가 없다. */
export type SignupResult = Omit<User, 'teams'>

export type Title = {
  code: string
  label: string
  category: string
  granted_at: string
}

export type PlayerCard = {
  id: string
  public_slug: string
  og_image_key: string
  user: { id: string; nickname: string }
  titles: Title[]
}

/** GET /cards/{slug} — 공개용. id 가 없다. */
export type PublicPlayerCard = Omit<PlayerCard, 'id'>
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`www/src/server/backend/errors.test.ts`:

```ts
import { BackendError, parseErrorBody, errorResponseBody } from './errors'

describe('parseErrorBody', () => {
  it('계약 형태의 에러에서 code 와 message 를 꺼낸다', () => {
    const e = parseErrorBody(401, {
      error: { code: 'INVALID_CREDENTIALS', message: '이메일 또는 비밀번호가 올바르지 않습니다.' },
    })
    expect(e.status).toBe(401)
    expect(e.code).toBe('INVALID_CREDENTIALS')
    expect(e.message).toBe('이메일 또는 비밀번호가 올바르지 않습니다.')
  })

  it('형태가 어긋난 본문이면 UNKNOWN_ERROR 로 떨어진다', () => {
    const e = parseErrorBody(500, '<html>502 Bad Gateway</html>')
    expect(e.status).toBe(500)
    expect(e.code).toBe('UNKNOWN_ERROR')
  })

  it('본문이 비어도 던지지 않는다', () => {
    const e = parseErrorBody(503, null)
    expect(e.code).toBe('UNKNOWN_ERROR')
  })
})

describe('errorResponseBody', () => {
  it('계약과 같은 형태로 되돌린다', () => {
    const e = new BackendError(404, 'CARD_NOT_FOUND', '카드가 없습니다.')
    expect(errorResponseBody(e)).toEqual({
      error: { code: 'CARD_NOT_FOUND', message: '카드가 없습니다.' },
    })
  })
})
```

- [ ] **Step 3: 테스트가 실패하는지 확인한다**

Run: `cd www && npm test -- errors`
Expected: FAIL — `./errors` 모듈이 없다.

- [ ] **Step 4: 구현한다**

`www/src/server/backend/errors.ts`:

```ts
export class BackendError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message)
    this.name = 'BackendError'
  }
}

/**
 * FastAPI 의 에러 본문을 BackendError 로 바꾼다.
 *
 * 백엔드가 항상 계약 형태로 준다는 보장은 없다 — 프록시가 끼어들면
 * HTML 이 오기도 한다. 그때도 던지지 않고 UNKNOWN_ERROR 로 떨어뜨린다.
 */
export function parseErrorBody(status: number, body: unknown): BackendError {
  if (
    body !== null &&
    typeof body === 'object' &&
    'error' in body &&
    typeof (body as Record<string, unknown>).error === 'object'
  ) {
    const err = (body as { error: Record<string, unknown> }).error
    if (typeof err?.code === 'string') {
      const message = typeof err.message === 'string' ? err.message : '알 수 없는 오류입니다.'
      return new BackendError(status, err.code, message)
    }
  }
  return new BackendError(status, 'UNKNOWN_ERROR', '서버와 통신하지 못했습니다.')
}

export function errorResponseBody(e: BackendError) {
  return { error: { code: e.code, message: e.message } }
}
```

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

Run: `cd www && npm test -- errors`
Expected: PASS (4 tests)

- [ ] **Step 6: 커밋**

```bash
git add www/src/server/backend/
git commit -m "feat(www): 계약 타입과 에러 변환 — code 로만 분기한다"
```

---

### Task 4: 백엔드 게이트웨이 인터페이스와 mock 구현

**Files:**
- Create: `www/src/server/backend/gateway.ts`
- Create: `www/src/server/backend/mock.ts`
- Create: `www/src/server/backend/index.ts`
- Test: `www/src/server/backend/mock.test.ts`

**Interfaces:**
- Consumes: Task 3의 `types.ts`, `errors.ts`
- Produces:
  - `interface Backend` — 아래 Step 1의 시그니처 그대로
  - `mockBackend: Backend`
  - `getBackend(): Backend` — `USE_MOCK`으로 고른다

- [ ] **Step 1: 인터페이스를 쓴다**

`www/src/server/backend/gateway.ts`:

```ts
import type { AuthToken, PlayerCard, PublicPlayerCard, SignupResult, User } from './types'

/**
 * FastAPI 와의 유일한 접점. Route Handler 만 이걸 쓴다.
 * 화면 코드는 이 타입을 보지 않는다 — 같은 오리진 /api/* 만 부른다.
 */
export interface Backend {
  signup(input: { email: string; password: string; nickname: string }): Promise<SignupResult>
  login(input: { email: string; password: string }): Promise<AuthToken>
  loginWithGoogle(input: { id_token: string }): Promise<AuthToken>
  getMe(token: string): Promise<User>
  updateMe(token: string, input: { nickname: string }): Promise<User>
  getMyCard(token: string): Promise<PlayerCard>
  getPublicCard(slug: string): Promise<PublicPlayerCard>
}
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`www/src/server/backend/mock.test.ts`:

```ts
import { mockBackend } from './mock'

describe('mockBackend', () => {
  it('데모 계정으로 로그인하면 토큰을 준다', async () => {
    const t = await mockBackend.login({
      email: 'demo@super-sub.example',
      password: 'supersub2026',
    })
    expect(t.access_token).toBeTruthy()
    expect(t.token_type).toBe('bearer')
    expect(t.expires_in).toBe(604800)
  })

  it('비밀번호가 틀리면 INVALID_CREDENTIALS 를 던진다', async () => {
    await expect(
      mockBackend.login({ email: 'demo@super-sub.example', password: '틀림' }),
    ).rejects.toMatchObject({ status: 401, code: 'INVALID_CREDENTIALS' })
  })

  it('없는 이메일도 INVALID_CREDENTIALS 다 — 가입 여부를 흘리지 않는다', async () => {
    await expect(
      mockBackend.login({ email: '없는사람@example.com', password: 'supersub2026' }),
    ).rejects.toMatchObject({ status: 401, code: 'INVALID_CREDENTIALS' })
  })

  it('가입하면 teams 없이 사용자를 돌려준다', async () => {
    const u = await mockBackend.signup({
      email: '새사람@example.com',
      password: 'supersub2026',
      nickname: '새사람',
    })
    expect(u.nickname).toBe('새사람')
    expect(u).not.toHaveProperty('teams')
  })

  it('이미 있는 이메일로 가입하면 EMAIL_ALREADY_EXISTS 다', async () => {
    await expect(
      mockBackend.signup({
        email: 'demo@super-sub.example',
        password: 'supersub2026',
        nickname: '중복',
      }),
    ).rejects.toMatchObject({ status: 409, code: 'EMAIL_ALREADY_EXISTS' })
  })

  it('토큰이 유효하지 않으면 getMe 가 INVALID_TOKEN 을 던진다', async () => {
    await expect(mockBackend.getMe('가짜토큰')).rejects.toMatchObject({
      status: 401,
      code: 'INVALID_TOKEN',
    })
  })

  it('닉네임을 바꾸면 GET /me 와 같은 형태를 돌려준다', async () => {
    const t = await mockBackend.login({
      email: 'demo@super-sub.example',
      password: 'supersub2026',
    })
    const u = await mockBackend.updateMe(t.access_token, { nickname: '바뀐이름' })
    expect(u.nickname).toBe('바뀐이름')
    expect(Array.isArray(u.teams)).toBe(true)
  })

  it('공개 카드는 인증 없이 조회된다', async () => {
    const c = await mockBackend.getPublicCard('hong-gildong-4f2a')
    expect(c.public_slug).toBe('hong-gildong-4f2a')
    expect(c).not.toHaveProperty('id')
  })

  it('없는 슬러그는 CARD_NOT_FOUND 다', async () => {
    await expect(mockBackend.getPublicCard('없는슬러그')).rejects.toMatchObject({
      status: 404,
      code: 'CARD_NOT_FOUND',
    })
  })

  it('카드에 수치 필드를 넣지 않는다', async () => {
    const c = await mockBackend.getPublicCard('hong-gildong-4f2a')
    const keys = Object.keys(c)
    expect(keys).not.toContain('score')
    expect(keys).not.toContain('rating')
    expect(keys).not.toContain('grade')
    for (const t of c.titles) {
      expect(t).not.toHaveProperty('earned')
    }
  })
})
```

- [ ] **Step 3: 테스트가 실패하는지 확인한다**

Run: `cd www && npm test -- mock`
Expected: FAIL — `./mock` 모듈이 없다.

- [ ] **Step 4: mock 을 구현한다**

`www/src/server/backend/mock.ts`. 값은 계약서 "눌러볼 수 있는 값" 절을 그대로 쓴다.

```ts
import { BackendError } from './errors'
import type { Backend } from './gateway'
import type { AuthToken, PlayerCard, PublicPlayerCard, SignupResult, User } from './types'

const DEMO_EMAIL = 'demo@super-sub.example'
const DEMO_PASSWORD = 'supersub2026'
const DEMO_TOKEN = 'mock-access-token-demo'
const EXPIRES_IN = 604800

/** 프로세스가 살아 있는 동안만 유지된다. mock 이므로 이걸로 충분하다. */
const users = new Map<string, User>([
  [
    DEMO_TOKEN,
    {
      id: '3f1c0000-0000-4000-8000-000000000001',
      email: DEMO_EMAIL,
      nickname: '홍길동',
      created_at: '2026-08-25T10:30:00Z',
      teams: [
        {
          team_id: '9a2e0000-0000-4000-8000-000000000002',
          name: '번개FC',
          region: '서울 강남',
          sport_code: 'futsal',
          role: 'member',
          joined_at: '2026-07-01T00:00:00Z',
        },
      ],
    },
  ],
])

const card: PlayerCard = {
  id: '7b4d0000-0000-4000-8000-000000000003',
  public_slug: 'hong-gildong-4f2a',
  og_image_key: 'cards/7b4d0000.png',
  user: { id: '3f1c0000-0000-4000-8000-000000000001', nickname: '홍길동' },
  titles: [
    {
      code: 'sharp_shooter',
      label: '슈팅이 매서운',
      category: '강점',
      granted_at: '2026-08-20T12:00:00Z',
    },
    {
      code: 'weekend_regular',
      label: '주말 개근',
      category: '활동',
      granted_at: '2026-08-01T09:00:00Z',
    },
  ],
}

function requireUser(token: string): User {
  const u = users.get(token)
  if (!u) throw new BackendError(401, 'INVALID_TOKEN', '다시 로그인해 주세요.')
  return u
}

export const mockBackend: Backend = {
  async signup({ email, password, nickname }) {
    if ([...users.values()].some((u) => u.email === email)) {
      throw new BackendError(409, 'EMAIL_ALREADY_EXISTS', '이미 가입된 이메일입니다.')
    }
    if (password.length < 8) {
      throw new BackendError(422, 'WEAK_PASSWORD', '비밀번호는 8자 이상이어야 합니다.')
    }
    const result: SignupResult = {
      id: `mock-${users.size + 1}`,
      email,
      nickname,
      created_at: '2026-08-28T00:00:00Z',
    }
    // 가입한 계정은 빈 상태로 온다 — 계약서가 강조하는 지점이다.
    users.set(`mock-access-token-${result.id}`, { ...result, teams: [] })
    return result
  },

  async login({ email, password }) {
    // 이메일이 없는 경우와 비밀번호가 틀린 경우를 구분하지 않는다.
    const entry = [...users.entries()].find(([, u]) => u.email === email)
    const ok = entry && (email !== DEMO_EMAIL || password === DEMO_PASSWORD)
    if (!entry || !ok || password.length < 8) {
      throw new BackendError(401, 'INVALID_CREDENTIALS', '이메일 또는 비밀번호가 올바르지 않습니다.')
    }
    return { access_token: entry[0], token_type: 'bearer', expires_in: EXPIRES_IN } as AuthToken
  },

  async loginWithGoogle() {
    return { access_token: DEMO_TOKEN, token_type: 'bearer', expires_in: EXPIRES_IN }
  },

  async getMe(token) {
    return requireUser(token)
  },

  async updateMe(token, { nickname }) {
    const u = requireUser(token)
    const trimmed = nickname.trim() // 서버가 정규화한다
    if (trimmed.length < 1 || trimmed.length > 20) {
      throw new BackendError(422, 'VALIDATION_ERROR', '요청 값이 올바르지 않습니다: nickname')
    }
    const next = { ...u, nickname: trimmed }
    users.set(token, next)
    return next
  },

  async getMyCard(token) {
    const u = requireUser(token)
    if (u.email !== DEMO_EMAIL) {
      // 가입만으로는 카드가 생기지 않는다.
      throw new BackendError(404, 'CARD_NOT_FOUND', '아직 선수 카드가 없습니다.')
    }
    return card
  },

  async getPublicCard(slug) {
    if (slug !== card.public_slug) {
      throw new BackendError(404, 'CARD_NOT_FOUND', '카드를 찾을 수 없습니다.')
    }
    const { id: _id, ...rest } = card
    return rest as PublicPlayerCard
  },
}
```

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

Run: `cd www && npm test -- mock`
Expected: PASS (10 tests)

- [ ] **Step 6: 스위치를 쓴다**

`www/src/server/backend/index.ts`:

```ts
import type { Backend } from './gateway'
import { mockBackend } from './mock'

/**
 * mock/실제 전환은 서버에서만 일어난다.
 * USE_MOCK 에 NEXT_PUBLIC_ 을 붙이지 않는다 — 클라이언트 번들에 박힌다.
 */
export function getBackend(): Backend {
  if (process.env.USE_MOCK === '1') return mockBackend
  // Task 11 에서 fastapiBackend 로 바꾼다.
  return mockBackend
}

export type { Backend } from './gateway'
export * from './types'
export { BackendError, errorResponseBody } from './errors'
```

- [ ] **Step 7: 커밋**

```bash
git add www/src/server/backend/
git commit -m "feat(www): 백엔드 게이트웨이 — 인터페이스 하나에 mock 구현"
```

---

### Task 5: 세션 쿠키와 인증 Route Handler

**Files:**
- Create: `www/src/server/session.ts`
- Create: `www/src/app/api/auth/login/route.ts`
- Create: `www/src/app/api/auth/signup/route.ts`
- Create: `www/src/app/api/auth/logout/route.ts`
- Test: `www/src/server/session.test.ts`
- Test: `www/src/app/api/auth/login/route.test.ts`

**Interfaces:**
- Consumes: Task 4의 `getBackend()`, Task 3의 `BackendError`/`errorResponseBody`
- Produces:
  - `SESSION_COOKIE = 'supersub_token'`
  - `readToken(req: NextRequest): string | null`
  - `setSession(res: NextResponse, token: string, maxAge: number): NextResponse`
  - `clearSession(res: NextResponse): NextResponse`
  - `POST /api/auth/login` · `POST /api/auth/signup` · `POST /api/auth/logout`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`cookies()`(`next/headers`) 대신 `NextRequest`/`NextResponse`의 쿠키 API만 쓴다 — 그래야 테스트에서 모킹 없이 검증된다.

`www/src/server/session.test.ts`:

```ts
import { NextRequest, NextResponse } from 'next/server'
import { SESSION_COOKIE, clearSession, readToken, setSession } from './session'

describe('세션 쿠키', () => {
  it('요청에서 토큰을 읽는다', () => {
    const req = new NextRequest('https://supersub-ai.com/api/me')
    req.cookies.set(SESSION_COOKIE, 'tok-1')
    expect(readToken(req)).toBe('tok-1')
  })

  it('쿠키가 없으면 null 이다', () => {
    const req = new NextRequest('https://supersub-ai.com/api/me')
    expect(readToken(req)).toBeNull()
  })

  it('httpOnly 로 심는다 — JS 가 읽지 못해야 한다', () => {
    const res = setSession(NextResponse.json({ ok: true }), 'tok-1', 604800)
    const c = res.cookies.get(SESSION_COOKIE)
    expect(c?.value).toBe('tok-1')
    expect(c?.httpOnly).toBe(true)
    expect(c?.sameSite).toBe('lax')
    expect(c?.maxAge).toBe(604800)
  })

  it('로그아웃하면 만료시킨다', () => {
    const res = clearSession(NextResponse.json({ ok: true }))
    expect(res.cookies.get(SESSION_COOKIE)?.maxAge).toBe(0)
  })
})
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd www && npm test -- session`
Expected: FAIL — `./session` 모듈이 없다.

- [ ] **Step 3: `session.ts` 를 구현한다**

`www/src/server/session.ts`:

```ts
import type { NextRequest, NextResponse } from 'next/server'

export const SESSION_COOKIE = 'supersub_token'

export function readToken(req: NextRequest): string | null {
  return req.cookies.get(SESSION_COOKIE)?.value ?? null
}

/**
 * 액세스 토큰을 httpOnly 쿠키에 심는다.
 *
 * 계약서상 refresh 토큰이 없어서 액세스 토큰 하나가 전부다. localStorage 에
 * 두면 XSS 한 번에 통째로 새고 만료 전까지 되돌릴 방법이 없다.
 */
export function setSession(res: NextResponse, token: string, maxAge: number): NextResponse {
  res.cookies.set(SESSION_COOKIE, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge,
  })
  return res
}

export function clearSession(res: NextResponse): NextResponse {
  res.cookies.set(SESSION_COOKIE, '', {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: 0,
  })
  return res
}
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run: `cd www && npm test -- session`
Expected: PASS (4 tests)

- [ ] **Step 5: Route Handler 의 실패하는 테스트를 쓴다**

`www/src/app/api/auth/login/route.test.ts`:

```ts
import { NextRequest } from 'next/server'
import { SESSION_COOKIE } from '@/server/session'
import { POST } from './route'

function post(body: unknown) {
  return new NextRequest('https://supersub-ai.com/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'content-type': 'application/json' },
  })
}

describe('POST /api/auth/login', () => {
  beforeAll(() => {
    process.env.USE_MOCK = '1'
  })

  it('성공하면 토큰을 본문이 아니라 쿠키에 담는다', async () => {
    const res = await POST(post({ email: 'demo@super-sub.example', password: 'supersub2026' }))
    expect(res.status).toBe(200)

    const cookie = res.cookies.get(SESSION_COOKIE)
    expect(cookie?.httpOnly).toBe(true)
    expect(cookie?.value).toBeTruthy()

    // 토큰이 응답 본문으로 새어 나가면 httpOnly 가 의미 없어진다.
    expect(JSON.stringify(await res.json())).not.toContain(cookie!.value)
  })

  it('비밀번호가 틀리면 401 INVALID_CREDENTIALS 를 그대로 넘긴다', async () => {
    const res = await POST(post({ email: 'demo@super-sub.example', password: '틀린비번' }))
    expect(res.status).toBe(401)
    expect(await res.json()).toEqual({
      error: { code: 'INVALID_CREDENTIALS', message: expect.any(String) },
    })
  })

  it('본문이 JSON 이 아니면 400 이다', async () => {
    const req = new NextRequest('https://supersub-ai.com/api/auth/login', {
      method: 'POST',
      body: 'not json',
      headers: { 'content-type': 'application/json' },
    })
    const res = await POST(req)
    expect(res.status).toBe(400)
  })
})
```

- [ ] **Step 6: 테스트가 실패하는지 확인한다**

Run: `cd www && npm test -- login`
Expected: FAIL — `./route` 모듈이 없다.

- [ ] **Step 7: 로그인 핸들러를 구현한다**

`www/src/app/api/auth/login/route.ts`:

```ts
import { NextResponse, type NextRequest } from 'next/server'
import { BackendError, errorResponseBody, getBackend } from '@/server/backend'
import { setSession } from '@/server/session'

export async function POST(req: NextRequest) {
  let body: { email?: string; password?: string }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json(
      { error: { code: 'BAD_REQUEST', message: '요청 형식이 잘못되었습니다.' } },
      { status: 400 },
    )
  }

  if (typeof body.email !== 'string' || typeof body.password !== 'string') {
    return NextResponse.json(
      { error: { code: 'BAD_REQUEST', message: '이메일과 비밀번호가 필요합니다.' } },
      { status: 400 },
    )
  }

  try {
    const token = await getBackend().login({ email: body.email, password: body.password })
    // 토큰은 본문에 담지 않는다. 쿠키로만 나간다.
    return setSession(NextResponse.json({ ok: true }), token.access_token, token.expires_in)
  } catch (e) {
    if (e instanceof BackendError) {
      return NextResponse.json(errorResponseBody(e), { status: e.status })
    }
    throw e
  }
}
```

- [ ] **Step 8: 테스트가 통과하는지 확인한다**

Run: `cd www && npm test -- login`
Expected: PASS (3 tests)

- [ ] **Step 9: 회원가입 핸들러를 구현한다**

`www/src/app/api/auth/signup/route.ts`:

```ts
import { NextResponse, type NextRequest } from 'next/server'
import { BackendError, errorResponseBody, getBackend } from '@/server/backend'

export async function POST(req: NextRequest) {
  let body: { email?: string; password?: string; nickname?: string }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json(
      { error: { code: 'BAD_REQUEST', message: '요청 형식이 잘못되었습니다.' } },
      { status: 400 },
    )
  }

  if (
    typeof body.email !== 'string' ||
    typeof body.password !== 'string' ||
    typeof body.nickname !== 'string'
  ) {
    return NextResponse.json(
      { error: { code: 'BAD_REQUEST', message: '이메일·비밀번호·닉네임이 필요합니다.' } },
      { status: 400 },
    )
  }

  try {
    const user = await getBackend().signup({
      email: body.email,
      password: body.password,
      nickname: body.nickname,
    })
    // 가입은 로그인이 아니다 — 세션을 심지 않는다. 화면이 로그인으로 보낸다.
    return NextResponse.json(user, { status: 201 })
  } catch (e) {
    if (e instanceof BackendError) {
      return NextResponse.json(errorResponseBody(e), { status: e.status })
    }
    throw e
  }
}
```

- [ ] **Step 10: 로그아웃 핸들러를 구현한다**

`www/src/app/api/auth/logout/route.ts`:

```ts
import { NextResponse } from 'next/server'
import { clearSession } from '@/server/session'

export async function POST() {
  return clearSession(NextResponse.json({ ok: true }))
}
```

- [ ] **Step 11: 전체 테스트를 돌린다**

Run: `cd www && npm test`
Expected: PASS (전부)

- [ ] **Step 12: 커밋**

```bash
git add www/src/server/session.ts www/src/app/api/auth/
git commit -m "feat(www): 세션은 httpOnly 쿠키에 — 토큰을 응답 본문에 담지 않는다"
```

---

### Task 6: 나머지 Route Handler (`/me`, `/me/card`, `/cards/[slug]`)

**Files:**
- Create: `www/src/server/handler.ts`
- Create: `www/src/app/api/me/route.ts`
- Create: `www/src/app/api/me/card/route.ts`
- Create: `www/src/app/api/cards/[slug]/route.ts`
- Test: `www/src/app/api/me/route.test.ts`

**Interfaces:**
- Consumes: Task 4의 `getBackend()`, Task 5의 `readToken`
- Produces:
  - `withAuth(req, fn)` — 쿠키가 없으면 401 `UNAUTHORIZED`, 있으면 `fn(token)` 실행
  - `toErrorResponse(e: unknown): NextResponse`
  - `GET/PATCH /api/me` · `GET /api/me/card` · `GET /api/cards/[slug]`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`www/src/app/api/me/route.test.ts`:

```ts
import { NextRequest } from 'next/server'
import { SESSION_COOKIE } from '@/server/session'
import { GET, PATCH } from './route'

const DEMO_TOKEN = 'mock-access-token-demo'

function req(method: string, token?: string, body?: unknown) {
  const r = new NextRequest('https://supersub-ai.com/api/me', {
    method,
    ...(body ? { body: JSON.stringify(body), headers: { 'content-type': 'application/json' } } : {}),
  })
  if (token) r.cookies.set(SESSION_COOKIE, token)
  return r
}

describe('/api/me', () => {
  beforeAll(() => {
    process.env.USE_MOCK = '1'
  })

  it('쿠키가 없으면 401 UNAUTHORIZED 다', async () => {
    const res = await GET(req('GET'))
    expect(res.status).toBe(401)
    expect((await res.json()).error.code).toBe('UNAUTHORIZED')
  })

  it('쿠키가 가짜면 401 INVALID_TOKEN 이다', async () => {
    const res = await GET(req('GET', '가짜'))
    expect(res.status).toBe(401)
    expect((await res.json()).error.code).toBe('INVALID_TOKEN')
  })

  it('로그인 상태면 사용자와 소속 팀을 준다', async () => {
    const res = await GET(req('GET', DEMO_TOKEN))
    expect(res.status).toBe(200)
    const u = await res.json()
    expect(u.email).toBe('demo@super-sub.example')
    expect(Array.isArray(u.teams)).toBe(true)
  })

  it('닉네임을 고치면 GET 과 같은 형태로 돌려준다', async () => {
    const res = await PATCH(req('PATCH', DEMO_TOKEN, { nickname: '새이름' }))
    expect(res.status).toBe(200)
    const u = await res.json()
    expect(u.nickname).toBe('새이름')
    expect(u).toHaveProperty('teams')
  })

  it('닉네임이 20자를 넘으면 422 VALIDATION_ERROR 다', async () => {
    const res = await PATCH(req('PATCH', DEMO_TOKEN, { nickname: '가'.repeat(21) }))
    expect(res.status).toBe(422)
    expect((await res.json()).error.code).toBe('VALIDATION_ERROR')
  })
})
```

> `UNAUTHORIZED`와 `INVALID_TOKEN`을 나눠 검사하는 이유는 클라이언트 동작이 다르기 때문이다 — 전자는 로그인 화면으로, 후자는 쿠키를 지우고 재로그인으로 보낸다.

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd www && npm test -- api/me`
Expected: FAIL — `./route` 모듈이 없다.

- [ ] **Step 3: 공용 헬퍼를 쓴다**

`www/src/server/handler.ts`:

```ts
import { NextResponse, type NextRequest } from 'next/server'
import { BackendError, errorResponseBody } from '@/server/backend'
import { readToken } from '@/server/session'

export function toErrorResponse(e: unknown): NextResponse {
  if (e instanceof BackendError) {
    return NextResponse.json(errorResponseBody(e), { status: e.status })
  }
  throw e
}

export async function withAuth(
  req: NextRequest,
  fn: (token: string) => Promise<NextResponse>,
): Promise<NextResponse> {
  const token = readToken(req)
  if (!token) {
    return NextResponse.json(
      { error: { code: 'UNAUTHORIZED', message: '로그인이 필요합니다.' } },
      { status: 401 },
    )
  }
  try {
    return await fn(token)
  } catch (e) {
    return toErrorResponse(e)
  }
}
```

- [ ] **Step 4: `/api/me` 를 구현한다**

`www/src/app/api/me/route.ts`:

```ts
import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

export async function GET(req: NextRequest) {
  return withAuth(req, async (token) => NextResponse.json(await getBackend().getMe(token)))
}

export async function PATCH(req: NextRequest) {
  return withAuth(req, async (token) => {
    let body: { nickname?: unknown }
    try {
      body = await req.json()
    } catch {
      return NextResponse.json(
        { error: { code: 'BAD_REQUEST', message: '요청 형식이 잘못되었습니다.' } },
        { status: 400 },
      )
    }
    if (typeof body.nickname !== 'string') {
      return NextResponse.json(
        { error: { code: 'VALIDATION_ERROR', message: '요청 값이 올바르지 않습니다: nickname' } },
        { status: 422 },
      )
    }
    return NextResponse.json(await getBackend().updateMe(token, { nickname: body.nickname }))
  })
}
```

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

Run: `cd www && npm test -- api/me`
Expected: PASS (5 tests)

- [ ] **Step 6: `/api/me/card` 를 구현한다**

`www/src/app/api/me/card/route.ts`:

```ts
import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

export async function GET(req: NextRequest) {
  return withAuth(req, async (token) => NextResponse.json(await getBackend().getMyCard(token)))
}
```

- [ ] **Step 7: `/api/cards/[slug]` 를 구현한다**

인증이 없다 — 공유용이다(SFR-009).

`www/src/app/api/cards/[slug]/route.ts`:

```ts
import { NextResponse } from 'next/server'
import { getBackend } from '@/server/backend'
import { toErrorResponse } from '@/server/handler'

export async function GET(_req: Request, ctx: { params: Promise<{ slug: string }> }) {
  const { slug } = await ctx.params
  try {
    return NextResponse.json(await getBackend().getPublicCard(slug))
  } catch (e) {
    return toErrorResponse(e)
  }
}
```

- [ ] **Step 8: 전체 테스트와 빌드를 돌린다**

Run: `cd www && npm test && npm run build`
Expected: 둘 다 성공

- [ ] **Step 9: 커밋**

```bash
git add www/src/server/handler.ts www/src/app/api/
git commit -m "feat(www): /me · /me/card · /cards/{slug} 중계 — UNAUTHORIZED 와 INVALID_TOKEN 을 나눈다"
```

---

### Task 7: 로그인·회원가입 화면

**Files:**
- Create: `www/src/lib/api/client.ts`
- Create: `www/src/app/login/page.tsx`
- Create: `www/src/app/signup/page.tsx`
- Test: `www/src/lib/api/client.test.ts`
- Test: `www/src/app/login/page.test.tsx`

**Interfaces:**
- Consumes: Task 5의 `/api/auth/login`, `/api/auth/signup`
- Produces: `apiPost<T>(path: string, body: unknown): Promise<T>` — 실패 시 `ApiCallError { code, message, status }`를 던진다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`www/src/lib/api/client.test.ts`:

```ts
import { ApiCallError, apiPost } from './client'

describe('apiPost', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('성공하면 본문을 돌려준다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
    )
    await expect(apiPost('/api/auth/logout', {})).resolves.toEqual({ ok: true })
  })

  it('실패하면 code 를 담은 에러를 던진다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({ error: { code: 'INVALID_CREDENTIALS', message: '틀렸습니다.' } }),
            { status: 401 },
          ),
      ),
    )
    await expect(apiPost('/api/auth/login', {})).rejects.toMatchObject({
      code: 'INVALID_CREDENTIALS',
      status: 401,
    })
  })

  it('네트워크가 끊기면 NETWORK_ERROR 다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('failed to fetch')
      }),
    )
    await expect(apiPost('/api/auth/login', {})).rejects.toBeInstanceOf(ApiCallError)
  })
})
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd www && npm test -- client`
Expected: FAIL — `./client` 모듈이 없다.

- [ ] **Step 3: 클라이언트를 구현한다**

`www/src/lib/api/client.ts`:

```ts
'use client'

export class ApiCallError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message)
    this.name = 'ApiCallError'
  }
}

/**
 * 같은 오리진의 /api/* 만 부른다. 브라우저는 FastAPI 주소를 모른다.
 * 쿠키는 same-origin 이라 자동으로 실린다.
 */
export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    })
  } catch {
    throw new ApiCallError(0, 'NETWORK_ERROR', '서버에 연결하지 못했습니다.')
  }

  const data = await res.json().catch(() => null)
  if (!res.ok) {
    const err = (data as { error?: { code?: string; message?: string } } | null)?.error
    throw new ApiCallError(
      res.status,
      err?.code ?? 'UNKNOWN_ERROR',
      err?.message ?? '알 수 없는 오류입니다.',
    )
  }
  return data as T
}
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run: `cd www && npm test -- client`
Expected: PASS (3 tests)

- [ ] **Step 5: 로그인 화면의 실패하는 테스트를 쓴다**

`www/src/app/login/page.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LoginPage from './page'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}))

describe('로그인 화면', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('이메일과 비밀번호 입력칸이 있다', () => {
    render(<LoginPage />)
    expect(screen.getByLabelText('이메일')).toBeInTheDocument()
    expect(screen.getByLabelText('비밀번호')).toBeInTheDocument()
  })

  it('실패하면 서버가 준 message 를 보여준다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              error: { code: 'INVALID_CREDENTIALS', message: '이메일 또는 비밀번호가 올바르지 않습니다.' },
            }),
            { status: 401 },
          ),
      ),
    )
    render(<LoginPage />)
    await userEvent.type(screen.getByLabelText('이메일'), 'a@b.com')
    await userEvent.type(screen.getByLabelText('비밀번호'), 'supersub2026')
    await userEvent.click(screen.getByRole('button', { name: '로그인' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      '이메일 또는 비밀번호가 올바르지 않습니다.',
    )
  })
})
```

`userEvent`가 없으면 설치한다: `npm i -D @testing-library/user-event`

- [ ] **Step 6: 테스트가 실패하는지 확인한다**

Run: `cd www && npm test -- login/page`
Expected: FAIL — `./page` 모듈이 없다.

- [ ] **Step 7: 로그인 화면을 구현한다**

`www/src/app/login/page.tsx`:

```tsx
'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { ApiCallError, apiPost } from '@/lib/api/client'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await apiPost('/api/auth/login', { email, password })
      router.push('/me')
      router.refresh()
    } catch (err) {
      // message 가 아니라 code 로 분기해야 할 곳이 생기면 여기서 나눈다.
      setError(err instanceof ApiCallError ? err.message : '알 수 없는 오류입니다.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-6 px-6">
      <h1 className="text-2xl font-bold">로그인</h1>
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1.5">
          <span className="text-sm text-neutral-500">이메일</span>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="rounded-lg border px-3 py-2"
          />
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="text-sm text-neutral-500">비밀번호</span>
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded-lg border px-3 py-2"
          />
        </label>
        {error && (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={busy}
          className="rounded-lg bg-neutral-900 px-4 py-2.5 text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
        >
          로그인
        </button>
      </form>
    </main>
  )
}
```

- [ ] **Step 8: 테스트가 통과하는지 확인한다**

Run: `cd www && npm test -- login/page`
Expected: PASS (2 tests)

- [ ] **Step 9: 회원가입 화면을 구현한다**

`www/src/app/signup/page.tsx` — 로그인과 같은 모양이되 닉네임이 붙고, 성공하면 `/login`으로 보낸다.

```tsx
'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { ApiCallError, apiPost } from '@/lib/api/client'

export default function SignupPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [nickname, setNickname] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await apiPost('/api/auth/signup', { email, password, nickname })
      // 가입은 로그인이 아니다. 세션이 없으니 로그인 화면으로 보낸다.
      router.push('/login')
    } catch (err) {
      setError(err instanceof ApiCallError ? err.message : '알 수 없는 오류입니다.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-6 px-6">
      <h1 className="text-2xl font-bold">회원가입</h1>
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1.5">
          <span className="text-sm text-neutral-500">이메일</span>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="rounded-lg border px-3 py-2"
          />
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="text-sm text-neutral-500">비밀번호</span>
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded-lg border px-3 py-2"
          />
          <span className="text-xs text-neutral-400">8자 이상</span>
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="text-sm text-neutral-500">닉네임</span>
          <input
            type="text"
            required
            minLength={1}
            maxLength={20}
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            className="rounded-lg border px-3 py-2"
          />
          <span className="text-xs text-neutral-400">1~20자</span>
        </label>
        {error && (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={busy}
          className="rounded-lg bg-neutral-900 px-4 py-2.5 text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
        >
          가입하기
        </button>
      </form>
    </main>
  )
}
```

- [ ] **Step 10: 전체 테스트를 돌린다**

Run: `cd www && npm test`
Expected: PASS (전부)

- [ ] **Step 11: 커밋**

```bash
git add www/src/lib/ www/src/app/login/ www/src/app/signup/
git commit -m "feat(www): 로그인·회원가입 화면 — 에러는 서버가 준 message 를 그대로 보여준다"
```

---

### Task 8: 프로필 화면과 닉네임 수정

**Files:**
- Create: `www/src/server/currentUser.ts`
- Create: `www/src/app/me/page.tsx`
- Create: `www/src/app/me/NicknameForm.tsx`
- Test: `www/src/app/me/NicknameForm.test.tsx`

**Interfaces:**
- Consumes: Task 6의 `/api/me`, Task 4의 `getBackend()`
- Produces: `requireUser(): Promise<User>` — 서버 컴포넌트에서 쓴다. 세션이 없거나 무효면 `/login`으로 redirect 한다

- [ ] **Step 1: 서버 컴포넌트용 사용자 조회를 쓴다**

여기서는 `cookies()`를 쓴다 — Route Handler가 아니라 서버 컴포넌트다.

`www/src/server/currentUser.ts`:

```ts
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import { BackendError, getBackend, type User } from '@/server/backend'
import { SESSION_COOKIE } from '@/server/session'

export async function requireUser(): Promise<User> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value
  if (!token) redirect('/login')

  try {
    return await getBackend().getMe(token)
  } catch (e) {
    // INVALID_TOKEN 이면 쿠키가 썩은 것이다. 로그인으로 보낸다.
    if (e instanceof BackendError && e.status === 401) redirect('/login')
    throw e
  }
}
```

- [ ] **Step 2: 닉네임 폼의 실패하는 테스트를 쓴다**

`www/src/app/me/NicknameForm.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import NicknameForm from './NicknameForm'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}))

describe('닉네임 수정', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('현재 닉네임이 입력칸에 들어 있다', () => {
    render(<NicknameForm nickname="홍길동" />)
    expect(screen.getByLabelText('닉네임')).toHaveValue('홍길동')
  })

  it('저장에 성공하면 알림을 보여준다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify({ nickname: '새이름' }), { status: 200 })),
    )
    render(<NicknameForm nickname="홍길동" />)
    await userEvent.clear(screen.getByLabelText('닉네임'))
    await userEvent.type(screen.getByLabelText('닉네임'), '새이름')
    await userEvent.click(screen.getByRole('button', { name: '저장' }))
    expect(await screen.findByRole('status')).toHaveTextContent('저장했습니다')
  })

  it('422 면 서버 message 를 보여준다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              error: { code: 'VALIDATION_ERROR', message: '요청 값이 올바르지 않습니다: nickname' },
            }),
            { status: 422 },
          ),
      ),
    )
    render(<NicknameForm nickname="홍길동" />)
    await userEvent.click(screen.getByRole('button', { name: '저장' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('nickname')
  })
})
```

- [ ] **Step 3: 테스트가 실패하는지 확인한다**

Run: `cd www && npm test -- NicknameForm`
Expected: FAIL — `./NicknameForm` 모듈이 없다.

- [ ] **Step 4: `apiPatch` 를 추가한다**

`www/src/lib/api/client.ts`에 붙인다. `apiPost`와 본문이 같으므로 메서드를 인자로 뺀다.

```ts
async function send<T>(method: 'POST' | 'PATCH', path: string, body: unknown): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, {
      method,
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    })
  } catch {
    throw new ApiCallError(0, 'NETWORK_ERROR', '서버에 연결하지 못했습니다.')
  }

  const data = await res.json().catch(() => null)
  if (!res.ok) {
    const err = (data as { error?: { code?: string; message?: string } } | null)?.error
    throw new ApiCallError(
      res.status,
      err?.code ?? 'UNKNOWN_ERROR',
      err?.message ?? '알 수 없는 오류입니다.',
    )
  }
  return data as T
}

export const apiPost = <T>(path: string, body: unknown) => send<T>('POST', path, body)
export const apiPatch = <T>(path: string, body: unknown) => send<T>('PATCH', path, body)
```

기존 `apiPost` 본문은 지운다. Task 7의 `client.test.ts`가 계속 통과해야 한다.

- [ ] **Step 5: 닉네임 폼을 구현한다**

`www/src/app/me/NicknameForm.tsx`:

```tsx
'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { ApiCallError, apiPatch } from '@/lib/api/client'

export default function NicknameForm({ nickname }: { nickname: string }) {
  const router = useRouter()
  const [value, setValue] = useState(nickname)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSaved(false)
    setBusy(true)
    try {
      await apiPatch('/api/me', { nickname: value })
      setSaved(true)
      router.refresh()
    } catch (err) {
      setError(err instanceof ApiCallError ? err.message : '알 수 없는 오류입니다.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-3">
      <label className="flex flex-col gap-1.5">
        <span className="text-sm text-neutral-500">닉네임</span>
        <input
          type="text"
          minLength={1}
          maxLength={20}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="rounded-lg border px-3 py-2"
        />
      </label>
      {error && (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}
      {saved && (
        <p role="status" className="text-sm text-green-600">
          저장했습니다.
        </p>
      )}
      <button
        type="submit"
        disabled={busy}
        className="self-start rounded-lg border px-4 py-2 disabled:opacity-50"
      >
        저장
      </button>
    </form>
  )
}
```

- [ ] **Step 6: 테스트가 통과하는지 확인한다**

Run: `cd www && npm test -- NicknameForm`
Expected: PASS (3 tests)

- [ ] **Step 7: 프로필 화면을 구현한다**

`www/src/app/me/page.tsx` — 서버 컴포넌트다.

```tsx
import Link from 'next/link'
import { requireUser } from '@/server/currentUser'
import NicknameForm from './NicknameForm'

export default async function MePage() {
  const user = await requireUser()

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-10 px-6 py-16">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">{user.nickname}</h1>
        <p className="text-sm text-neutral-500">{user.email}</p>
      </header>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">프로필</h2>
        <NicknameForm nickname={user.nickname} />
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">소속 팀</h2>
        {user.teams.length === 0 ? (
          <p className="text-sm text-neutral-500">아직 소속된 팀이 없습니다.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {user.teams.map((t) => (
              <li key={t.team_id} className="rounded-lg border px-4 py-3">
                <p className="font-medium">{t.name}</p>
                <p className="text-sm text-neutral-500">
                  {t.region} · {t.sport_code}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <Link href="/me/card" className="text-sm underline">
        내 선수 카드 보기 →
      </Link>
    </main>
  )
}
```

> 새 계정은 `teams`가 **빈 배열**로 온다 — 계약서가 강조하는 자리다. 빈 상태를 반드시 그린다.

- [ ] **Step 8: 전체 테스트와 빌드를 돌린다**

Run: `cd www && npm test && npm run build`
Expected: 둘 다 성공

- [ ] **Step 9: 커밋**

```bash
git add www/src/server/currentUser.ts www/src/app/me/ www/src/lib/api/client.ts
git commit -m "feat(www): 프로필 화면 — 닉네임 수정과 빈 소속 팀 상태"
```

---

### Task 9: 선수 카드 — 내 카드와 공개 카드

**Files:**
- Create: `www/src/app/me/card/page.tsx`
- Create: `www/src/components/PlayerCardView.tsx`
- Create: `www/src/app/c/[slug]/page.tsx`
- Test: `www/src/components/PlayerCardView.test.tsx`

**Interfaces:**
- Consumes: Task 4의 `getBackend()`, Task 3의 `PublicPlayerCard`/`Title`
- Produces: `<PlayerCardView card={{ public_slug, user, titles }} />`

**결정 사항 — `og_image_key`를 쓰지 않는다.** 계약서의 `og_image_key`는 `cards/7b4d....png` 같은 스토리지 키인데, **어느 스토리지의 어떤 베이스 URL인지가 아직 정해지지 않았다.** 정해질 때까지 Next.js가 카드 데이터로 이미지를 직접 그린다. 베이스 URL이 정해지면 그때 바꾼다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`www/src/components/PlayerCardView.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import PlayerCardView from './PlayerCardView'

const card = {
  public_slug: 'hong-gildong-4f2a',
  og_image_key: 'cards/7b4d.png',
  user: { id: '3f1c', nickname: '홍길동' },
  titles: [
    { code: 'sharp_shooter', label: '슈팅이 매서운', category: '강점', granted_at: '2026-08-20T12:00:00Z' },
    { code: 'weekend_regular', label: '주말 개근', category: '활동', granted_at: '2026-08-01T09:00:00Z' },
  ],
}

describe('선수 카드', () => {
  it('닉네임과 받은 호칭을 보여준다', () => {
    render(<PlayerCardView card={card} />)
    expect(screen.getByRole('heading', { name: '홍길동' })).toBeInTheDocument()
    expect(screen.getByText('슈팅이 매서운')).toBeInTheDocument()
    expect(screen.getByText('주말 개근')).toBeInTheDocument()
  })

  it('호칭이 없으면 빈 상태를 보여준다', () => {
    render(<PlayerCardView card={{ ...card, titles: [] }} />)
    expect(screen.getByText(/아직 받은 호칭이 없습니다/)).toBeInTheDocument()
  })

  it('수치를 그리지 않는다 — 점수·등급·별점이 없어야 한다', () => {
    const { container } = render(<PlayerCardView card={card} />)
    expect(container.textContent).not.toMatch(/[0-9]+\s*점/)
    expect(container.textContent).not.toMatch(/등급/)
    expect(container.querySelector('progress')).toBeNull()
    expect(container.querySelector('meter')).toBeNull()
  })
})
```

> 세 번째 테스트가 계약서 4절(부록 D.5)을 코드로 못 박는 자리다. 카드에 수치가 되살아나면 설계가 무의미해진다.

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd www && npm test -- PlayerCardView`
Expected: FAIL — `./PlayerCardView` 모듈이 없다.

- [ ] **Step 3: 카드 컴포넌트를 구현한다**

`www/src/components/PlayerCardView.tsx`:

```tsx
import type { PublicPlayerCard } from '@/server/backend'

/**
 * 수치를 그리지 않는다 (계약서 4절 / 부록 D.5).
 * 점수·등급·별점·진행률 바를 여기에 넣지 않는다.
 * titles 는 받은 것만 온다 — 미달 표식을 만들지 않는다.
 */
export default function PlayerCardView({ card }: { card: PublicPlayerCard }) {
  return (
    <article className="rounded-2xl border p-8">
      <h1 className="text-3xl font-bold">{card.user.nickname}</h1>

      <h2 className="mt-8 text-sm font-semibold text-neutral-500">호칭</h2>
      {card.titles.length === 0 ? (
        <p className="mt-2 text-sm text-neutral-500">아직 받은 호칭이 없습니다.</p>
      ) : (
        <ul className="mt-3 flex flex-wrap gap-2">
          {card.titles.map((t) => (
            <li key={t.code} className="rounded-full border px-3 py-1.5 text-sm">
              <span className="mr-1.5 text-xs text-neutral-400">{t.category}</span>
              {t.label}
            </li>
          ))}
        </ul>
      )}
    </article>
  )
}
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run: `cd www && npm test -- PlayerCardView`
Expected: PASS (3 tests)

- [ ] **Step 5: 공개 카드 페이지를 구현한다**

`www/src/app/c/[slug]/page.tsx` — 인증 없이 서버 렌더링한다. `generateMetadata`가 공유 미리보기를 만든다.

```tsx
import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import PlayerCardView from '@/components/PlayerCardView'
import { BackendError, getBackend, type PublicPlayerCard } from '@/server/backend'

async function load(slug: string): Promise<PublicPlayerCard | null> {
  try {
    return await getBackend().getPublicCard(slug)
  } catch (e) {
    if (e instanceof BackendError && e.status === 404) return null
    throw e
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>
}): Promise<Metadata> {
  const { slug } = await params
  const card = await load(slug)
  if (!card) return { title: '카드를 찾을 수 없습니다 · Super-Sub' }

  const title = `${card.user.nickname} · Super-Sub`
  const description =
    card.titles.length > 0
      ? card.titles.map((t) => t.label).join(' · ')
      : '생활체육 선수 카드'

  return {
    title,
    description,
    openGraph: { title, description, type: 'profile' },
    twitter: { card: 'summary_large_image', title, description },
  }
}

export default async function PublicCardPage({
  params,
}: {
  params: Promise<{ slug: string }>
}) {
  const { slug } = await params
  const card = await load(slug)
  if (!card) notFound()

  return (
    <main className="mx-auto max-w-xl px-6 py-16">
      <PlayerCardView card={card} />
    </main>
  )
}
```

- [ ] **Step 6: 내 카드 페이지를 구현한다**

`www/src/app/me/card/page.tsx` — 404 `CARD_NOT_FOUND`를 빈 상태로 그린다. 계약서가 "카드는 가입만으로 생기지 않는다"고 못 박은 자리다.

```tsx
import Link from 'next/link'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import PlayerCardView from '@/components/PlayerCardView'
import { BackendError, getBackend, type PlayerCard } from '@/server/backend'
import { SESSION_COOKIE } from '@/server/session'

export default async function MyCardPage() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value
  if (!token) redirect('/login')

  let card: PlayerCard | null = null
  try {
    card = await getBackend().getMyCard(token)
  } catch (e) {
    if (e instanceof BackendError && e.status === 401) redirect('/login')
    if (!(e instanceof BackendError && e.code === 'CARD_NOT_FOUND')) throw e
  }

  return (
    <main className="mx-auto max-w-xl px-6 py-16">
      {card ? (
        <>
          <PlayerCardView card={card} />
          <p className="mt-6 text-sm text-neutral-500">
            공유 링크:{' '}
            <Link href={`/c/${card.public_slug}`} className="underline">
              /c/{card.public_slug}
            </Link>
          </p>
        </>
      ) : (
        <div className="rounded-2xl border p-8">
          <h1 className="text-xl font-semibold">아직 선수 카드가 없습니다</h1>
          <p className="mt-2 text-sm text-neutral-500">
            경기 영상이 분석되면 카드가 만들어집니다.
          </p>
        </div>
      )}
      <Link href="/me" className="mt-8 inline-block text-sm underline">
        ← 프로필로
      </Link>
    </main>
  )
}
```

- [ ] **Step 7: 전체 테스트와 빌드를 돌린다**

Run: `cd www && npm test && npm run build`
Expected: 둘 다 성공

- [ ] **Step 8: 손으로 확인한다**

```bash
cd www && USE_MOCK=1 npm run dev
```

- `/c/hong-gildong-4f2a` → 카드가 뜬다
- `/c/없는슬러그` → 404 페이지
- 페이지 소스에서 `og:title`이 `홍길동 · Super-Sub` 인지 확인

- [ ] **Step 9: 커밋**

```bash
git add www/src/components/ www/src/app/c/ www/src/app/me/card/
git commit -m "feat(www): 선수 카드 — 공개 링크와 공유 미리보기, 수치는 그리지 않는다"
```

- [ ] **Step 10: 배포하고 도메인에서 확인한다**

```bash
cd www && vercel --prod
```

`https://supersub-ai.com/c/hong-gildong-4f2a` 에서 카드가 뜨는지 확인한다.

---

### Task 10: 영상 분석 자리 화면

설계 문서의 라우트 표에 있는 `/analysis` 다. **백엔드 API가 없으므로 기능을 만들지 않는다** — 자리와 "준비 중"만 정직하게 그린다. 그럴듯한 가짜 분석 결과를 그리지 않는다. 데모에서 진짜로 오해받고, 계약서 4절이 금지한 수치가 화면에 되살아나는 통로가 된다.

**Files:**
- Create: `www/src/app/analysis/page.tsx`
- Test: `www/src/app/analysis/page.test.tsx`

**Interfaces:**
- Consumes: 없음
- Produces: `AnalysisBody` — 이름있는 export. 나중에 인증을 씌울 때 기본 export 만 바꾸면 되도록 분리해 둔다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`www/src/app/analysis/page.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import AnalysisBody from './page'

describe('영상 분석 화면', () => {
  it('준비 중임을 밝힌다', () => {
    render(<AnalysisBody />)
    expect(screen.getByText(/준비 중/)).toBeInTheDocument()
  })

  it('가짜 분석 결과를 그리지 않는다 — 수치가 없어야 한다', () => {
    const { container } = render(<AnalysisBody />)
    expect(container.textContent).not.toMatch(/[0-9]+\s*(점|%)/)
    expect(container.querySelector('progress')).toBeNull()
    expect(container.querySelector('meter')).toBeNull()
  })
})
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd www && npm test -- analysis`
Expected: FAIL — `./page` 모듈이 없다.

- [ ] **Step 3: 구현한다**

보여줄 개인 정보가 없으므로 인증을 걸지 않는다. 그래서 서버 컴포넌트가 아니라 순수 함수 컴포넌트이고, 테스트가 그대로 렌더할 수 있다.

`www/src/app/analysis/page.tsx`:

```tsx
import Link from 'next/link'

export function AnalysisBody() {
  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <h1 className="text-2xl font-bold">영상 분석</h1>
      <div className="mt-6 rounded-2xl border border-dashed p-8">
        <p className="font-medium">준비 중입니다.</p>
        <p className="mt-2 text-sm text-neutral-500">
          경기 영상을 올려 분석하는 기능은 백엔드 작업이 끝나면 열립니다.
        </p>
      </div>
      <Link href="/me" className="mt-8 inline-block text-sm underline">
        ← 프로필로
      </Link>
    </main>
  )
}

export default AnalysisBody
```

> 나중에 로그인 확인이 필요해지면 기본 export 만 서버 컴포넌트로 바꾼다 — `export default async function Page() { await requireUser(); return <AnalysisBody /> }`. 그때 Task 8 의 `requireUser` 를 가져온다. `AnalysisBody` 는 그대로 두면 테스트도 그대로 산다.

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run: `cd www && npm test -- analysis`
Expected: PASS (2 tests)

- [ ] **Step 5: 커밋**

```bash
git add www/src/app/analysis/
git commit -m "feat(www): 영상 분석 자리 화면 — 가짜 결과를 그리지 않는다"
```

---

### Task 11: FastAPI 구현체 연결

백엔드가 배포된 뒤에 한다. 그전에도 코드는 쓸 수 있고, `fetch`를 스텁해서 테스트한다.

**Files:**
- Create: `www/src/server/backend/fastapi.ts`
- Modify: `www/src/server/backend/index.ts`
- Test: `www/src/server/backend/fastapi.test.ts`

**Interfaces:**
- Consumes: Task 4의 `Backend` 인터페이스, Task 3의 `parseErrorBody`
- Produces: `fastapiBackend: Backend`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`www/src/server/backend/fastapi.test.ts`:

```ts
import { fastapiBackend } from './fastapi'

describe('fastapiBackend', () => {
  beforeEach(() => {
    process.env.BACKEND_BASE_URL = 'http://127.0.0.1:8000/api/v1'
  })
  afterEach(() => vi.unstubAllGlobals())

  it('로그인은 /auth/login 으로 POST 한다', async () => {
    const fetchMock = vi.fn(
      async () =>
        new Response(
          JSON.stringify({ access_token: 'tok', token_type: 'bearer', expires_in: 604800 }),
          { status: 200 },
        ),
    )
    vi.stubGlobal('fetch', fetchMock)

    const t = await fastapiBackend.login({ email: 'a@b.com', password: 'supersub2026' })
    expect(t.access_token).toBe('tok')

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('http://127.0.0.1:8000/api/v1/auth/login')
    expect(init.method).toBe('POST')
  })

  it('인증이 필요한 호출에 Bearer 헤더를 붙인다', async () => {
    const fetchMock = vi.fn(
      async () => new Response(JSON.stringify({ id: '1', teams: [] }), { status: 200 }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await fastapiBackend.getMe('tok-1')
    const [, init] = fetchMock.mock.calls[0]
    expect(init.headers.Authorization).toBe('Bearer tok-1')
  })

  it('에러 응답을 BackendError 로 바꾼다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({ error: { code: 'CARD_NOT_FOUND', message: '없습니다.' } }),
            { status: 404 },
          ),
      ),
    )
    await expect(fastapiBackend.getPublicCard('없음')).rejects.toMatchObject({
      status: 404,
      code: 'CARD_NOT_FOUND',
    })
  })

  it('백엔드가 HTML 을 뱉어도 던지지 않고 UNKNOWN_ERROR 로 떨어진다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('<html>502</html>', { status: 502 })),
    )
    await expect(fastapiBackend.getPublicCard('x')).rejects.toMatchObject({
      code: 'UNKNOWN_ERROR',
    })
  })
})
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd www && npm test -- fastapi`
Expected: FAIL — `./fastapi` 모듈이 없다.

- [ ] **Step 3: 구현한다**

`www/src/server/backend/fastapi.ts`:

```ts
import { parseErrorBody } from './errors'
import type { Backend } from './gateway'
import type { AuthToken, PlayerCard, PublicPlayerCard, SignupResult, User } from './types'

function baseUrl(): string {
  return process.env.BACKEND_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'
}

async function call<T>(
  path: string,
  init: { method?: string; token?: string; body?: unknown } = {},
): Promise<T> {
  const headers: Record<string, string> = { 'content-type': 'application/json' }
  if (init.token) headers.Authorization = `Bearer ${init.token}`

  const res = await fetch(`${baseUrl()}${path}`, {
    method: init.method ?? 'GET',
    headers,
    ...(init.body !== undefined ? { body: JSON.stringify(init.body) } : {}),
    cache: 'no-store',
  })

  const data = await res.json().catch(() => null)
  if (!res.ok) throw parseErrorBody(res.status, data)
  return data as T
}

export const fastapiBackend: Backend = {
  signup: (input) => call<SignupResult>('/auth/signup', { method: 'POST', body: input }),
  login: (input) => call<AuthToken>('/auth/login', { method: 'POST', body: input }),
  loginWithGoogle: (input) => call<AuthToken>('/auth/google', { method: 'POST', body: input }),
  getMe: (token) => call<User>('/me', { token }),
  updateMe: (token, input) => call<User>('/me', { method: 'PATCH', token, body: input }),
  getMyCard: (token) => call<PlayerCard>('/me/card', { token }),
  getPublicCard: (slug) => call<PublicPlayerCard>(`/cards/${encodeURIComponent(slug)}`),
}
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run: `cd www && npm test -- fastapi`
Expected: PASS (4 tests)

- [ ] **Step 5: 스위치를 연결한다**

`www/src/server/backend/index.ts`의 `getBackend()`를 고친다:

```ts
import type { Backend } from './gateway'
import { fastapiBackend } from './fastapi'
import { mockBackend } from './mock'

export function getBackend(): Backend {
  return process.env.USE_MOCK === '1' ? mockBackend : fastapiBackend
}

export type { Backend } from './gateway'
export * from './types'
export { BackendError, errorResponseBody } from './errors'
```

- [ ] **Step 6: 로컬 백엔드에 붙여 확인한다**

FastAPI를 띄운다 (`fastapi/` 참고):

```bash
cd fastapi && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

다른 셸에서:

```bash
cd www && USE_MOCK=0 BACKEND_BASE_URL=http://127.0.0.1:8000/api/v1 npm run dev
```

`demo@super-sub.example` / `supersub2026` 으로 로그인해 `/me`와 `/me/card`가 뜨는지 확인한다.

- [ ] **Step 7: 전체 테스트와 빌드를 돌린다**

Run: `cd www && npm test && npm run build`
Expected: 둘 다 성공

- [ ] **Step 8: 커밋**

```bash
git add www/src/server/backend/
git commit -m "feat(www): FastAPI 구현체 연결 — USE_MOCK 으로 갈아끼운다"
```

---

## 이 계획에 넣지 않은 것

- **영상 분석 기능 자체** — 백엔드 API가 없다(계약서 5절). Task 10 은 "준비 중" 자리만 그린다. API 가 생기면 별도 계획으로 붙인다.
- **구글 로그인 화면** — `POST /auth/google`은 계약에 있고 `loginWithGoogle`도 게이트웨이에 넣어 뒀지만, 웹용 구글 클라이언트 설정(승인된 자바스크립트 원본에 `supersub-ai.com` 등록)이 남아 있다. 배포 후 별도로 붙인다.
- **토큰 갱신** — 백엔드에 `POST /auth/refresh`가 없다.
- **팀/스카우팅 검색** — 계약에 없다.
- **다국어**
