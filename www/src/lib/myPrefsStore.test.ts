import { loadMyPrefs, saveMyPrefs } from './myPrefsStore'
import { __resetRefDataCache } from './refData'

/**
 * **내 경기 조건을 서버에 읽고 쓴다** (계약 3-13절, CCC 40번).
 *
 * 🔴 **여기가 「내가 남의 AI 추천 후보로 뜨기 시작하는」 자리다.** 서버가
 * 후보를 고를 때 첫 하드 필터가 「그 포지션을 등록했는가」인데, 조건이
 * `localStorage` 에만 남던 동안에는 **아무도 등록된 적이 없어서** 팀을
 * 만들어도 추천이 영영 0명이었다(2026-09-17에 실제로 그랬다).
 */
const REGIONS = [
  { id: 'rg-001', city: '서울', district: '강남구', label: '서울 강남구' },
  { id: 'rg-010', city: '서울', district: '마포구', label: '서울 마포구' },
]
const POSITIONS = [
  { id: 'ps-football-gk', sport_code: 'football', code: 'GK', label: '골키퍼' },
  { id: 'ps-football-mf', sport_code: 'football', code: 'MF', label: '미드필더' },
]

type Sent = { url: string; method: string; body: unknown }

/** 지역·포지션 목록을 주고, 내 조건 경로의 응답을 정한다. */
function stub(pref: unknown = { user_id: 'u1', region_ids: [], slots: [], position_ids: [] }) {
  const sent: Sent[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const u = String(url)
      sent.push({
        url: u,
        method: init?.method ?? 'GET',
        body: init?.body ? JSON.parse(String(init.body)) : null,
      })
      if (u.startsWith('/api/regions')) return new Response(JSON.stringify(REGIONS), { status: 200 })
      if (u.startsWith('/api/positions'))
        return new Response(JSON.stringify(POSITIONS), { status: 200 })
      if (u.startsWith('/api/me/match-preferences'))
        return new Response(JSON.stringify(pref), { status: 200 })
      return new Response('null', { status: 404 })
    }),
  )
  return sent
}

beforeEach(() => __resetRefDataCache())
afterEach(() => vi.unstubAllGlobals())

describe('내 조건 저장', () => {
  it('고른 포지션을 id 로 바꿔 서버에 올린다', async () => {
    const sent = stub()

    await saveMyPrefs('football', {
      regions: ['서울 마포구'],
      times: [{ day: 6, from: '09:00', to: '11:00' }],
      positions: ['MF'],
    })

    const put = sent.find((s) => s.method === 'PUT')!
    expect(put.url).toBe('/api/me/match-preferences')
    expect(put.body).toEqual({
      region_ids: ['rg-010'],
      slots: [{ weekday: 5, start_time: '09:00:00', end_time: '11:00:00' }],
      position_ids: ['ps-football-mf'],
    })
  })

  /**
   * 🔴 **조용히 빈 조건으로 저장되는 것을 막는다.** 약칭→id 가 하나도 안
   * 풀리면(종목이 어긋났거나 목록을 못 받았거나) 「포지션 0개」로 저장되는데,
   * 그러면 **화면에는 성공으로 보이는데 추천 후보에는 영영 안 뜬다** — 그
   * 조합이 가장 나쁘다. 팀 조건의 지역에서 같은 판단을 했다.
   */
  it('고른 포지션이 하나도 안 풀리면 저장하지 않고 알린다', async () => {
    const sent = stub()

    await expect(
      saveMyPrefs('football', { regions: [], times: [], positions: ['QB'] }),
    ).rejects.toThrow()

    expect(sent.some((s) => s.method === 'PUT')).toBe(false)
  })

  /* 종목을 모르면 약칭을 풀 수 없다 — 약칭은 종목 안에서만 유일하다. */
  it('종목을 모르는데 포지션을 골랐으면 저장하지 않는다', async () => {
    const sent = stub()

    await expect(
      saveMyPrefs(null, { regions: [], times: [], positions: ['MF'] }),
    ).rejects.toThrow()

    expect(sent.some((s) => s.method === 'PUT')).toBe(false)
  })

  /* 포지션을 안 골랐으면 종목을 몰라도 지역·시간은 올릴 수 있다. */
  it('포지션을 안 골랐으면 종목 없이도 올린다', async () => {
    const sent = stub()

    await saveMyPrefs(null, { regions: ['서울 강남구'], times: [], positions: [] })

    const put = sent.find((s) => s.method === 'PUT')!
    expect(put.body).toEqual({ region_ids: ['rg-001'], slots: [], position_ids: [] })
  })
})

describe('내 조건 읽기', () => {
  /**
   * 🔴 **아직 안 정한 것과 빈 조건을 가른다** — 「처음이라 물어야 하는가」가
   * 그 차이로 정해진다. 서버는 안 정했을 때도 빈 목록을 담은 200 을 준다.
   */
  it('아무것도 안 정했으면 null 이다', async () => {
    stub({ user_id: 'u1', region_ids: [], slots: [], position_ids: [] })
    expect(await loadMyPrefs('football')).toBeNull()
  })

  it('받은 id 를 화면 값으로 되돌린다', async () => {
    stub({
      user_id: 'u1',
      region_ids: ['rg-001'],
      slots: [{ weekday: 5, start_time: '09:00:00', end_time: '11:00:00' }],
      position_ids: ['ps-football-gk'],
    })

    expect(await loadMyPrefs('football')).toEqual({
      regions: ['서울 강남구'],
      times: [{ day: 6, from: '09:00', to: '11:00' }],
      positions: ['GK'],
    })
  })

  /* 포지션만 정해 둔 것도 「정했다」다 — 그것이 곧 후보로 뜨는 조건이다. */
  it('포지션만 있어도 정한 것으로 본다', async () => {
    stub({ user_id: 'u1', region_ids: [], slots: [], position_ids: ['ps-football-mf'] })
    expect((await loadMyPrefs('football'))?.positions).toEqual(['MF'])
  })
})
