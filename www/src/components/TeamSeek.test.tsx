import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { OpenMatch } from '@/server/backend'
import { __resetRefDataCache } from '@/lib/refData'
import TeamSeek from './TeamSeek'

/**
 * 「팀원」 판의 **거르기** — 미결 `jin` 15번의 남은 조각(2026-09-10).
 *
 * 🔴 **거르기는 서버가 한다.** 화면에서 걸러 봐야 받아 온 첫 페이지(20건)
 * 안에서만 걸러져서, 그 뒤에 있는 것은 영영 안 나온다. 그래서 이 시험들은
 * **무엇이 질의로 나갔는지**를 붙든다.
 */
const MATCH: OpenMatch = {
  id: 'om1',
  team_id: 't1',
  team_name: '번개FC',
  region: '서울 강남구',
  sport_code: 'football',
  played_at: '2026-09-12T10:00:00Z',
  place: '강남 풋살장 1구장',
  needs: [{ position_code: 'GK', position_label: '골키퍼', head_count: 1 }],
}

const REGIONS = [
  { id: 'rg-001', city: '서울', district: '강남구', label: '서울 강남구' },
  { id: 'rg-010', city: '서울', district: '마포구', label: '서울 마포구' },
]
const POSITIONS = [
  { id: 'ps-football-gk', sport_code: 'football', code: 'GK', label: '골키퍼' },
  { id: 'ps-football-mf', sport_code: 'football', code: 'MF', label: '미드필더' },
]

/**
 * 🔴 **조건은 이제 서버에 있다**(계약 3-13절, 2026-09-17) — 전에는
 * `localStorage` 였다. 그래서 「이미 정해 둔 사람」을 만드는 방법이 저장소에
 * 값을 넣는 것이 아니라 **이 경로의 응답**을 정하는 것이다.
 */
const PREF_WIRE = {
  user_id: 'u1',
  region_ids: [] as string[],
  slots: [{ weekday: 5, start_time: '09:00:00', end_time: '11:00:00' }],
  position_ids: [] as string[],
}

function ok(body: unknown) {
  return { ok: true, status: 200, json: async () => body }
}

function stub(items: OpenMatch[] = [MATCH], pref: unknown = PREF_WIRE) {
  // `init` 은 안 쓰지만 **받는 모양은 맞춘다** — 시험이 무엇을 PUT 했는지 볼 때
  // 두 번째 인자가 타입에 있어야 집을 수 있다.
  const fn = vi.fn(async (url: string, _init?: RequestInit) => {
    const u = String(url)
    if (u.startsWith('/api/regions')) return ok(REGIONS)
    if (u.startsWith('/api/positions')) return ok(POSITIONS)
    if (u.startsWith('/api/me/match-preferences')) return ok(pref)
    return ok({ items, total: items.length, page: 1, size: 20 })
  })
  vi.stubGlobal('fetch', fn)
  return fn
}

/** 경기 목록을 받으러 나간 호출들만 — 조건·참조 데이터 호출과 섞이지 않게. */
const matchCalls = (fn: ReturnType<typeof vi.fn>) =>
  fn.mock.calls.filter((c) => String(c[0]).startsWith('/api/matches'))

/** 마지막으로 나간 **목록** 질의의 파라미터. */
const lastQuery = (fn: ReturnType<typeof vi.fn>) =>
  new URL(String(matchCalls(fn).at(-1)![0]), 'https://x.test').searchParams

/**
 * 🔴 **조건을 먼저 묻는다**(사용자 결정, 2026-09-10) — 정해 두지 않았으면
 * 거르기 줄도 목록도 안 그린다. 아래 시험들은 **이미 정해 둔** 사람의 화면이다.
 *
 * 🔴 **조건이 거르기를 대신하지 않는다.** 조건은 「늘 이런 경기를 찾는다」이고
 * 거르기는 「지금 이 목록에서 더 좁힌다」라 층이 다르다 — 조건은 거르기의
 * **첫 값**만 채운다.
 */
