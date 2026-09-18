import { render, act, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import HomeStage from './HomeStage'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh: vi.fn() }),
  // 등장 애니메이션이 "이번에 인트로가 도는가" 를 경로로 판단한다
  // (`useIntroDone`) — 이미 본 것으로 쳐 바로 들어오게 둔다.
  usePathname: () => '/',
}))

/**
 * 굴림을 흉내 낸다 — **아무 일도 안 일어나야** 한다는 것을 재기 위한 것이다.
 *
 * 🔴 한때 이것이 화면을 넘기는 **유일한 길**이었고, 그래서 여기 붙어 있던
 * 시험들은 「휠 한 번은 기록에 한 걸음만」·「글자를 치는 중엔 안 넘어간다」
 * 같은 것이었다. 길을 단추로 옮기면서(2026-09-18, 사용자 요청) 그 전부가
 * 필요 없어졌고, 대신 **굴림이 아무것도 안 한다**는 것을 붙든다 —
 * 예전 코드로 되돌리면 아래 셋이 빨개진다(되돌려서 확인했다).
 */
function wheelBurst(deltaY: number, n = 5) {
  act(() => {
    for (let k = 0; k < n; k++) {
      window.dispatchEvent(new WheelEvent('wheel', { deltaY, bubbles: true, cancelable: true }))
    }
  })
}

function setup() {
  return render(
    <HomeStage
      user={{ nickname: '홍길동' }}
      destinations={[]}
      featured={[]}
    />,
  )
}

describe('홈 — 눌러야만 영상 모음으로 간다', () => {
  let push: ReturnType<typeof vi.spyOn>
  let back: ReturnType<typeof vi.spyOn>

  // jsdom 의 `play()` 는 약속을 안 돌려줘서 `.catch` 에서 죽는다(영상 모음이
  // 내려오면 바로 튼다). 이 시험이 보는 것은 기록이지 재생이 아니다.
  beforeAll(() => {
    vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue(undefined)
    vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => {})
  })

  beforeEach(() => {
    window.history.replaceState(null, '')
    push = vi.spyOn(window.history, 'pushState')
    back = vi.spyOn(window.history, 'back').mockImplementation(() => {})
  })

  afterEach(() => {
    push.mockRestore()
    back.mockRestore()
  })

  /** 자판도 화면을 넘기지 않는다 — 단추에 얹힌 Enter·스페이스만 남는다. */
  function keyOn(target: Element | Window, key: string, init: KeyboardEventInit = {}) {
    act(() => {
      target.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true, ...init }))
    })
  }

  it('아무리 굴려도 영상 모음으로 안 내려간다', () => {
    setup()
    wheelBurst(100)
    expect(push).not.toHaveBeenCalled()
  })

  it('영상 모음에 내려가 있어도 굴림으로는 안 올라온다 — 워드마크만 올린다', async () => {
    setup()
    await userEvent.click(screen.getByRole('button', { name: /영상 둘러보기/ }))
    push.mockClear()
    wheelBurst(-100)
    expect(back).not.toHaveBeenCalled()
  })

  it.each(['ArrowDown', 'PageDown', ' ', 'ArrowUp', 'PageUp'])(
    '글쇠 %s 는 화면을 안 넘긴다 — 글을 치다 넘어가던 길을 없앴다',
    (key) => {
      setup()
      keyOn(document.body, key)
      expect(push).not.toHaveBeenCalled()
    },
  )

  /**
   * 🔴 **이것이 유일한 문이다.** 굴림을 걷어낸 뒤로 이 단추가 없으면 영상
   * 모음에 닿을 길이 아예 없다 — 이름이 바뀌거나 단추가 `<p>` 로 돌아가면
   * 여기서 잡힌다.
   */
  it('단추를 누르면 내려간다 — 기록에 한 걸음', async () => {
    setup()
    await userEvent.click(screen.getByRole('button', { name: /영상 둘러보기/ }))
    expect(push).toHaveBeenCalledTimes(1)
  })

  it('두 번 빠르게 눌러도 걸음은 하나다', async () => {
    setup()
    const hint = screen.getByRole('button', { name: /영상 둘러보기/ })
    await userEvent.click(hint)
    await userEvent.click(hint)
    expect(push).toHaveBeenCalledTimes(1)
  })
})

/**
 * 🔴 **수락하면 대기 화면이 뜬다 — 헤더와 판이 이어져 있는가** (2026-09-17).
 *
 * 사용자가 로컬에서 「수락하기 눌렀는데 왜 대기화면 안 뜸?」으로 잡았다.
 * 원인은 `SiteHeader` 와 `HomeStage` 가 **각각** `useNotifyInbox()` 를 불러서,
 * 헤더에서 수락한 결과가 대기 화면을 그리는 `SquadPanel` 쪽 통에 **영영 안
 * 들어간** 것이다.
 *
 * 🔴 **조각마다 시험이 통과해도 이어지는지는 따로 봐야 한다** — 그날 그걸
 * 안 봐서 사용자가 대신 잡았다. 그래서 이 시험은 **끝에서 끝까지** 간다:
 * 알림을 열고 → 수락하고 → 대기 화면이 뜨는지.
 */
describe('홈 — 경기 신청을 수락하면 대기 화면이 뜬다', () => {
  const REQUEST = {
    id: 'tmr0',
    requester_team_id: 'mt-away',
    target_team_id: 'team-mine',
    proposed_played_at: '2026-09-19T09:00:00+09:00',
    proposed_place: '망원 실내구장 A',
    status: 'pending',
    match_id: null,
    requester_team_name: '망원 유나이티드',
    requester_team_region: '서울 마포구',
    target_team_name: '번개FC',
    target_team_region: '서울 강남구',
    requester_squad_public_slug: null,
    target_squad_public_slug: null,
  }

  afterEach(() => vi.unstubAllGlobals())

  it('헤더에서 수락한 결과가 판까지 닿는다', async () => {
    const { screen, waitFor } = await import('@testing-library/react')
    const userEvent = (await import('@testing-library/user-event')).default

    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((url: string) => {
        const u = String(url)
        const body = u.endsWith('/api/me')
          ? { teams: [{ team_id: 'team-mine', role: 'owner', name: '번개FC' }] }
          : u.includes('/match-requests')
            ? [REQUEST]
            : []
        return Promise.resolve({ ok: true, status: 200, json: async () => body })
      }),
    )

    render(
      <HomeStage
        user={{ nickname: '홍길동' }}
        destinations={[{ title: '알림', icon: 'circle_notifications', summary: '받은 신청' }]}
        featured={[]}
      />,
    )

    await userEvent.click(await screen.findByRole('button', { name: /알림/ }))
    await userEvent.click(await screen.findByRole('button', { name: '수락하기' }))

    // 🔴 **이 한 줄이 「이어져 있는가」다** — 조각 시험으로는 안 잡힌다.
    await waitFor(() =>
      expect(screen.getByRole('dialog', { name: '경기가 잡혔습니다' })).toBeInTheDocument(),
    )
  })
})
