import { NextRequest } from 'next/server'
import { SESSION_COOKIE } from '@/server/session'
import { POST as signup } from '../../auth/signup/route'
import { POST as login } from '../../auth/login/route'
import { GET } from './route'

const DEMO_TOKEN = 'mock-access-token-demo'
const DEMO_EMAIL = 'demo@super-sub.example'

function req(token?: string, query = '') {
  const r = new NextRequest(`https://supersub-ai.com/api/admin/videos${query}`)
  if (token) r.cookies.set(SESSION_COOKIE, token)
  return r
}

async function nonAdminToken(): Promise<string> {
  const email = `member-${Date.now()}@super-sub.example`
  await signup(
    new NextRequest('https://supersub-ai.com/api/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password: 'password123', nickname: '일반회원' }),
      headers: { 'content-type': 'application/json' },
    }),
  )
  const res = await login(
    new NextRequest('https://supersub-ai.com/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password: 'password123' }),
      headers: { 'content-type': 'application/json' },
    }),
  )
  return res.cookies.get(SESSION_COOKIE)!.value
}

describe('GET /api/admin/videos', () => {
  beforeAll(() => {
    process.env.USE_MOCK = '1'
  })

  it('쿠키가 없으면 401 UNAUTHORIZED 다', async () => {
    const res = await GET(req())
    expect(res.status).toBe(401)
    expect((await res.json()).error.code).toBe('UNAUTHORIZED')
  })

  it('관리자가 아니면 403 FORBIDDEN 이다', async () => {
    const token = await nonAdminToken()
    const res = await GET(req(token, `?user=${DEMO_EMAIL}`))
    expect(res.status).toBe(403)
    expect((await res.json()).error.code).toBe('FORBIDDEN')
  })

  it('없는 사람이면 404 USER_NOT_FOUND 다', async () => {
    const res = await GET(req(DEMO_TOKEN, '?user=nobody@super-sub.example'))
    expect(res.status).toBe(404)
    expect((await res.json()).error.code).toBe('USER_NOT_FOUND')
  })

  it('관리자면 그 사람의 영상 목록을 준다 — 실패 사유도 함께', async () => {
    const res = await GET(req(DEMO_TOKEN, `?user=${DEMO_EMAIL}`))
    expect(res.status).toBe(200)
    const body = await res.json()
    expect(body.email).toBe(DEMO_EMAIL)
    expect(body.items.length).toBeGreaterThan(0)
    // 허용목록: 실패 사유가 있는 항목이면 문자열, 아니면 null.
    for (const item of body.items) {
      expect(['string', 'object']).toContain(typeof item.analysis_failure_reason)
    }
  })
})
