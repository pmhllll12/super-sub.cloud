import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PREFS_KEY, type MatchPrefs } from '@/lib/matchPrefs'
import { __resetRegionsCache } from '@/lib/teamPrefsStore'
import TeamMatch from './TeamMatch'

/**
 * **비슷한 팀 명단** — 「팀 매칭」이 여는 판(사용자 요청, 2026-09-10).
 *
 * ⚠️ **명단은 아직 mock 이다**(`lib/teamMatch.ts` — 「비슷하다」를 고르는
 * 경로가 계약에 없다). 🔴 **신청은 2026-09-16 에 진짜가 됐다**(계약 3-15절) —
 * 그래서 이 파일은 `fetch` 를 세우고 **무엇이 나갔는지**까지 본다.
 */
/** 이미 정해 둔 조건 — 이게 없으면 판이 명단 대신 **조건부터 묻는다**. */
const PREFS: MatchPrefs = {
  regions: ['서울 강남구'],
  times: [{ day: 6, from: '09:00', to: '11:00' }],
  positions: [],
}

describe('비슷한 팀 명단', () => {
  /* 🔴 대역이 이 값을 읽으므로 **쓰는 곳보다 위**에 둔다(모듈 상수 TDZ). */
  const MY_TEAM = 'team-mine'

  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem(PREFS_KEY, JSON.stringify({ team: PREFS }))
  })

  /** 나간 요청들 — 신청이 진짜로 서버로 가는지 본다. */
  let calls: { url: string; body: string | null }[]

  beforeEach(() => {
    calls = []
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        calls.push({
          url: String(input),
          body: typeof init?.body === 'string' ? init.body : null,
        })
        const u = String(input)
        /* 🔴 **조건은 이제 서버에서 온다**(CCC 40번) — 전에는 `localStorage`
           였다. 그 둘을 대역하지 않으면 조건이 `null` 로 읽혀서 판이 명단
           대신 **조건 판부터 띄운다**(실제로 12건이 그렇게 깨졌다). */
        if (u.endsWith('/api/regions')) {
          return Promise.resolve(
            new Response(
              JSON.stringify([
                { id: 'rg-001', city: '서울', district: '강남구', label: '서울 강남구' },
              ]),
              { status: 200 },
            ),
          )
        }
        if (u.includes('/match-preferences')) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                team_id: MY_TEAM,
                region_ids: ['rg-001'],
                // 토요일 = 계약 5(0=월). 화면의 day 6 과 같은 날이다.
                slots: [{ weekday: 5, start_time: '09:00:00', end_time: '11:00:00' }],
              }),
              { status: 200 },
            ),
          )
        }
        return Promise.resolve(
          new Response(JSON.stringify({ id: 'tmr9', status: 'pending' }), { status: 201 }),
        )
      },
    )
  })

  afterEach(() => {
    vi.restoreAllMocks()
    /* 🔴 지역 목록은 한 번만 읽고 캐시한다 — 시험 사이에 비워야 다음
       시험의 대역이 실제로 불린다. */
    __resetRegionsCache()
  })

  const open = (onRequested = vi.fn()) => {
    render(
      <TeamMatch
        size="5"
        closing={false}
        onClose={() => {}}
        teamId={MY_TEAM}
        onRequested={onRequested}
      />,
    )
    return onRequested
  }

  /* mock 이 일부러 늦게 답한다 — 즉시 답하면 「찾는 중」 화면을 안 만들게 되고,
     진짜 경로가 붙는 날 그 화면이 없다는 것을 알게 된다. */
  it('찾는 동안 그렇게 말한다', () => {
    open()
    expect(screen.getByText('비슷한 팀을 찾고 있습니다…')).toBeInTheDocument()
  })

  it('우리와 같은 크기의 팀만 나온다', async () => {
    open()
    expect(await screen.findByText('번개FC')).toBeInTheDocument()
    // mock 의 세 팀이 다 5:5 다 — 7:7 을 넣으면 아무도 안 나온다.
    expect(screen.getAllByRole('button', { name: '경기 신청' })).toHaveLength(3)
  })

  /* 🔴 **크기마다 팀이 나온다.** 5:5 만 mock 에 넣어 뒀더니 판을 7:7 로 바꾼
     사람에게 「조건이 맞는 팀이 없습니다」만 떴다(사용자 지적, 2026-09-10) —
     mock 이 비어 있는 것과 조건이 안 맞는 것이 화면에서 같아 보인다. */
  it.each([
    ['3', '삼삼오오'],
    ['5', '번개FC'],
    ['7', '강남 세븐스'],
  ])('%s:%s 판에도 팀이 나온다', async (size, first) => {
    render(
      <TeamMatch
        size={size}
        closing={false}
        onClose={() => {}}
        teamId={MY_TEAM}
        onRequested={vi.fn()}
      />,
    )
    expect(await screen.findByText(first)).toBeInTheDocument()
  })

  /* 🔴 **크기가 섞이지 않는다** — 5:5 를 짜 놓고 7:7 팀이 나오면 그 자체로
     「비슷하다」가 아니다. */
  it('우리와 다른 크기의 팀은 안 나온다', async () => {
    open()
    await screen.findByText('번개FC')
    expect(screen.queryByText('강남 세븐스')).toBeNull()
    expect(screen.queryByText('삼삼오오')).toBeNull()
  })

  /* 🔴 **근거를 지어내지 않는다 — 조건과 대조해서 만든다.** 손으로 적어 두면
     「토요일」이라 해 놓고 날짜가 일요일인 일이 생긴다(실제로 있었다). */
  it('조건과 실제로 겹치는 것만 근거로 적는다', async () => {
    open()
    await screen.findByText('번개FC')
    /* 조건은 「서울 강남구 · 토 09:00~11:00」.
       지역은 번개FC(강남구) 하나, 시간은 토요일 둘(번개 10시 · 망원 9시)이
       겹치고 수원(일요일)은 안 겹친다. */
    expect(screen.getAllByText('같은 지역')).toHaveLength(1)
    expect(screen.getAllByText('시간이 맞음')).toHaveLength(2)
    // 크기는 늘 같으므로 셋 다 붙는다.
    expect(screen.getAllByText('5 : 5')).toHaveLength(3)
  })

  /* 🔴 **안 겹친다고 빼지 않는다.** 조건은 「이런 걸 찾는다」이지 「이것만
     보겠다」가 아니다 — 다 빼면 조건을 조금 잘못 적은 사람에게 빈 화면만 남는다.
     대신 근거가 많은 쪽이 위로 온다. */
  it('근거가 많은 팀이 앞에 온다', async () => {
    open()
    await screen.findByText('번개FC')
    const names = [...document.querySelectorAll('.ss-tm-name')].map((el) => el.textContent)
    expect(names[0]).toBe('번개FC')
    expect(names).toHaveLength(3)
  })

  /**
   * 🔴 조건을 아직 안 정했으면 **명단 대신 묻는다**(사용자 결정).
   *
   * 🔴 **서버는 조건이 없을 때도 빈 목록을 담은 200 을 준다**(404 가 아니다) —
   * 그래서 「지역도 시간도 0개」를 곧 「안 정했다」로 읽는다. 전에는
   * `localStorage.clear()` 로 만들던 상태다.
   */
  it('조건이 없으면 먼저 묻는다', async () => {
    __resetRegionsCache()
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const u = String(input)
      const body = u.endsWith('/api/regions')
        ? []
        : { team_id: MY_TEAM, region_ids: [], slots: [] }
      return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))
    })
    open()
    expect(await screen.findByText('어떤 경기를 찾으세요?')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '경기 신청' })).toBeNull()
  })

  it('정해 둔 조건이 있으면 고칠 길만 둔다', async () => {
    open()
    await screen.findByText('번개FC')
    expect(screen.queryByText('어떤 경기를 찾으세요?')).toBeNull()
    expect(screen.getByRole('button', { name: '설정 수정' })).toBeInTheDocument()
  })

  /**
   * 🔴 **신청은 「잡혔다」가 아니다**(사용자 요청, 2026-09-16). 전에는 가짜
   * `applyToTeam` 이 1.4초 뒤 수락된 것으로 쳐 줘서 대기 팝업이 바로 떴다 —
   * 이제 이 판이 하는 일은 신청을 **거는 것까지**이고, 확정은 알림으로 온다.
   */
  it('신청하면 계약 경로로 보내고, 상대 수락을 기다린다고 적는다', async () => {
    const user = userEvent.setup()
    const onRequested = open()
    await screen.findByText('번개FC')

    await user.click(screen.getAllByRole('button', { name: '경기 신청' })[0])

    await waitFor(() => expect(onRequested).toHaveBeenCalled())
    const sent = calls.find((c) => c.url === `/api/teams/${MY_TEAM}/match-requests`)
    expect(sent).toBeDefined()
    expect(JSON.parse(sent!.body!).target_team_id).toBe('mt-1')

    // 🔴 **대기 팝업을 띄우라고 하지 않는다** — 넘기는 것은 신청 id 다.
    expect(onRequested.mock.calls[0][0]).toBe('tmr9')
    expect(await screen.findByRole('button', { name: '상대 수락 대기 중' })).toBeInTheDocument()
  })

  /* 🔴 **한 번에 한 곳에만 신청한다.** 여러 곳에 걸어 두면 둘이 동시에
     수락했을 때 어느 경기가 잡힌 것인지 화면이 답할 수 없다. */
  it('기다리는 동안 다른 팀에는 신청하지 못한다', async () => {
    const user = userEvent.setup()
    open()
    await screen.findByText('번개FC')

    await user.click(screen.getAllByRole('button', { name: '경기 신청' })[0])
    for (const b of screen.getAllByRole('button', { name: '경기 신청' })) {
      expect(b).toBeDisabled()
    }
  })

  /* 🔴 **어디까지가 진짜인지 적어 둔다.** 신청은 진짜로 나가지만 명단은
     아직 붙박이다 — 안 적으면 다음 사람이 둘 다 진짜로 여긴다. */
  it('명단이 아직 예시라는 것을 적어 둔다', async () => {
    open()
    await screen.findByText('번개FC')
    expect(screen.getByText(/명단은 아직 예시입니다/)).toBeInTheDocument()
  })
})
