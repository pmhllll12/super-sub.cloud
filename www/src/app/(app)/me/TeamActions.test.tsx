import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TeamActions from './TeamActions'

const refresh = vi.fn()
vi.mock('next/navigation', () => ({ useRouter: () => ({ refresh }) }))

/**
 * **팀 만들기 · 나가기** (계약 3-3절, 2026-09-16).
 *
 * 🔴 계약(`POST /teams`)은 처음부터 있었는데 **화면이 없어서 실제로는 팀을
 * 만들 방법이 없었다.** 팀이 없으면 스쿼드 · 경기 신청 · 알림이 전부 막힌다.
 */
describe('프로필 — 소속', () => {
  let sent: { url: string; method: string; body: string | null }[]

  function stub(fail?: { status: number; code: string; message: string }) {
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        sent.push({
          url,
          method: init?.method ?? 'GET',
          body: typeof init?.body === 'string' ? init.body : null,
        })
        if (fail && init?.method === 'DELETE') {
          return Promise.resolve(
            new Response(JSON.stringify({ error: { code: fail.code, message: fail.message } }), {
              status: fail.status,
            }),
          )
        }
        return Promise.resolve(new Response(JSON.stringify({ id: 't9' }), { status: 201 }))
      },
    )
  }

  beforeEach(() => {
    sent = []
    refresh.mockClear()
    stub()
  })

  afterEach(() => vi.restoreAllMocks())

  /**
   * 🔴 **접혀 있을 뿐 DOM 에는 있다**(2026-09-16). 부드럽게 펴지려면 전환할
   * 대상이 있어야 해서 `{open && …}` 로 붙였다 뗐다 하지 않는다.
   *
   * 그래서 **탭으로 못 닿게** 하는 것이 중요하다 — 안 그러면 눈에 안 보이는
   * 입력칸에 커서가 들어간다. `aria-hidden` 은 포커스를 막지 못해 `inert` 다.
   */
  it('평소에는 폼이 접혀 있고 탭으로도 못 닿는다', () => {
    const { container } = render(<TeamActions teams={[]} userId="u1" />)
    expect(screen.getByRole('button', { name: '팀 만들기' })).toBeInTheDocument()
    const fold = container.querySelector('.ss-profile-form-fold')
    expect(fold).toHaveAttribute('data-open', 'false')
    expect(fold?.firstElementChild).toHaveAttribute('inert')
  })

  it('펴면 닿을 수 있게 된다', async () => {
    const user = userEvent.setup()
    const { container } = render(<TeamActions teams={[]} userId="u1" />)
    await user.click(screen.getByRole('button', { name: '팀 만들기' }))
    const fold = container.querySelector('.ss-profile-form-fold')
    expect(fold).toHaveAttribute('data-open', 'true')
    expect(fold?.firstElementChild).not.toHaveAttribute('inert')
  })

  /* 🔴 **종목을 안 묻는다**(사용자 결정) — 풋살만 다룬다. BFF 가 채운다. */
  it('이름과 지역만 묻는다 — 종목은 안 묻는다', async () => {
    const user = userEvent.setup()
    render(<TeamActions teams={[]} userId="u1" />)
    await user.click(screen.getByRole('button', { name: '팀 만들기' }))
    expect(screen.getByLabelText('팀 이름')).toBeInTheDocument()
    /* ⚠️ 라벨이 「지역 (예: 서울 강남)」이다 — 예시를 칸 아래가 아니라 **라벨 옆
       괄호**로 옮겼다(2026-09-16, 사용자 요청). 접근성 이름도 그 전체다:
       보이는 글자가 이름에 들어 있어야 한다는 규칙(label in name)을 지키려면
       `aria-label` 로 「지역」만 따로 주면 안 된다. */
    expect(screen.getByLabelText(/지역/)).toBeInTheDocument()
    expect(screen.queryByLabelText(/종목/)).toBeNull()
  })

  /* 🔴 **스쿼드도 같이 연다.** 팀만 만들면 홈 판이 404 로 빈 채 뜨고, 거기
     넣은 사람이 서버에 안 남는다. */
  it('만들면 팀과 스쿼드를 함께 연다', async () => {
    const user = userEvent.setup()
    render(<TeamActions teams={[]} userId="u1" />)
    await user.click(screen.getByRole('button', { name: '팀 만들기' }))
    await user.type(screen.getByLabelText('팀 이름'), '번개FC')
    await user.type(screen.getByLabelText(/지역/), '서울 강남')
    await user.click(screen.getByRole('button', { name: '만들기' }))

    await waitFor(() => expect(refresh).toHaveBeenCalled())
    const made = sent.find((s) => s.url === '/api/teams' && s.method === 'POST')
    expect(made).toBeDefined()
    expect(JSON.parse(made!.body!)).toEqual({ name: '번개FC', region: '서울 강남' })
    expect(sent.some((s) => s.url === '/api/teams/t9/squad')).toBe(true)
  })

  /* 🔴 `member_id` 는 곧 `user_id` 다 — 소속 행의 id 가 아니다. */
  it('나가기는 내 user_id 로 나간다', async () => {
    const user = userEvent.setup()
    render(<TeamActions teams={[{ team_id: 't1', name: '번개FC', region: '서울 강남', sport_code: 'futsal', role: 'member' }]} userId="u1" />)
    await user.click(screen.getByRole('button', { name: '팀 나가기' }))

    await waitFor(() => expect(refresh).toHaveBeenCalled())
    expect(sent.some((s) => s.url === '/api/teams/t1/members/u1' && s.method === 'DELETE')).toBe(
      true,
    )
  })

  /**
   * 🔴 **마지막 주장은 못 나간다** — 화면에서 미리 막지 않는다. 주장이 몇인지는
   * 서버만 알고, 화면이 짐작해 막으면 나갈 수 있는 사람까지 막힌다.
   */
  it('마지막 주장이면 서버가 준 이유를 그대로 보여 준다', async () => {
    stub({ status: 409, code: 'LAST_OWNER', message: '마지막 주장은 팀을 나갈 수 없습니다.' })
    const user = userEvent.setup()
    render(<TeamActions teams={[{ team_id: 't1', name: '번개FC', region: '서울 강남', sport_code: 'futsal', role: 'owner' }]} userId="u1" />)
    // 🔴 단추가 **눌린다** — 막아 두지 않는다.
    await user.click(screen.getByRole('button', { name: '팀 나가기' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('마지막 주장은 팀을 나갈 수 없습니다.')
  })
})

/**
 * 🔴 **팀이 있으면 만들 자리를 안 낸다**(사용자 요청, 2026-09-16).
 *
 * 지금 홈은 `teams[0]` 하나만 본다 — 둘째 팀을 만들 수 있게 두면 만들고도
 * 화면 어디에도 안 보이는 팀이 생긴다. 나가고 나면 다시 나온다.
 */
describe('프로필 — 팀 만들기가 나오는 때', () => {
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify({ id: 't9' }), { status: 201 })),
    )
  })
  afterEach(() => vi.restoreAllMocks())

  const TEAM = {
    team_id: 't1',
    name: '번개FC',
    region: '서울 강남',
    sport_code: 'futsal',
    role: 'member',
  }

  /**
   * 🔴 **팀이 있어도 만들 수 있다**(사용자 지적, 2026-09-16 — 「마지막 주장이어도
   * 새로 만들고 싶을 수 있다」). 계약에 팀 해체도 소유권 이양도 없어서 마지막
   * 주장은 나갈 수가 없는데, 만들 자리까지 막으면 새 팀을 시작할 길이 없다.
   */
  it('팀이 있어도 만들기가 나온다', () => {
    render(<TeamActions teams={[TEAM]} userId="u1" />)
    expect(screen.getByRole('button', { name: '팀 만들기' })).toBeInTheDocument()
    // 나가기는 팀 이름과 같은 줄에 있다.
    const line = screen.getByText('번개FC').closest('.ss-profile-team-name')
    expect(line?.querySelector('button')).toHaveTextContent('팀 나가기')
  })

  /* 🔴 **정정 (2026-09-16, 사용자 요청)**: 앞서 「팀을 만들어야 스쿼드와 경기
     신청을 쓸 수 있습니다」까지 적게 붙들던 것을 걷었다 — 바로 아래에 「팀
     만들기」 단추가 서 있어 **같은 말을 두 번** 하는 자리였다. */
  it('팀이 없으면 한 줄로만 적고 만들 자리를 낸다', () => {
    render(<TeamActions teams={[]} userId="u1" />)
    expect(screen.getByRole('button', { name: '팀 만들기' })).toBeInTheDocument()
    expect(screen.getByText('아직 소속된 팀이 없습니다.')).toBeInTheDocument()
    expect(screen.queryByText(/팀을 만들어야/)).toBeNull()
  })

  /* 🔴 **홈은 한 팀만 그린다.** 만들 수 있게 열었으니 고를 자리도 있어야
     한다 — 없으면 새로 만든 팀이 홈에 안 보인다. */
  it('소속이 하나뿐이면 고를 자리가 없다', () => {
    render(<TeamActions teams={[TEAM]} userId="u1" homeTeamId="t1" />)
    expect(screen.queryByRole('button', { name: /홈에/ })).toBeNull()
  })

  it('소속이 여럿이면 홈에 보일 팀을 고른다', () => {
    const second = { ...TEAM, team_id: 't2', name: '새벽FC' }
    render(<TeamActions teams={[TEAM, second]} userId="u1" homeTeamId="t1" />)
    expect(screen.getByRole('button', { name: '홈에 보이는 팀' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getByRole('button', { name: '홈에 이 팀 보기' })).toHaveAttribute(
      'aria-pressed',
      'false',
    )
  })
})
