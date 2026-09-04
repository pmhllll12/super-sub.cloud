import { NextRequest } from 'next/server'
import { SESSION_COOKIE } from '@/server/session'
import { POST } from './route'

const DEMO_TOKEN = 'mock-access-token-demo'
const DEMO_TEAM_ID = '9a2e0000-0000-4000-8000-000000000002'

function req(token: string | undefined, body: unknown) {
  const r = new NextRequest(`https://supersub-ai.com/api/teams/${DEMO_TEAM_ID}/matches`, {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'content-type': 'application/json' },
  })
  if (token) r.cookies.set(SESSION_COOKIE, token)
  return r
}

function ctx(teamId = DEMO_TEAM_ID) {
  return { params: Promise.resolve({ teamId }) }
}

describe('POST /api/teams/[teamId]/matches', () => {
  beforeAll(() => {
    process.env.USE_MOCK = '1'
  })

  it('쿠키가 없으면 401 UNAUTHORIZED 다', async () => {
    const res = await POST(req(undefined, {}), ctx())
    expect(res.status).toBe(401)
    expect((await res.json()).error.code).toBe('UNAUTHORIZED')
  })

  it('필수 필드가 없으면 422 VALIDATION_ERROR 다 — 백엔드를 부르지 않는다', async () => {
    const res = await POST(req(DEMO_TOKEN, { place: '어딘가' }), ctx())
    expect(res.status).toBe(422)
    expect((await res.json()).error.code).toBe('VALIDATION_ERROR')
  })

  it('needs 항목의 형태가 어긋나면 422 다', async () => {
    const res = await POST(
      req(DEMO_TOKEN, {
        played_at: new Date(Date.now() + 86400000).toISOString(),
        place: '어딘가',
        needs: [{ position_code: 'GK' }], // head_count 없음
      }),
      ctx(),
    )
    expect(res.status).toBe(422)
    expect((await res.json()).error.code).toBe('VALIDATION_ERROR')
  })

  it('주장이 유효한 값으로 부르면 201로 경기가 만들어진다', async () => {
    const res = await POST(
      req(DEMO_TOKEN, {
        played_at: new Date(Date.now() + 86400000).toISOString(),
        place: '강남 풋살장 3구장',
        needs: [{ position_code: 'FW', head_count: 1 }],
      }),
      ctx(),
    )
    expect(res.status).toBe(201)
    const match = await res.json()
    expect(match.team_id).toBe(DEMO_TEAM_ID)
    expect(match.place).toBe('강남 풋살장 3구장')
  })
})
