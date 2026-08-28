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
