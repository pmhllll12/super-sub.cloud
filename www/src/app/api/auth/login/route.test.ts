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

/**
 * 🔴 **`Retry-After` 가 브라우저까지 와야 한다** — 계약 1번(SEC-009),
 * 미결 `jin` 2번.
 *
 * `www` 는 프록시라 헤더가 세 곳을 지나는데 **중간에서 끊기고 있었다**
 * (2026-09-01 정어진 확인). 그러면 화면은 얼마나 기다릴지 몰라 임의의 상수를
 * 쓰게 된다 — 남은 시간은 대부분 그보다 짧다.
 *
 * 여기서는 **BFF 한 층**(백엔드 응답 → 우리 응답)만 붙든다. 진짜 FastAPI 를
 * 세우지 않고 `BACKEND_BASE_URL` 로 가는 fetch 를 대역으로 바꾼다.
 */
describe('POST /api/auth/login — 429 Retry-After', () => {
  const prevMock = process.env.USE_MOCK
  const prevBase = process.env.BACKEND_BASE_URL

  beforeEach(() => {
    // mock 백엔드에는 제한이 없다 — 진짜 갈래(fastapiBackend)를 타야 한다.
    delete process.env.USE_MOCK
    process.env.BACKEND_BASE_URL = 'https://backend.test'
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    if (prevMock === undefined) delete process.env.USE_MOCK
    else process.env.USE_MOCK = prevMock
    if (prevBase === undefined) delete process.env.BACKEND_BASE_URL
    else process.env.BACKEND_BASE_URL = prevBase
  })

  function backendSays(headers: Record<string, string>) {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              error: { code: 'TOO_MANY_REQUESTS', message: '요청이 너무 잦습니다.' },
            }),
            { status: 429, headers },
          ),
      ),
    )
  }

  it('백엔드가 준 Retry-After 를 그대로 다시 싣는다', async () => {
    backendSays({ 'Retry-After': '37' })
    const res = await POST(post({ email: 'a@b.com', password: 'supersub2026' }))
    expect(res.status).toBe(429)
    expect(res.headers.get('retry-after')).toBe('37')
    expect((await res.json()).error.code).toBe('TOO_MANY_REQUESTS')
  })

  /* 🔴 **없는 헤더를 지어내지 않는다.** 0 을 싣으면 화면이 곧바로 다시
     보내도 된다고 읽는다 — 그게 이 항목이 막으려는 것이다. */
  it('백엔드가 안 주면 우리도 안 싣는다', async () => {
    backendSays({})
    const res = await POST(post({ email: 'a@b.com', password: 'supersub2026' }))
    expect(res.status).toBe(429)
    expect(res.headers.get('retry-after')).toBeNull()
  })

  /* ⚠️ 계약은 **정수 초**로 정했다. HTTP 가 허용하는 날짜 형식이 오면 못 읽은
     것으로 치고 넘어간다 — 잘못 읽어 0 으로 만드는 쪽이 더 나쁘다. */
  it('날짜 형식이면 못 읽은 것으로 치고 안 싣는다', async () => {
    backendSays({ 'Retry-After': 'Wed, 21 Oct 2026 07:28:00 GMT' })
    const res = await POST(post({ email: 'a@b.com', password: 'supersub2026' }))
    expect(res.headers.get('retry-after')).toBeNull()
  })
})
