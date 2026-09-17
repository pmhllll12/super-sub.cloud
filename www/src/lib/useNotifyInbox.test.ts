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
