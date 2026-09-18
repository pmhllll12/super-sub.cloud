import { fireEvent, render, screen, waitFor } from '@testing-library/react'
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
        if (u.includes('/match-candidates')) {
          return Promise.resolve(
            new Response(
              JSON.stringify([
                {
                  team_id: 'mt-a',
                  team_name: '망원 유나이티드',
                  region_label: '서울 마포구',
                  formation: '5:5',
                  reasons: [{ kind: 'time', detail: '토요일 11:00~12:00 겹침' }],
                },
                {
                  team_id: 'mt-b',
                  team_name: '성수 웨이브',
                  region_label: '서울 성동구',
                  formation: '5:5',
                  reasons: [],
                },
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

  /**
   * ✅ **명단이 서버 것이 됐다** (CCC 40번, 2026-09-17).
   *
   * 🔴 여기 있던 시험들은 **일부러 없앤 동작**을 붙들고 있었다 — 화면이
   * 붙박이 7팀을 **판 크기로 거르고** `whyMatches()` 로 **근거를 다시
   * 계산하던** 것이다. 계약이 그 둘을 서버로 옮겼고, 「하지 말 것」에
   * **다시 계산하지 말라**고 못 박았다(다시 계산하면 서버와 다른 답이 나온다).
   */
  it('서버가 준 이름·지역·근거를 그대로 그린다', async () => {
    open()
    expect(await screen.findByText('망원 유나이티드')).toBeInTheDocument()
    expect(screen.getByText('토요일 11:00~12:00 겹침')).toBeInTheDocument()
  })

  /**
   * 🔴 **화면이 다시 거르지 않는다.** 판 크기·자기 팀 제외·로스터 충원은
   * 서버가 하드 필터로 이미 걸렀다 — 여기서 또 거르면 서버가 준 목록이
   * 화면에서 조용히 줄어든다.
   */
  it('판 크기로 다시 거르지 않는다 — 서버가 준 만큼 그린다', async () => {
    render(
      <TeamMatch
        size="7"
        closing={false}
        onClose={() => {}}
        teamId={MY_TEAM}
        onRequested={vi.fn()}
      />,
    )
    // 대역이 주는 것은 5:5 둘인데, 우리 판이 7:7 이어도 그대로 온다.
    expect(await screen.findByText('망원 유나이티드')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: '경기 신청' })).toHaveLength(2)
  })

  /* 🔴 소프트 근거가 0개인 줄도 정상이다 — 하드 필터는 통과했다. */
  it('근거가 없는 후보도 목록에 남는다', async () => {
    open()
    expect(await screen.findByText('성수 웨이브')).toBeInTheDocument()
  })

  /**
   * 🔴 **바로 신청하지 않는다.** 후보에는 경기 시각·구장이 **없어서**(팀
   * 후보이지 경기 공고가 아니다) 그 둘을 먼저 고른다 — 화면이 채우면
   * 아무도 못 뛰는 경기가 잡힌다.
   */
  it('신청하기를 누르면 시각·구장을 먼저 고르게 한다', async () => {
    const user = userEvent.setup()
    open()
    await screen.findByText('망원 유나이티드')

    await user.click(screen.getAllByRole('button', { name: '경기 신청' })[0])

    /* 🔴 **열자마자 쓸 수 있는 시각이 채워져 있다**(2026-09-18) — 비워
       두었더니 달력에서 날짜만 고르고 시각이 `00:00` 으로 남아 「지난
       시각입니다」에 걸렸다. 그래서 제안 줄(「언제」) 대신 이 칸이 먼저 뜬다. */
    const at = screen.getByLabelText('직접 고르기') as HTMLInputElement
    expect(at.value).not.toBe('')
    expect(new Date(at.value).getTime()).toBeGreaterThan(Date.now())

    expect(screen.getByText('어디서')).toBeInTheDocument()
    // 구장을 안 골랐으면 못 보낸다.
    expect(screen.getByRole('button', { name: '이 시각으로 신청' })).toBeDisabled()
  })

  /* 🔴 **시각은 우리 조건에서 온다** — 지어내지 않는다. 조건이 토요일뿐이면
     고를 수 있는 것도 토요일뿐이다.

     🔴 **직접 고르기 칸을 비워야 제안이 나온다**(2026-09-18) — 둘이 같이
     떠 있으면 어느 것이 쓰이는지 알 수 없어서, 직접 고른 값이 있으면
     제안을 안 그린다. **제안을 없앤 것이 아니라는 것**이 이 시험이다. */
  it('직접 고르기를 비우면 우리 조건에서 나온 시각이 돌아온다', async () => {
    const user = userEvent.setup()
    open()
    await screen.findByText('망원 유나이티드')
    await user.click(screen.getAllByRole('button', { name: '경기 신청' })[0])

    // 채워져 있는 동안에는 제안 줄이 없다.
    expect(screen.queryByText('언제')).toBeNull()

    fireEvent.change(screen.getByLabelText('직접 고르기'), { target: { value: '' } })

    const when = screen.getByText('언제').closest('label')?.querySelector('select')
    expect(when).not.toBeNull()
    expect(when?.options).toHaveLength(1)
    expect(when?.options[0].textContent).toContain('토')
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
    await screen.findByText('망원 유나이티드')
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
    await screen.findByText('망원 유나이티드')

    /* 🔴 **두 단계다**(2026-09-17) — 후보에는 시각·구장이 없어서 먼저 고른다. */
    await user.click(screen.getAllByRole('button', { name: '경기 신청' })[0])
    const place = screen.getByText('어디서').closest('label')!.querySelector('select')!
    await user.selectOptions(place, place.options[1].value)
    await user.click(screen.getByRole('button', { name: '이 시각으로 신청' }))

    await waitFor(() => expect(onRequested).toHaveBeenCalled())
    const sent = calls.find((c) => c.url === `/api/teams/${MY_TEAM}/match-requests`)
    expect(sent).toBeDefined()
    const body = JSON.parse(sent!.body!)
    expect(body.target_team_id).toBe('mt-a')
    /* 🔴 **고른 값이 그대로 나간다** — 지어낸 시각·구장이 아니다. 그리고
       시각은 `toISOString()`(UTC) 이 아니라 **고른 현지 시각**이다. */
    expect(body.place).toBe(place.options[1].value)
    expect(body.played_at).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:00[+-]\d{2}:\d{2}$/)

    // 🔴 **대기 팝업을 띄우라고 하지 않는다** — 넘기는 것은 신청 id 다.
    expect(onRequested.mock.calls[0][0]).toBe('tmr9')
    expect(await screen.findByRole('button', { name: '상대 수락 대기 중' })).toBeInTheDocument()
  })

  /* 🔴 **한 번에 한 곳에만 신청한다.** 여러 곳에 걸어 두면 둘이 동시에
     수락했을 때 어느 경기가 잡힌 것인지 화면이 답할 수 없다. */
  it('기다리는 동안 다른 팀에는 신청하지 못한다', async () => {
    const user = userEvent.setup()
    open()
    await screen.findByText('망원 유나이티드')

    await user.click(screen.getAllByRole('button', { name: '경기 신청' })[0])
    const place = screen.getByText('어디서').closest('label')!.querySelector('select')!
    await user.selectOptions(place, place.options[1].value)
    await user.click(screen.getByRole('button', { name: '이 시각으로 신청' }))

    await screen.findByRole('button', { name: '상대 수락 대기 중' })
    for (const b of screen.getAllByRole('button', { name: '경기 신청' })) {
      expect(b).toBeDisabled()
    }
  })

  /* 🔴 **어디까지가 진짜인지 적어 둔다.** 신청은 진짜로 나가지만 명단은
     아직 붙박이다 — 안 적으면 다음 사람이 둘 다 진짜로 여긴다. */
  /* 🔴 **「예시입니다」를 걷었다**(2026-09-17) — 명단이 진짜가 됐으므로 그
     문구가 이제 거짓이다. 붙박이로 되돌아가면 이 시험이 먼저 빨개진다. */
  it('명단이 예시라고 적지 않는다 — 이제 서버 것이다', async () => {
    open()
    await screen.findByText('망원 유나이티드')
    expect(screen.queryByText(/명단은 아직 예시입니다/)).toBeNull()
    expect(screen.getByText(/수락해야 경기가 잡힙니다/)).toBeInTheDocument()
  })

  /**
   * **시각을 직접 고른다** (사용자 요청, 2026-09-18 — 시연 촬영).
   *
   * 🔴 **제안만으로는 오늘 경기를 못 잡는다.** 제안은 조건(요일+시간대)에서
   * 「다음에 오는 그 요일」로 만들어져서, 조건이 토요일뿐이면 **다음 토요일**
   * 이다. 시연에서는 **1분 뒤**로 잡아야 대기 화면 → 경기 끝내기 → 리뷰까지
   * 한자리에서 보여 줄 수 있다.
   *
   * 🔴 **제안을 없애지 않는다** — 평소에는 그쪽이 맞다(「지어내지 않는다」).
   * 직접 고르기는 그 옆에 붙는 길이다.
   */
  it('시각을 직접 고를 수 있다', async () => {
    const user = userEvent.setup()
    open()
    await screen.findByText('망원 유나이티드')
    await user.click(screen.getAllByRole('button', { name: '경기 신청' })[0])

    expect(screen.getByLabelText('직접 고르기')).toBeInTheDocument()
  })

  it('직접 고른 시각이 신청에 실린다', async () => {
    const user = userEvent.setup()
    open()
    await screen.findByText('망원 유나이티드')
    await user.click(screen.getAllByRole('button', { name: '경기 신청' })[0])

    fireEvent.change(screen.getByLabelText('직접 고르기'), {
      target: { value: '2027-03-04T19:30' },
    })
    await user.selectOptions(
      screen.getByText('어디서').closest('label')!.querySelector('select')!,
      screen.getByText('어디서').closest('label')!.querySelectorAll('option')[1].value,
    )
    await user.click(screen.getByRole('button', { name: '이 시각으로 신청' }))

    await waitFor(() => {
      const req = calls.find((c) => c.url.includes('/match-requests'))
      expect(req).toBeTruthy()
      expect(JSON.parse(req!.body!).played_at).toContain('2027-03-04T19:30')
    })
  })

  /* 🔴 **지난 시각은 막는다** — 서버가 받아 줘도 아무도 못 뛴다
     (`matchProposal.ts` 의 「지난 시각으로 신청하면」 주석과 같은 판단). */
  it('지난 시각으로는 신청이 안 눌린다', async () => {
    const user = userEvent.setup()
    open()
    await screen.findByText('망원 유나이티드')
    await user.click(screen.getAllByRole('button', { name: '경기 신청' })[0])

    fireEvent.change(screen.getByLabelText('직접 고르기'), {
      target: { value: '2020-01-01T09:00' },
    })
    expect(screen.getByRole('button', { name: '이 시각으로 신청' })).toBeDisabled()
  })

  /**
   * 🔴 **시간 조건이 비어도 신청은 할 수 있어야 한다** (2026-09-18).
   *
   * 시간을 비우는 것은 **정상적인 길**이다 — 그래야 AI 추천 후보 필터가
   * 풀린다(프로필의 「시간 조건 지우기」). 그런데 전에는 여기서 제안이
   * 0개라고 판이 통째로 닫혀서, **필터를 푼 팀은 경기를 못 거는** 앞뒤가
   * 안 맞는 상태가 됐다.
   */
  it('조건에 시간이 없어도 직접 골라 신청할 수 있다', async () => {
    __resetRegionsCache()
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const u = String(input)
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
      if (u.includes('/match-candidates')) {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              {
                team_id: 'mt-a',
                team_name: '망원 유나이티드',
                region_label: '서울 마포구',
                formation: '5:5',
                reasons: [],
              },
            ]),
            { status: 200 },
          ),
        )
      }
      if (u.includes('/match-preferences')) {
        // 🔴 지역만 있고 **시간은 비어 있다** — 「시간 조건 지우기」를 쓴 뒤다.
        return Promise.resolve(
          new Response(
            JSON.stringify({ team_id: MY_TEAM, region_ids: ['rg-001'], slots: [] }),
            { status: 200 },
          ),
        )
      }
      return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }))
    })

    const user = userEvent.setup()
    open()
    await screen.findByText('망원 유나이티드')
    await user.click(screen.getAllByRole('button', { name: '경기 신청' })[0])

    // 판이 닫히지 않는다 — 직접 고르는 칸이 있다.
    expect(screen.getByLabelText('직접 고르기')).toBeInTheDocument()
  })

  /**
   * **판 안에서 굴리면 페이지가 안 움직인다** (사용자 지적, 2026-09-18).
   *
   * 「A팀 매칭 판에서 다른 팀 보려고 스크롤 하면 아예 비디오 여기로 내려와」
   *
   * 🔴 `.ss-tm-list` 에는 이미 `overscroll-behavior: contain` 이 있었다.
   * 새는 자리는 **목록 밖**이다 — 머리줄(「설정 수정」)이나 아래 안내
   * (「신청은 상대 팀장에게 갑니다」) 위에서 굴리면 그 휠은 목록이 아니라
   * **페이지**로 가고, 홈은 아래가 영상 모음이라 거기까지 내려간다.
   */
  it('목록 밖에서 굴려도 페이지로 안 넘긴다', async () => {
    open()
    await screen.findByText('망원 유나이티드')

    const foot = screen.getByText(/수락해야 경기가 잡힙니다/)
    const ev = new WheelEvent('wheel', { deltaY: 120, bubbles: true, cancelable: true })
    foot.dispatchEvent(ev)

    expect(ev.defaultPrevented).toBe(true)
  })

  /* 🔴 **목록이 아직 구를 수 있으면 막지 않는다** — 막아 버리면 목록 자체가
     안 움직인다. 페이지로 넘어가는 것만 막는 것이 요점이다. */
  it('목록이 구를 수 있으면 그 휠은 그대로 둔다', async () => {
    open()
    await screen.findByText('망원 유나이티드')

    const list = document.querySelector('.ss-tm-list') as HTMLElement
    // jsdom 은 크기를 안 재므로 구를 여지가 있다고 알려 준다.
    Object.defineProperty(list, 'scrollHeight', { value: 900, configurable: true })
    Object.defineProperty(list, 'clientHeight', { value: 300, configurable: true })
    list.scrollTop = 0

    const ev = new WheelEvent('wheel', { deltaY: 120, bubbles: true, cancelable: true })
    list.dispatchEvent(ev)

    expect(ev.defaultPrevented).toBe(false)
  })
})
