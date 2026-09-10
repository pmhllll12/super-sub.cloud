import { NextRequest } from 'next/server'
import { SESSION_COOKIE } from '@/server/session'
import { GET } from './route'

const DEMO_TOKEN = 'mock-access-token-demo'

function req(token: string | undefined, query = '') {
  const r = new NextRequest(`https://supersub-ai.com/api/positions${query}`)
  if (token) r.cookies.set(SESSION_COOKIE, token)
  return r
}

/**
 * 계약 3-3절 `GET /positions` (CCC 28).
 *
 * 🔴 이 경로가 생기기 전에는 챗봇 프롬프트 · 스쿼드 등재 · 모집 등록이 각자
 * `{ GK: '골키퍼', … }` 를 들고 있었다 — 마이그레이션이 바뀌면 **조용히
 * 낡는** 자리였다. 목록의 정본이 서버 하나라는 것을 이 시험이 붙든다.
 */
describe('GET /api/positions', () => {
  beforeAll(() => {
    process.env.USE_MOCK = '1'
  })

  // 참조 데이터지만 열어 두지 않는다 — 계약이 「로그인하면 누구나」로 정했다.
  it('쿠키가 없으면 401 UNAUTHORIZED 다', async () => {
    const res = await GET(req(undefined))
    expect(res.status).toBe(401)
    expect((await res.json()).error.code).toBe('UNAUTHORIZED')
  })

  it('종목을 주면 그 종목의 포지션만 준다', async () => {
    const res = await GET(req(DEMO_TOKEN, '?sport_code=football'))
    expect(res.status).toBe(200)
    const body = await res.json()
    expect(body.map((p: { code: string }) => p.code).sort()).toEqual(['DF', 'FW', 'GK', 'MF'])
    expect(body.every((p: { sport_code: string }) => p.sport_code === 'football')).toBe(true)
  })

  /* 🔴 **빈 배열이 아니라 422 다**(`GET /matches` 와 같은 판단) — 오타와
     "그 종목 포지션이 아직 없다"가 같아 보이면 사용자가 없는 것을 계속
     기다린다. */
  it('없는 종목이면 422 UNKNOWN_SPORT 다', async () => {
    const res = await GET(req(DEMO_TOKEN, '?sport_code=quidditch'))
    expect(res.status).toBe(422)
    expect((await res.json()).error.code).toBe('UNKNOWN_SPORT')
  })

  /* 🔴 **빈 값을 그대로 흘려보내지 않는다.** `?sport_code=` 는 "전체"가 아니라
     없는 종목이라, 그대로 보내면 전 종목을 원한 사람이 422 를 받는다. */
  it('sport_code 가 비어 있으면 전 종목으로 본다', async () => {
    const res = await GET(req(DEMO_TOKEN, '?sport_code='))
    expect(res.status).toBe(200)
    expect((await res.json()).length).toBeGreaterThan(4)
  })

  /* 🔴 **`code` 는 종목 안에서만 유일하다** — 야구 `C`(포수)와 농구 `C`(센터)가
     둘 다 실려 온다. 코드만으로 이름을 찾으면 남의 종목 이름이 붙는다. */
  it('전 종목을 받으면 같은 코드가 종목별로 따로 온다', async () => {
    const res = await GET(req(DEMO_TOKEN))
    const cs = (await res.json()).filter((p: { code: string }) => p.code === 'C')
    expect(cs.map((p: { sport_code: string }) => p.sport_code).sort()).toEqual([
      'baseball',
      'basketball',
    ])
    expect(new Set(cs.map((p: { label: string }) => p.label)).size).toBe(2)
  })
})
