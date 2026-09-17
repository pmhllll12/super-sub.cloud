import { render, act } from '@testing-library/react'
import HomeStage from './HomeStage'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh: vi.fn() }),
  // 등장 애니메이션이 "이번에 인트로가 도는가" 를 경로로 판단한다
  // (`useIntroDone`) — 이미 본 것으로 쳐 바로 들어오게 둔다.
  usePathname: () => '/',
}))

/**
 * 🔴 **휠 한 번(튕김)은 기록에 한 걸음만 남겨야 한다.**
 *
 * 마우스 휠은 한 번 튕기면 `wheel` 이벤트가 **여러 개** 온다. 그 전부가 각자
 * 기록을 건드리면 내려갈 때 `pushState` 가 몇 번씩 쌓이고, 올라올 때
 * `history.back()` 이 몇 번씩 나가 **화면 밖으로 걸어 나간다** — 도메인에 올린
 * 뒤 데스크톱 사용자들이 겪은 것이 이것이다(영상 모음에서 휠을 올렸더니
 * `/market` 으로 가거나 사이트 밖으로 나갔다. 2026-09-06 헤드리스로 재현).
 *
 * 한 태스크 안에서 여러 개를 흘리는 것이 그 상황이다 — 실제로도 입력 큐에
 * 쌓인 휠들이 `popstate` 보다 먼저 처리되면서 전부 옛 상태를 본다.
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

describe('홈 — 굴림으로 영상 모음을 오간다', () => {
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

  it('휠 한 번을 세게 굴려도 기록은 한 걸음만 쌓인다', () => {
    setup()
    wheelBurst(100)
    expect(push).toHaveBeenCalledTimes(1)
  })

  it('영상 모음에서 휠을 올릴 때 뒤로 가기를 한 번만 부른다', () => {
    setup()
    wheelBurst(100)
    push.mockClear()
    wheelBurst(-100)
    expect(back).toHaveBeenCalledTimes(1)
  })

  it('기록에 우리 걸음이 없으면 뒤로 가기를 부르지 않는다 — 사이트를 벗어난다', () => {
    setup()
    wheelBurst(-100)
    expect(back).not.toHaveBeenCalled()
  })

  /**
   * 🔴 **글자를 치는 중에는 자판이 화면을 넘기지 않는다**(사용자 지적,
   * 2026-09-08: 챗봇에 「안녕하세요. 」까지 쳤더니 영상 모음으로 넘어갔다).
   *
   * 자판으로도 오갈 수 있어야 해서 `ArrowDown`·`PageDown`·**스페이스**를
   * 「내려가기」로 받는데, 그 셋은 글자를 치는 사람에게도 온다 — 스페이스는
   * **띄어쓰기**이고 화살표는 **글자 사이를 오가는 것**이다. 어디서 눌렀는지를
   * 보지 않으면 문장 한 줄을 못 쓴다.
   */
  function keyOn(target: Element | Window, key: string, init: KeyboardEventInit = {}) {
    act(() => {
      target.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true, ...init }))
    })
  }

  it.each(['ArrowDown', 'PageDown', ' '])(
    '글쇠 %s 를 입력칸에서 눌러도 영상 모음으로 안 넘어간다',
    (key) => {
      const { container } = setup()
      const input = document.createElement('input')
      container.appendChild(input)
      keyOn(input, key)
      expect(push).not.toHaveBeenCalled()
    },
  )

  it('챗봇 판 안에서 누른 글쇠는 화면을 안 넘긴다', () => {
    const { container } = setup()
    const panel = document.createElement('div')
    panel.className = 'ss-matchbot'
    const btn = document.createElement('button')
    panel.appendChild(btn)
    container.appendChild(panel)
    keyOn(btn, ' ')
    expect(push).not.toHaveBeenCalled()
  })

  it('한글을 조합하는 중에 온 글쇠는 화면을 안 넘긴다', () => {
    setup()
    // IME 가 조합 중일 때 브라우저가 보내는 것 — 글쇠는 아직 글자의 일부다.
    keyOn(window, ' ', { isComposing: true })
    expect(push).not.toHaveBeenCalled()
  })

  it('그래도 빈 자리에서 누르면 자판으로 넘어간다 — 길을 막지 않는다', () => {
    setup()
    keyOn(document.body, 'ArrowDown')
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
