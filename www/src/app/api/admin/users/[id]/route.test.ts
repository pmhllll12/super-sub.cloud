import { NextRequest } from 'next/server'
import { SESSION_COOKIE } from '@/server/session'
import { POST as signup } from '../../../auth/signup/route'
import { GET, DELETE } from './route'

const DEMO_TOKEN = 'mock-access-token-demo'
const DEMO_ID = '3f1c0000-0000-4000-8000-000000000001'

function req(method: 'GET' | 'DELETE', token: string | undefined, id: string) {
  const r = new NextRequest(`https://supersub-ai.com/api/admin/users/${id}`, { method })
  if (token) r.cookies.set(SESSION_COOKIE, token)
  return r
}

function ctx(id: string) {
  return { params: Promise.resolve({ id }) }
}

/** 지워도 다른 테스트에 영향이 없는 회원 하나를 만들어 id 를 돌려준다. */
async function throwawayUserId(): Promise<string> {
  const email = `throwaway-${Date.now()}@super-sub.example`
  const res = await signup(
    new NextRequest('https://supersub-ai.com/api/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password: 'password123', nickname: '지울회원' }),
      headers: { 'content-type': 'application/json' },
    }),
  )
  return (await res.json()).id
}

describe('/api/admin/users/[id]', () => {
  beforeAll(() => {
    process.env.USE_MOCK = '1'
  })

  describe('GET', () => {
    it('쿠키가 없으면 401 이다', async () => {
      const res = await GET(req('GET', undefined, DEMO_ID), ctx(DEMO_ID))
      expect(res.status).toBe(401)
    })

    it('관리자면 상세 정보를 준다', async () => {
      const res = await GET(req('GET', DEMO_TOKEN, DEMO_ID), ctx(DEMO_ID))
      expect(res.status).toBe(200)
      const body = await res.json()
      expect(body.email).toBe('demo@super-sub.example')
      expect(body.has_card).toBe(true)
      expect(Array.isArray(body.teams)).toBe(true)
    })

    it('없는 회원이면 404 USER_NOT_FOUND 다', async () => {
      const missing = '00000000-0000-4000-8000-000000000000'
      const res = await GET(req('GET', DEMO_TOKEN, missing), ctx(missing))
      expect(res.status).toBe(404)
      expect((await res.json()).error.code).toBe('USER_NOT_FOUND')
    })
  })

  describe('DELETE', () => {
    it('없는 회원이면 404 다', async () => {
      const missing = '00000000-0000-4000-8000-000000000000'
      const res = await DELETE(req('DELETE', DEMO_TOKEN, missing), ctx(missing))
      expect(res.status).toBe(404)
    })

    it('있는 회원이면 204 로 지우고, 그 뒤 조회는 404 다', async () => {
      const id = await throwawayUserId()
      const del = await DELETE(req('DELETE', DEMO_TOKEN, id), ctx(id))
      expect(del.status).toBe(204)

      const after = await GET(req('GET', DEMO_TOKEN, id), ctx(id))
      expect(after.status).toBe(404)
    })
  })
})
