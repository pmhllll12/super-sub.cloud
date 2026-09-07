import { NextRequest } from 'next/server'
import { SESSION_COOKIE } from '@/server/session'
import { POST } from './route'

const DEMO_TOKEN = 'mock-access-token-demo'

function req(token: string | undefined, body: unknown) {
  const r = new NextRequest('https://supersub-ai.com/api/chat', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'content-type': 'application/json' },
  })
  if (token) r.cookies.set(SESSION_COOKIE, token)
  return r
}

/**
 * 실제 LLM 왕복(도구 호출)까지는 여기서 검증하지 않는다 — 이 시험은 라우트
 * 자체의 로직(인증·검증·비용 절약 지름길·설정 게이트)만 본다. LLM 호출은
 * `GEMINI_API_KEY`가 있어야 도달하는 자리라 CI에서 안전하게 못 돌린다.
 */
describe('POST /api/chat', () => {
  const originalKey = process.env.GEMINI_API_KEY

  beforeAll(() => {
    process.env.USE_MOCK = '1'
  })

  afterEach(() => {
    if (originalKey === undefined) delete process.env.GEMINI_API_KEY
    else process.env.GEMINI_API_KEY = originalKey
  })

  it('쿠키가 없으면 401 UNAUTHORIZED 다', async () => {
    const res = await POST(req(undefined, { message: '안녕' }))
    expect(res.status).toBe(401)
    expect((await res.json()).error.code).toBe('UNAUTHORIZED')
  })

  it('message 가 없으면 422 VALIDATION_ERROR 다', async () => {
    const res = await POST(req(DEMO_TOKEN, {}))
    expect(res.status).toBe(422)
    expect((await res.json()).error.code).toBe('VALIDATION_ERROR')
  })

  it('주장인 팀이 없으면 LLM을 부르지 않고 바로 안내한다 (API 키 없어도 됨)', async () => {
    delete process.env.GEMINI_API_KEY
    const { mockBackend } = await import('@/server/backend/mock')
    const fresh = await mockBackend.signup({
      email: `no-team-${Date.now()}@example.com`,
      password: 'supersub2026',
      nickname: '팀없음',
    })
    const t = await mockBackend.login({ email: fresh.email, password: 'supersub2026' })

    const res = await POST(req(t.access_token, { message: '경기 등록하고 싶어요' }))
    expect(res.status).toBe(200)
    const body = await res.json()
    expect(body.reply).toContain('먼저 팀을 만들어')
    expect(body.proposal).toBeNull()
  })

  it('팀이 있는데 GEMINI_API_KEY 가 없으면 503 CHAT_NOT_CONFIGURED 다', async () => {
    delete process.env.GEMINI_API_KEY
    const res = await POST(req(DEMO_TOKEN, { message: '경기 등록하고 싶어요' }))
    expect(res.status).toBe(503)
    expect((await res.json()).error.code).toBe('CHAT_NOT_CONFIGURED')
  })
})
