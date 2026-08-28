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
