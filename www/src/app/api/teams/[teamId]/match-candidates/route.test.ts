import { NextRequest } from 'next/server'
import { SESSION_COOKIE } from '@/server/session'
import { GET } from './route'
import { PUT } from '../match-preferences/route'

/**
 * 「맞는 상대」 후보 (계약 3-13절, CCC 40번).
 *
 * 🔴 **조건을 등록한 팀만 후보가 된다**(하드 필터). 그 규칙의 짝이 곧
 * 「우리가 조건을 안 올리면 **남의 목록에도 우리가 안 뜬다**」다 — 사용자가
 * 물은 것이 정확히 이것이라 시험으로 굳혀 둔다.
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
  const r = new NextRequest('http://t/api/teams/x/match-candidates', {
    method: body === undefined ? 'GET' : 'PUT',
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  })
  r.cookies.set(SESSION_COOKIE, DEMO_TOKEN)
  return r
}

describe('GET /api/teams/[teamId]/match-candidates', () => {
  it('조건을 올린 뒤에는 후보가 온다', async () => {
    await PUT(req({ region_ids: ['rg-001'], slots: [] }), ctx(TEAM))

    const res = await GET(req(), ctx(TEAM))
    expect(res.status).toBe(200)
    const rows = await res.json()
    expect(rows.length).toBeGreaterThan(0)
    // 🔴 **점수가 없다.** 근거는 `reasons` 의 사실값 문장이다.
    expect(rows[0]).not.toHaveProperty('score')
    expect(rows[0]).toHaveProperty('reasons')
  })

  /* 🔴 소프트 근거가 0개인 줄도 정상이다 — 하드 필터는 통과했다. */
  it('근거가 빈 후보도 목록에 남는다', async () => {
    await PUT(req({ region_ids: ['rg-001'], slots: [] }), ctx(TEAM))
    const rows = await (await GET(req(), ctx(TEAM))).json()
    expect(rows.some((r: { reasons: unknown[] }) => r.reasons.length === 0)).toBe(true)
  })

  it('🔴 조건을 안 올린 팀에는 후보가 안 온다 — 우리도 남에게 안 뜬다', async () => {
    // 조건을 비우면(통째로 교체) 등록이 없는 상태가 된다.
    await PUT(req({ region_ids: [], slots: [] }), ctx(TEAM))

    const rows = await (await GET(req(), ctx(TEAM))).json()
    expect(rows).toEqual([])
  })
})
