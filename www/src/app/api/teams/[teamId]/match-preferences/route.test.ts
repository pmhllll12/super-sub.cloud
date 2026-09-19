import { NextRequest } from 'next/server'
import { SESSION_COOKIE } from '@/server/session'
import { GET, PUT } from './route'

/**
 * 팀 경기 조건 (계약 3-13절, CCC 40번).
 *
 * 🔴 **이 경로가 「우리 팀이 남에게 보이기 시작하는」 자리다** — 서버가
 * 「경기 조건을 하나라도 등록한 팀만」 후보로 고른다. 전에는 조건이
 * 브라우저에만 남아서 우리 팀이 남의 목록에 아예 안 떴다.
 */
beforeAll(() => {
  process.env.USE_MOCK = '1'
})

const DEMO_TOKEN = 'mock-access-token-demo'
const TEAM = '9a2e0000-0000-4000-8000-000000000002'

function ctx(teamId: string) {
  return { params: Promise.resolve({ teamId }) }
}

function req(body?: unknown) {
  const r = new NextRequest('http://t/api/teams/x/match-preferences', {
    method: body === undefined ? 'GET' : 'PUT',
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  })
  r.cookies.set(SESSION_COOKIE, DEMO_TOKEN)
  return r
}

describe('PUT /api/teams/[teamId]/match-preferences', () => {
  it('조건을 저장하면 그대로 돌려주고, 다시 읽어도 남아 있다', async () => {
    const saved = await PUT(
      req({
        region_ids: ['rg-001'],
        slots: [{ weekday: 5, start_time: '11:00:00', end_time: '12:00:00' }],
      }),
      ctx(TEAM),
    )
    expect(saved.status).toBe(200)
    expect((await saved.json()).region_ids).toEqual(['rg-001'])

    const read = await GET(req(), ctx(TEAM))
    expect((await read.json()).slots).toHaveLength(1)
  })

  /* 🔴 **통째로 교체다**(계약) — 부분 병합이 아니다. */
  it('다시 보내면 통째로 갈아 끼운다', async () => {
    await PUT(req({ region_ids: ['rg-001'], slots: [] }), ctx(TEAM))
    const res = await PUT(req({ region_ids: ['rg-010'], slots: [] }), ctx(TEAM))
    expect((await res.json()).region_ids).toEqual(['rg-010'])
  })

  /* 🔴 mock 이 실서버보다 너그러우면 **배포에서만 터진다**(1.12 회차에 세 번). */
  it('없는 지역 id 는 422 로 막는다', async () => {
    const res = await PUT(req({ region_ids: ['rg-없음'], slots: [] }), ctx(TEAM))
    expect(res.status).toBe(422)
    expect((await res.json()).error.code).toBe('UNKNOWN_REGION')
  })

  it('시작이 끝보다 늦은 시간대는 422 로 막는다', async () => {
    const res = await PUT(
      req({
        region_ids: [],
        slots: [{ weekday: 5, start_time: '13:00:00', end_time: '11:00:00' }],
      }),
      ctx(TEAM),
    )
    expect(res.status).toBe(422)
    expect((await res.json()).error.code).toBe('INVALID_TIME_SLOT')
  })

  /* 🔴 빈 몸통을 그대로 흘리면 「통째로 교체」 때문에 조건이 전부 지워진다. */
  it('배열이 아닌 몸통은 422 로 막는다 — 조건이 지워지면 안 된다', async () => {
    const res = await PUT(req({}), ctx(TEAM))
    expect(res.status).toBe(422)
  })
})
