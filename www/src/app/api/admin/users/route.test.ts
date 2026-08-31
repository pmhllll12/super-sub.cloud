import { NextRequest } from 'next/server'
import { SESSION_COOKIE } from '@/server/session'
import { POST as signup } from '../../auth/signup/route'
import { POST as login } from '../../auth/login/route'
import { GET } from './route'

const DEMO_TOKEN = 'mock-access-token-demo'

function req(token?: string, query = '') {
  const r = new NextRequest(`https://supersub-ai.com/api/admin/users${query}`)
  if (token) r.cookies.set(SESSION_COOKIE, token)
  return r
}

/** 관리자가 아닌 회원 하나를 만들고 로그인해 그 토큰을 돌려준다. */
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

describe('GET /api/admin/users', () => {
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
    const res = await GET(req(token))
    expect(res.status).toBe(403)
    expect((await res.json()).error.code).toBe('FORBIDDEN')
  })

  it('관리자면 회원 목록을 준다', async () => {
    const res = await GET(req(DEMO_TOKEN))
    expect(res.status).toBe(200)
    const body = await res.json()
    expect(body.items.some((u: { email: string }) => u.email === 'demo@super-sub.example')).toBe(
      true,
    )
    expect(body.page).toBe(1)
  })

  it('q 로 거르면 안 맞는 회원은 안 나온다', async () => {
    const res = await GET(req(DEMO_TOKEN, '?q=존재하지않는닉네임'))
    expect(res.status).toBe(200)
    expect((await res.json()).total).toBe(0)
  })
})
