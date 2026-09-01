import { NextRequest } from 'next/server'
import { SESSION_COOKIE } from '@/server/session'
import { POST } from './route'

function post(body: unknown) {
  return new NextRequest('https://supersub-ai.com/api/auth/google', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'content-type': 'application/json' },
  })
}

describe('POST /api/auth/google', () => {
  beforeAll(() => {
    process.env.USE_MOCK = '1'
  })

  it('성공하면 비밀번호 로그인과 마찬가지로 토큰을 쿠키에만 담는다', async () => {
    const res = await POST(post({ id_token: 'mock-id-token' }))
    expect(res.status).toBe(200)

    const cookie = res.cookies.get(SESSION_COOKIE)
    expect(cookie?.httpOnly).toBe(true)
    expect(cookie?.value).toBeTruthy()

    expect(JSON.stringify(await res.json())).not.toContain(cookie!.value)
  })

  it('id_token 이 없으면 400 이다', async () => {
    const res = await POST(post({ access_token: '이건 access_token 이지 id_token 이 아니다' }))
    expect(res.status).toBe(400)
  })

  it('본문이 JSON 이 아니면 400 이다', async () => {
    const req = new NextRequest('https://supersub-ai.com/api/auth/google', {
      method: 'POST',
      body: 'not json',
      headers: { 'content-type': 'application/json' },
    })
    const res = await POST(req)
    expect(res.status).toBe(400)
  })
})