describe('팀원 판 — 종목 · 지역으로 거른다', () => {
  beforeEach(() => __resetRefDataCache())
  afterEach(() => vi.unstubAllGlobals())

  const open = () => render(<TeamSeek closing={false} onClose={() => {}} />)

  /* 🔴 **「전체」는 빈 값이 아니라 파라미터를 빼는 것이다.** `sport_code=` 는
     "전체"가 아니라 **없는 종목**이라 422 `UNKNOWN_SPORT` 로 튕긴다. */
  it('처음에는 거르는 값을 아예 안 보낸다', async () => {
    const fn = stub()
    open()
    await waitFor(() => expect(matchCalls(fn).length).toBeGreaterThan(0))
    const q = lastQuery(fn)
    expect(q.has('sport_code')).toBe(false)
    expect(q.has('region')).toBe(false)
    expect(q.get('size')).toBe('20')
  })

  /* 🔴 화면은 `soccer`, 백엔드는 `football` 이다 — 경계에서 바꿔 보낸다
     (`lib/sports.ts` 의 `SPORT_CODE`). 화면 키를 그대로 보내면 422 다. */
  it('종목을 고르면 백엔드 코드로 다시 묻는다', async () => {
    const fn = stub()
    open()
    await waitFor(() => expect(matchCalls(fn).length).toBeGreaterThan(0))

    await userEvent.click(screen.getByRole('button', { name: '축구' }))
    await waitFor(() => expect(lastQuery(fn).get('sport_code')).toBe('football'))
  })

  it('전체로 되돌리면 종목을 다시 안 보낸다', async () => {
    const fn = stub()
    open()
    await userEvent.click(screen.getByRole('button', { name: '축구' }))
    await waitFor(() => expect(lastQuery(fn).get('sport_code')).toBe('football'))

    await userEvent.click(screen.getByRole('button', { name: '전체' }))
    await waitFor(() => expect(lastQuery(fn).has('sport_code')).toBe(false))
  })

  /* 지역은 자유 문자열이라 **글자마다 부르지 않는다** — 제출한 값만 나간다.
     안 걸리면 그냥 빈 목록이고 422 가 아니다(종목과 처리가 다르다). */
  it('지역은 적는 동안이 아니라 찾기를 눌렀을 때 나간다', async () => {
    const fn = stub()
    open()
    await waitFor(() => expect(matchCalls(fn).length).toBeGreaterThan(0))
    const before = matchCalls(fn).length

    await userEvent.type(screen.getByLabelText('지역'), '마포')
    expect(matchCalls(fn).length).toBe(before)

    await userEvent.click(screen.getByRole('button', { name: '찾기' }))
    await waitFor(() => expect(lastQuery(fn).get('region')).toBe('마포'))
  })

  /* 🔴 **빈 지역은 안 보낸다** — 지웠는데 `region=` 이 남으면 "빈 이름의
     지역"을 찾는 질의가 된다. */
  it('지역을 비우면 그 파라미터가 빠진다', async () => {
    const fn = stub()
    open()
    await userEvent.type(screen.getByLabelText('지역'), '마포')
    await userEvent.click(screen.getByRole('button', { name: '찾기' }))
    await waitFor(() => expect(lastQuery(fn).get('region')).toBe('마포'))

    await userEvent.clear(screen.getByLabelText('지역'))
    await userEvent.click(screen.getByRole('button', { name: '찾기' }))
    await waitFor(() => expect(lastQuery(fn).has('region')).toBe(false))
  })

  /* 「없습니다」만 뜨면 사이트가 빈 것으로 읽힌다 — 거르기를 풀면 나온다는
     것을 알 수 있어야 한다. */
  it('걸러서 비면 조건 때문이라고 말한다', async () => {
    stub([])
    open()
    await userEvent.click(screen.getByRole('button', { name: '축구' }))
    expect(await screen.findByText('그 조건에 맞는 팀이 없습니다.')).toBeInTheDocument()
  })

  it('안 거르고 비면 그냥 없다고 말한다', async () => {
    stub([])
    open()
    expect(await screen.findByText('지금은 사람을 찾는 팀이 없습니다.')).toBeInTheDocument()
  })

  /* 🔴 **거르는 줄은 결과와 무관하게 늘 그린다.** 결과 안쪽에 두면 「없습니다」가
     떴을 때 거르기가 같이 사라져 되돌릴 방법이 없어진다. */
  it('결과가 비어도 거르는 줄은 남아 있다', async () => {
    stub([])
    open()
    await screen.findByText('지금은 사람을 찾는 팀이 없습니다.')
    expect(screen.getByRole('button', { name: '전체' })).toBeInTheDocument()
    expect(screen.getByLabelText('지역')).toBeInTheDocument()
  })

  /* 🔴 조건을 아직 안 정했으면 **묻는 것이 먼저다** — 목록도 거르기도 안 그린다. */
  it('조건이 없으면 먼저 묻는다', async () => {
    const fn = stub([MATCH], { user_id: 'u1', region_ids: [], slots: [], position_ids: [] })
    open()
    expect(await screen.findByText('어떤 경기를 찾으세요?')).toBeInTheDocument()
    // 조건을 모르는 채로 목록을 받아 오지 않는다.
    expect(matchCalls(fn)).toHaveLength(0)
  })

  /* 🔴 **조건의 첫 지역이 거르기의 첫 값을 채운다** — 늘 찾는 동네를 매번
     다시 적게 하지 않는다. 그 뒤로는 거르기가 제 일을 한다. */
  it('조건에 적은 동네로 시작한다', async () => {
    const fn = stub([MATCH], { ...PREF_WIRE, region_ids: ['rg-010'] })
    open()
    await waitFor(() => expect(lastQuery(fn).get('region')).toBe('서울 마포구'))
  })
})

