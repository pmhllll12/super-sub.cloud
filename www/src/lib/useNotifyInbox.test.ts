import { renderHook, waitFor } from '@testing-library/react'
import { useNotifyInbox } from './useNotifyInbox'

/**
 * **알림 줄의 팀 이름은 서버가 준다** (CCC 55, 미결 `paik` 31번, 2026-09-17).
 *
 * 🔴 **정정**: 전에는 계약이 이름을 안 줘서 화면의 붙박이 목록(`teamMatch.ts`
 * 의 `teamById`)에서 찾고, 못 찾으면 「상대 팀」이라고 적었다. 붙박이에 없는
 * 진짜 팀이 걸면 이름이 통째로 사라졌다 — 이름을 지어내지 않으려고 그렇게
 * 둔 것이지 옳아서가 아니었다.
 */
const ME = { teams: [{ team_id: 'team-mine', role: 'owner' }] }

function stub(rows: unknown[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((url: string) => {
      const u = String(url)
      const body = u.endsWith('/api/me')
        ? ME
        : u.includes('/match-requests')
          ? rows
          : []
      return Promise.resolve({ ok: true, status: 200, json: async () => body })
    }),
  )
}

const ROW = {
  id: 'tmr1',
  requester_team_id: 'mt-2',
  target_team_id: 'team-mine',
  proposed_played_at: '2026-09-19T09:00:00+09:00',
  proposed_place: '망원 실내구장 A',
  status: 'pending',
  match_id: null,
  requester_team_name: '망원 유나이티드',
  requester_team_region: '서울 마포구',
  target_team_name: '번개FC',
  target_team_region: '서울 강남구',
}

describe('알림함 — 상대 팀 이름', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('서버가 준 이름·지역을 그대로 쓴다', async () => {
    stub([ROW])
    const { result } = renderHook(() => useNotifyInbox())
    await waitFor(() => expect(result.current.items).toHaveLength(1))
    const item = result.current.items[0]
    expect(item.kind).toBe('team-match')
    if (item.kind !== 'team-match') return
    expect(item.name).toBe('망원 유나이티드')
    expect(item.region).toBe('서울 마포구')
  })

  /**
   * 🔴 **붙박이 목록에서 찾지 않는다.** `teamMatch.ts` 의 `TEAMS` 에 `mt-2` 가
   * 「망원 유나이티드」로 들어 있어서, 폴백이 되살아나도 위 시험은 통과한다 —
   * 그래서 **서버가 다른 이름을 준 경우**로 가른다. 폴백이 살아 있으면
   * 붙박이 이름이 이기므로 여기서 빨개진다.
   */
  it('붙박이 목록이 아니라 응답을 믿는다', async () => {
    stub([{ ...ROW, requester_team_name: '서버가 준 이름', requester_team_region: '서버 지역' }])
    const { result } = renderHook(() => useNotifyInbox())
    await waitFor(() => expect(result.current.items).toHaveLength(1))
    const item = result.current.items[0]
    if (item.kind !== 'team-match') throw new Error('경기 신청이어야 한다')
    expect(item.name).toBe('서버가 준 이름')
    expect(item.region).toBe('서버 지역')
  })

  /* 옛 응답이면 `null` 이다 — 그때도 터지지 않고, 화면이 이름 없이 그린다. */
  it('이름이 안 오면 null 로 둔다 — 지어내지 않는다', async () => {
    stub([{ ...ROW, requester_team_name: null, requester_team_region: null }])
    const { result } = renderHook(() => useNotifyInbox())
    await waitFor(() => expect(result.current.items).toHaveLength(1))
    const item = result.current.items[0]
    if (item.kind !== 'team-match') throw new Error('경기 신청이어야 한다')
    expect(item.name).toBeNull()
    expect(item.region).toBeNull()
  })
})

/**
 * **받은 팀 초대**도 이 알림함이 담는다 (CCC 53번, 미결 `paik` 37번).
 *
 * 서버가 초대 한 줄에 팀 이름·지역·부르는 자리·스쿼드 슬러그를 실어 주므로
 * (`GET /me/invitations`), 화면은 줄마다 팀을 따로 부르지 않는다.
 */
