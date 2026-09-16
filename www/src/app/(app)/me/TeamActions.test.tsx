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

  it('평소에는 폼이 접혀 있다', () => {
    render(<TeamActions teams={[]} userId="u1" />)
    expect(screen.getByRole('button', { name: '팀 만들기' })).toBeInTheDocument()
    expect(screen.queryByLabelText('팀 이름')).toBeNull()
  })

  /* 🔴 **종목을 안 묻는다**(사용자 결정) — 풋살만 다룬다. BFF 가 채운다. */
  it('이름과 지역만 묻는다 — 종목은 안 묻는다', async () => {
    const user = userEvent.setup()
    render(<TeamActions teams={[]} userId="u1" />)
    await user.click(screen.getByRole('button', { name: '팀 만들기' }))
    expect(screen.getByLabelText('팀 이름')).toBeInTheDocument()
    expect(screen.getByLabelText('지역')).toBeInTheDocument()
    expect(screen.queryByLabelText(/종목/)).toBeNull()
  })

  /* 🔴 **스쿼드도 같이 연다.** 팀만 만들면 홈 판이 404 로 빈 채 뜨고, 거기
     넣은 사람이 서버에 안 남는다. */
  it('만들면 팀과 스쿼드를 함께 연다', async () => {
    const user = userEvent.setup()
    render(<TeamActions teams={[]} userId="u1" />)
    await user.click(screen.getByRole('button', { name: '팀 만들기' }))
    await user.type(screen.getByLabelText('팀 이름'), '번개FC')
    await user.type(screen.getByLabelText('지역'), '서울 강남')
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
    await user.click(screen.getByRole('button', { name: '나가기' }))

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
    await user.click(screen.getByRole('button', { name: '나가기' }))

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

  it('팀이 있으면 만들기가 없다', () => {
    render(<TeamActions teams={[TEAM]} userId="u1" />)
    expect(screen.queryByRole('button', { name: '팀 만들기' })).toBeNull()
    // 나가기는 팀 이름과 같은 줄에 있다.
    const line = screen.getByText('번개FC').closest('.ss-profile-team-name')
    expect(line?.querySelector('button')).toHaveTextContent('나가기')
  })

  it('팀이 없으면 만들기가 나온다', () => {
    render(<TeamActions teams={[]} userId="u1" />)
    expect(screen.getByRole('button', { name: '팀 만들기' })).toBeInTheDocument()
    expect(screen.getByText(/팀을 만들어야/)).toBeInTheDocument()
  })
})