/**
 * **내 조건이 서버로 올라간다** (계약 3-13절, 2026-09-17).
 *
 * 🔴 **이게 「내가 남의 AI 추천 후보로 뜨는」 유일한 길이다.** 서버가 후보를
 * 고를 때 첫 하드 필터가 「그 포지션을 등록했는가」인데, 조건이 브라우저에만
 * 남던 동안에는 **아무도 등록된 적이 없어서** 추천 판이 늘 0명이었다.
 */
describe('팀원 판 — 내 자리를 서버에 등록한다', () => {
  beforeEach(() => __resetRefDataCache())
  afterEach(() => vi.unstubAllGlobals())

  const NEW = { user_id: 'u1', region_ids: [], slots: [], position_ids: [] }

  /** 아직 아무것도 안 정한 사람의 화면 — 조건 폼이 먼저 뜬다. */
  function openAsking(fn: ReturnType<typeof vi.fn>) {
    render(<TeamSeek closing={false} onClose={() => {}} sportCode="football" />)
    void fn
    return screen.findByText('어떤 경기를 찾으세요?')
  }

  /** 동네 · 시간 · 자리를 채운다 — 셋 다 있어야 「팀 찾기」가 눌린다. */
  async function fill() {
    /* 이 칸은 `aria-labelledby` 가 **바깥 묶음**에 붙어 있어서 이름으로
       집으면 입력칸이 아니라 묶음이 잡힌다 — 자리표시자로 집는다. */
    await userEvent.type(screen.getByPlaceholderText('동네 이름을 적으세요'), '마포')
    await userEvent.click(await screen.findByRole('button', { name: '서울 마포구' }))
    await userEvent.click(screen.getByRole('button', { name: '+ 시간 추가' }))
    await userEvent.click(await screen.findByRole('button', { name: '미드필더' }))
  }

  it('고른 자리를 id 로 바꿔 서버에 올린다', async () => {
    const fn = stub([MATCH], NEW)
    await openAsking(fn)
    await fill()

    await userEvent.click(screen.getByRole('button', { name: '팀 찾기' }))

    await waitFor(() => {
      const put = fn.mock.calls.find((c) => (c[1] as RequestInit | undefined)?.method === 'PUT')
      expect(put).toBeDefined()
      expect(String(put![0])).toBe('/api/me/match-preferences')
      const body = JSON.parse(String((put![1] as RequestInit).body))
      expect(body.position_ids).toEqual(['ps-football-mf'])
      expect(body.region_ids).toEqual(['rg-010'])
      expect(body.slots).toHaveLength(1)
    })
  })

  /**
   * 🔴 **저장이 안 되면 그렇게 말한다.** 조용히 넘어가면 사용자는 등록된 줄
   * 알고, 정작 남의 추천 목록에는 안 뜬다 — 그 조합이 가장 나쁘다.
   */
  it('저장이 안 되면 넘어가지 않고 알린다', async () => {
    const fn = vi.fn(async (url: string, init?: RequestInit) => {
      const u = String(url)
      if (u.startsWith('/api/regions')) return ok(REGIONS)
      if (u.startsWith('/api/positions')) return ok(POSITIONS)
      if (u.startsWith('/api/me/match-preferences')) {
        if (init?.method === 'PUT') return { ok: false, status: 500, json: async () => null }
        return ok(NEW)
      }
      return ok({ items: [MATCH], total: 1, page: 1, size: 20 })
    })
    vi.stubGlobal('fetch', fn)

    await openAsking(fn)
    await fill()
    await userEvent.click(screen.getByRole('button', { name: '팀 찾기' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('저장하지 못했습니다')
    // 🔴 폼이 그대로 열려 있어야 다시 시도할 수 있다.
    expect(screen.getByText('어떤 경기를 찾으세요?')).toBeInTheDocument()
  })
})