const INVITE = {
  id: 'inv1',
  team_id: 'team-bolt',
  invited_user_id: 'u-me',
  status: 'pending',
  created_at: '2026-09-17T10:00:00+09:00',
  responded_at: null,
  position_code: 'GK',
  position_label: '골키퍼',
  team_name: '번개FC',
  team_region: '서울 강남',
  team_sport_code: 'football',
  squad_public_slug: 'sq-abc123',
}

/** `/api/me` 응답과 초대 목록을 갈아 끼우는 대역. 보낸 요청을 모아 돌려준다. */
function stubInvites(invites: unknown[], me: unknown = ME) {
  const sent: { url: string; method: string }[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      const u = String(url)
      sent.push({ url: u, method: init?.method ?? 'GET' })
      const body = u.endsWith('/api/me') ? me : u.includes('/me/invitations') ? invites : []
      return Promise.resolve({ ok: true, status: 200, json: async () => body })
    }),
  )
  return sent
}

describe('알림함 — 받은 팀 초대', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('초대가 한 줄로 온다 — 팀 이름·지역·부르는 자리를 서버 값으로', async () => {
    stubInvites([INVITE])
    const { result } = renderHook(() => useNotifyInbox())
    await waitFor(() => expect(result.current.items).toHaveLength(1))
    const item = result.current.items[0]
    expect(item.kind).toBe('invitation')
    if (item.kind !== 'invitation') return
    expect(item.teamName).toBe('번개FC')
    expect(item.teamRegion).toBe('서울 강남')
    expect(item.posLabel).toBe('골키퍼')
    expect(item.squadSlug).toBe('sq-abc123')
  })

  /**
   * 🔴 **이것이 이 갈래의 함정이다.** 지금 `reload()` 는 `role === 'owner'` 인
   * 내 팀을 먼저 찾고 그 밑에서만 읽는다. 그런데 **초대를 받는 사람은 대개
   * 팀이 없다** — 팀 유무에 초대를 묶으면 정작 받아야 할 사람에게 안 뜬다.
   */
  it('🔴 내 팀이 없어도 초대는 읽는다 — 초대받는 사람은 대개 팀이 없다', async () => {
    stubInvites([INVITE], { teams: [] })
    const { result } = renderHook(() => useNotifyInbox())
    await waitFor(() => expect(result.current.items).toHaveLength(1))
    expect(result.current.items[0].kind).toBe('invitation')
  })

  /* 자리를 안 정한 초대(「우리 팀에 오세요」)가 정상이다 — 계약의 「하지 말 것」. */
  it('자리를 안 정한 초대도 정상이다 — null 을 실패로 보지 않는다', async () => {
    stubInvites([{ ...INVITE, position_code: null, position_label: null }])
    const { result } = renderHook(() => useNotifyInbox())
    await waitFor(() => expect(result.current.items).toHaveLength(1))
    const item = result.current.items[0]
    if (item.kind !== 'invitation') throw new Error('초대여야 한다')
    expect(item.posLabel).toBeNull()
  })

  it('수락하면 그 초대의 accept 경로를 부른다', async () => {
    const sent = stubInvites([INVITE])
    const { result } = renderHook(() => useNotifyInbox())
    await waitFor(() => expect(result.current.items).toHaveLength(1))
    const item = result.current.items[0]
    if (item.kind !== 'invitation') throw new Error('초대여야 한다')

    await result.current.acceptInvitation(item)

    expect(
      sent.some((c) => c.method === 'POST' && c.url.endsWith('/api/me/invitations/inv1/accept')),
    ).toBe(true)
  })

  it('거절하면 그 초대의 reject 경로를 부른다', async () => {
    const sent = stubInvites([INVITE])
    const { result } = renderHook(() => useNotifyInbox())
    await waitFor(() => expect(result.current.items).toHaveLength(1))
    const item = result.current.items[0]
    if (item.kind !== 'invitation') throw new Error('초대여야 한다')

    await result.current.rejectInvitation(item)

    expect(
      sent.some((c) => c.method === 'POST' && c.url.endsWith('/api/me/invitations/inv1/reject')),
    ).toBe(true)
  })
})
