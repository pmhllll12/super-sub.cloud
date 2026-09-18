import { NextRequest } from 'next/server'
import { SESSION_COOKIE } from '@/server/session'
import { GET, PUT } from './route'

/**
 * 내 경기 조건 (계약 3-13절, CCC 40번).
 *
 * 🔴 **이 경로가 「내가 남의 AI 추천 후보로 뜨기 시작하는」 자리다.** 서버가
 * 후보를 고를 때 첫 하드 필터가 「그 포지션을 등록했는가」인데, 조건이
 * 브라우저(`localStorage`)에만 남던 동안에는 **아무도 등록된 적이 없어서**
 * 팀을 만들어도 추천이 영영 0명이었다(2026-09-17에 실제로 그랬다).
 *
 * 🔴 **팀 조건과 저장소가 다르다** — 같은 사람이 팀장이면서 팀원일 수 있어
 * 계약이 둘을 절대 안 섞는다.
 */
beforeAll(() => {
  process.env.USE_MOCK = '1'
})

const DEMO_TOKEN = 'mock-access-token-demo'
const MF = 'ps-football-mf'
const GK = 'ps-football-gk'

function req(body?: unknown) {
  const r = new NextRequest('http://t/api/me/match-preferences', {
    method: body === undefined ? 'GET' : 'PUT',
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  })
  r.cookies.set(SESSION_COOKIE, DEMO_TOKEN)
  return r
}

describe('PUT /api/me/match-preferences', () => {
  it('포지션까지 저장하면 그대로 돌려주고, 다시 읽어도 남아 있다', async () => {
    const saved = await PUT(
      req({
        region_ids: ['rg-001'],
        slots: [{ weekday: 5, start_time: '11:00:00', end_time: '12:00:00' }],
        position_ids: [MF],
      }),
    )
    expect(saved.status).toBe(200)
    expect((await saved.json()).position_ids).toEqual([MF])

    const read = await GET(req())
    const body = await read.json()
    expect(body.position_ids).toEqual([MF])
    expect(body.slots).toHaveLength(1)
  })

  /* 🔴 **통째로 교체다**(계약) — 부분 병합이 아니다. */
  it('다시 보내면 통째로 갈아 끼운다', async () => {
    await PUT(req({ region_ids: [], slots: [], position_ids: [MF] }))
    const res = await PUT(req({ region_ids: [], slots: [], position_ids: [GK] }))
    expect((await res.json()).position_ids).toEqual([GK])
  })

  /* 🔴 mock 이 실서버보다 너그러우면 **배포에서만 터진다**(1.12 회차에 세 번). */
  it('없는 포지션 id 는 422 로 막는다', async () => {
    const res = await PUT(req({ region_ids: [], slots: [], position_ids: ['ps-없음'] }))
    expect(res.status).toBe(422)
    expect((await res.json()).error.code).toBe('UNKNOWN_POSITION')
  })

  it('없는 지역 id 는 422 로 막는다', async () => {
    const res = await PUT(req({ region_ids: ['rg-없음'], slots: [], position_ids: [] }))
    expect(res.status).toBe(422)
    expect((await res.json()).error.code).toBe('UNKNOWN_REGION')
  })

  it('시작이 끝보다 늦은 시간대는 422 로 막는다', async () => {
    const res = await PUT(
      req({
        region_ids: [],
        slots: [{ weekday: 5, start_time: '13:00:00', end_time: '11:00:00' }],
        position_ids: [],
      }),
    )
    expect(res.status).toBe(422)
    expect((await res.json()).error.code).toBe('INVALID_TIME_SLOT')
  })

  /* 🔴 빈 몸통을 그대로 흘리면 「통째로 교체」 때문에 조건이 전부 지워진다. */
  it('배열이 아닌 몸통은 422 로 막는다 — 조건이 지워지면 안 된다', async () => {
    expect((await PUT(req({}))).status).toBe(422)
  })
})
