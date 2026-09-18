import { render, screen, waitFor, within } from '@testing-library/react'
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
    /* 🔴 **목록의 값이어야 한다**(2026-09-17, 계약 52번과 함께 바뀜) — 전에는
       자유 입력이라 「서울 강남」으로도 만들어졌는데, 그러면 「사람을 찾는 팀」
       이 지역으로 거를 때 그 팀이 통째로 빠진다. */
    await user.type(screen.getByLabelText(/지역/), '서울 강남구')
    await user.click(screen.getByRole('button', { name: '만들기' }))

    await waitFor(() => expect(refresh).toHaveBeenCalled())
    const made = sent.find((s) => s.url === '/api/teams' && s.method === 'POST')
    expect(made).toBeDefined()
    expect(JSON.parse(made!.body!)).toEqual({ name: '번개FC', region: '서울 강남구' })
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

/**
 * **팀 이름·지역 수정** (계약 3-3절 `PATCH /teams/{id}`, CCC 52번, 2026-09-17).
 *
 * 🔴 **왜 급했나**: 「사람을 찾는 팀」이 지역으로 거르는데 그 값이
 * `team.region` 이다 — 오타를 내거나 연고를 옮기면 **그 팀 경기가 탐색에서
 * 통째로 빠지는데 고칠 방법이 없었다.**
 *
 * ⚠️ **질의를 수정 폼 안으로 좁힌다**(`within`). 팀 만들기 폼은 접혀 있을 뿐
 * **늘 DOM 에 있어서**(부드럽게 펴지려면 전환할 대상이 있어야 한다) 「팀
 * 이름」·「지역」 라벨이 화면에 둘씩 있다 — 안 좁히면 질의가 둘 다 집는다.
 */
describe('프로필 — 팀 이름·지역 수정', () => {
  let sent: { url: string; method: string; body: string | null }[]

  const OWNED = {
    team_id: 't1',
    name: '번개FC',
    region: '서울 강남구',
    sport_code: 'football',
    role: 'owner',
  }

  /** 팀 줄 안의 수정 폼 — 만들기 폼은 `<ul>` 밖에 있어 `li` 로 갈린다. */
  function editForm(container: HTMLElement) {
    return within(container.querySelector('li .ss-profile-form-fold') as HTMLElement)
  }

  beforeEach(() => {
    sent = []
    refresh.mockClear()
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        sent.push({
          url: String(input),
          method: init?.method ?? 'GET',
          body: typeof init?.body === 'string' ? init.body : null,
        })
        return Promise.resolve(new Response(JSON.stringify({ id: 't1' }), { status: 200 }))
      },
    )
  })
  afterEach(() => vi.restoreAllMocks())

  /* 🔴 **주장만**(계약) — 구성원이 부르면 403 이다. */
  it('구성원에게는 수정 단추를 안 낸다', () => {
    render(<TeamActions teams={[{ ...OWNED, role: 'member' }]} userId="u1" />)
    expect(screen.queryByRole('button', { name: '수정' })).toBeNull()
  })

  it('주장에게는 수정 단추가 나온다', () => {
    render(<TeamActions teams={[OWNED]} userId="u1" />)
    expect(screen.getByRole('button', { name: '수정' })).toBeInTheDocument()
  })

  /* 평소에는 접혀 있고 탭으로도 못 닿는다 — 만들기 폼과 같은 방식이다. */
  it('평소에는 수정 폼이 접혀 있다', () => {
    const { container } = render(<TeamActions teams={[OWNED]} userId="u1" />)
    const fold = container.querySelector('li .ss-profile-form-fold')
    expect(fold).toHaveAttribute('data-open', 'false')
    expect(fold?.firstElementChild).toHaveAttribute('inert')
  })

  /* 빈 칸에서 시작하면 안 바꿀 필드까지 사람이 다시 적게 된다. */
  it('펴면 지금 값으로 채워져 있다', async () => {
    const user = userEvent.setup()
    const { container } = render(<TeamActions teams={[OWNED]} userId="u1" />)
    await user.click(screen.getByRole('button', { name: '수정' }))
    const f = editForm(container)
    expect(f.getByLabelText('팀 이름')).toHaveValue('번개FC')
    expect(f.getByLabelText(/지역/)).toHaveValue('서울 강남구')
  })

  /**
   * 🔴 **바뀐 것만 싣는다**(계약의 「하지 말 것」) — 안 바꿀 필드는 `null` 도
   * 빈 값도 아니고 **아예 빼야** 한다. `null` 을 보내면 422 다.
   */
  it('이름만 고치면 name 만 보낸다', async () => {
    const user = userEvent.setup()
    const { container } = render(<TeamActions teams={[OWNED]} userId="u1" />)
    await user.click(screen.getByRole('button', { name: '수정' }))
    const f = editForm(container)
    await user.clear(f.getByLabelText('팀 이름'))
    await user.type(f.getByLabelText('팀 이름'), '천둥FC')
    await user.click(f.getByRole('button', { name: '저장' }))

    await waitFor(() => expect(refresh).toHaveBeenCalled())
    const patch = sent.find((s) => s.method === 'PATCH')
    expect(patch?.url).toBe('/api/teams/t1')
    expect(JSON.parse(patch!.body!)).toEqual({ name: '천둥FC' })
  })

  it('지역만 고치면 region 만 보낸다', async () => {
    const user = userEvent.setup()
    const { container } = render(<TeamActions teams={[OWNED]} userId="u1" />)
    await user.click(screen.getByRole('button', { name: '수정' }))
    const f = editForm(container)
    await user.clear(f.getByLabelText(/지역/))
    await user.type(f.getByLabelText(/지역/), '부산 해운대구')
    await user.click(f.getByRole('button', { name: '저장' }))

    await waitFor(() => expect(refresh).toHaveBeenCalled())
    expect(JSON.parse(sent.find((s) => s.method === 'PATCH')!.body!)).toEqual({
      region: '부산 해운대구',
    })
  })

  /* 둘 다 그대로면 부를 것이 없다 — 접기만 한다. */
  it('아무것도 안 바꾸면 서버를 안 부른다', async () => {
    const user = userEvent.setup()
    const { container } = render(<TeamActions teams={[OWNED]} userId="u1" />)
    await user.click(screen.getByRole('button', { name: '수정' }))
    await user.click(editForm(container).getByRole('button', { name: '저장' }))
    expect(sent.some((s) => s.method === 'PATCH')).toBe(false)
  })

  /**
   * 🔴 **저장되는 값은 목록의 것**이다 — 「강남」·「강남구」·「서울 강남구」가
   * 다 다른 값이면 대조가 깨져서, 고쳐도 여전히 탐색에서 빠진다.
   */
  it('목록에 없는 동네면 저장이 안 눌리고 그렇게 말한다', async () => {
    const user = userEvent.setup()
    const { container } = render(<TeamActions teams={[OWNED]} userId="u1" />)
    await user.click(screen.getByRole('button', { name: '수정' }))
    const f = editForm(container)
    await user.clear(f.getByLabelText(/지역/))
    await user.type(f.getByLabelText(/지역/), '없는동네')

    expect(f.getByRole('button', { name: '저장' })).toBeDisabled()
    expect(f.getByText('그런 동네가 목록에 없습니다.')).toBeInTheDocument()
  })

  it('적은 것과 겹치는 동네를 후보로 내고, 누르면 그 값이 된다', async () => {
    const user = userEvent.setup()
    const { container } = render(<TeamActions teams={[OWNED]} userId="u1" />)
    await user.click(screen.getByRole('button', { name: '수정' }))
    const f = editForm(container)
    await user.clear(f.getByLabelText(/지역/))
    await user.type(f.getByLabelText(/지역/), '해운대')
    await user.click(f.getByRole('button', { name: '부산 해운대구' }))

    expect(f.getByLabelText(/지역/)).toHaveValue('부산 해운대구')
    expect(f.getByRole('button', { name: '저장' })).toBeEnabled()
  })

  /* 🔴 **종목은 못 바꾼다** — 계약 본문에 자리가 없고, 포지션·스쿼드·경기가
     전부 그 값에 매달려 있다. */
  it('종목을 고치는 자리는 없다', async () => {
    const user = userEvent.setup()
    const { container } = render(<TeamActions teams={[OWNED]} userId="u1" />)
    await user.click(screen.getByRole('button', { name: '수정' }))
    expect(editForm(container).queryByLabelText(/종목/)).toBeNull()
  })
})

/**
 * **주장도 팀을 버릴 수 있다 — 해체** (사용자 지적, 2026-09-18).
 *
 * 「팀원들도 나가고 사실 팀장도 팀 해체 할 수 있어야 하는게 당연한거 아님?
 * 1명밖에 없어도 나가기 누르면 해체 할 수 있어야 하잖아」
 *
 * 🔴 여태 주장이 「팀 나가기」를 누르면 `409 LAST_OWNER` 를 받고 **거기서
 * 끝이었다.** 계약은 2026-09-17에 이미 길을 냈는데(`DELETE /teams/{id}`,
 * 미결 `paik` 35번) 화면이 그 길로 잇지를 않았다 — 혼자 만든 팀을 **버릴
 * 방법이 아예 없었다.**
 *
 * 🔴 **화면이 미리 판단하지 않는다.** 주장이 몇인지는 서버만 알므로, 나가기를
 * 눌러 보고 **서버가 `LAST_OWNER` 라고 답했을 때만** 해체를 권한다. 미리
 * 가르면 주장이 둘인 팀에서 나갈 수 있는 사람에게 해체를 들이민다.
 */
describe('프로필 — 마지막 주장의 팀 해체', () => {
  const refreshed = refresh
  const OWNER = [
    { team_id: 't1', name: '번개FC', region: '서울 강남', sport_code: 'football', role: 'owner' },
  ]
  let sent: { url: string; method: string }[]

  /** 나가기(`members/...`)만 409 로 막고, 해체(`teams/t1`)는 통과시킨다. */
  function stubLastOwner(disband?: { status: number; code: string; message: string }) {
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        const method = init?.method ?? 'GET'
        sent.push({ url, method })
        if (method === 'DELETE' && url.includes('/members/')) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                error: { code: 'LAST_OWNER', message: '마지막 주장은 팀을 나갈 수 없습니다.' },
              }),
              { status: 409 },
            ),
          )
        }
        if (method === 'DELETE' && disband) {
          return Promise.resolve(
            new Response(
              JSON.stringify({ error: { code: disband.code, message: disband.message } }),
              { status: disband.status },
            ),
          )
        }
        if (method === 'DELETE') return Promise.resolve(new Response(null, { status: 204 }))
        return Promise.resolve(new Response(JSON.stringify({ id: 't9' }), { status: 201 }))
      },
    )
  }

  beforeEach(() => {
    sent = []
    refreshed.mockClear()
    stubLastOwner()
  })
  afterEach(() => vi.restoreAllMocks())

  it('나가기가 막히면 해체할 길을 낸다', async () => {
    const user = userEvent.setup()
    render(<TeamActions teams={OWNER} userId="u1" />)
    await user.click(screen.getByRole('button', { name: '팀 나가기' }))

    expect(await screen.findByRole('button', { name: '팀 해체하기' })).toBeInTheDocument()
  })

  /* 🔴 **되돌릴 수 없다는 것을 먼저 적는다** — 팀 이름·지난 경기는 남지만
     구성원은 전부 나가고 다시 모아야 한다. */
  it('해체가 무엇인지 적어 준다', async () => {
    const user = userEvent.setup()
    render(<TeamActions teams={OWNER} userId="u1" />)
    await user.click(screen.getByRole('button', { name: '팀 나가기' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/되돌릴 수 없습니다/)
  })

  it('해체하면 그 팀으로 DELETE 가 나간다', async () => {
    const user = userEvent.setup()
    render(<TeamActions teams={OWNER} userId="u1" />)
    await user.click(screen.getByRole('button', { name: '팀 나가기' }))
    await user.click(await screen.findByRole('button', { name: '팀 해체하기' }))

    await waitFor(() => expect(refreshed).toHaveBeenCalled())
    expect(sent.some((s) => s.url === '/api/teams/t1' && s.method === 'DELETE')).toBe(true)
  })

  /**
   * 🔴 **앞으로 있을 경기가 있으면 서버가 막는다**(`409
   * TEAM_HAS_UPCOMING_MATCH`) — 상대에게는 약속이라 먼저 정리해야 한다.
   * 화면이 미리 가리지 않고 서버가 준 문구를 그대로 보여 준다.
   */
  it('잡힌 경기가 있어 해체가 막히면 그 이유를 보여 준다', async () => {
    stubLastOwner({
      status: 409,
      code: 'TEAM_HAS_UPCOMING_MATCH',
      message: '앞으로 있을 경기가 있어 해체할 수 없습니다.',
    })
    const user = userEvent.setup()
    render(<TeamActions teams={OWNER} userId="u1" />)
    await user.click(screen.getByRole('button', { name: '팀 나가기' }))
    await user.click(await screen.findByRole('button', { name: '팀 해체하기' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      '앞으로 있을 경기가 있어 해체할 수 없습니다.',
    )
    expect(refreshed).not.toHaveBeenCalled()
  })

  /* 🔴 **다른 이유로 막힌 것에는 해체를 권하지 않는다** — 나갈 수 있는
     사람에게 팀을 없애라고 하면 안 된다. */
  it('LAST_OWNER 가 아니면 해체를 안 권한다', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({ error: { code: 'FORBIDDEN', message: '권한이 없습니다.' } }),
          { status: 403 },
        ),
      ),
    )
    const user = userEvent.setup()
    render(<TeamActions teams={OWNER} userId="u1" />)
    await user.click(screen.getByRole('button', { name: '팀 나가기' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('권한이 없습니다.')
    expect(screen.queryByRole('button', { name: '팀 해체하기' })).toBeNull()
  })
})

/**
 * **떠난 팀은 그 자리에서 사라진다** (사용자 지적, 2026-09-18).
 *
 * 「팀 해체 했는데, 팀 왜 안사라지고 그 팀의 구성원이 아닙니다.로 나옴?
 * 아예 안나와야지」
 *
 * 🔴 **`router.refresh()` 하나로는 모자랐다.** 개발 모드에서 Next 는 라우트
 * 핸들러와 서버 컴포넌트를 **다른 모듈 그래프**로 묶어서, mock 을 고친 쪽과
 * 목록을 그리는 쪽이 갈린다(1.11 회차가 스위치·호칭에서 겪고 적어 둔 그
 * 함정이다). 해체는 됐는데 목록은 그대로였고, 거기서 나가기를 다시 누르니
 * **「그 팀의 구성원이 아닙니다」**(이미 나간 뒤라 404)가 떴다.
 *
 * 🔴 고치는 법은 1.11 의 결론과 같다 — **화면이 결과를 직접 반영한다.**
 * mock 우회가 아니라 어느 모드에서든 맞는 방식이고, 실서버에서도 다시 받아
 * 오기를 기다리지 않고 그 자리에서 사라진다.
 */
describe('프로필 — 떠난 팀은 목록에서 빠진다', () => {
  const TWO = [
    { team_id: 't1', name: '번개FC', region: '서울 강남', sport_code: 'football', role: 'owner' },
    { team_id: 't2', name: '한강FC', region: '서울 마포구', sport_code: 'football', role: 'member' },
  ]

  function stubOk() {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      /* 🔴 **주장인 t1 만** 막는다. 전부 막으면 팀원으로 나가는 갈래까지
         409 가 되어, 시험이 잡으려던 것과 다른 것을 재게 된다. */
      if ((init?.method ?? 'GET') === 'DELETE' && String(input).includes('/teams/t1/members/')) {
        return Promise.resolve(
          new Response(
            JSON.stringify({ error: { code: 'LAST_OWNER', message: '마지막 주장은 팀을 나갈 수 없습니다.' } }),
            { status: 409 },
          ),
        )
      }
      if ((init?.method ?? 'GET') === 'DELETE') {
        return Promise.resolve(new Response(null, { status: 204 }))
      }
      return Promise.resolve(new Response(JSON.stringify({ id: 't9' }), { status: 201 }))
    })
  }

  beforeEach(() => {
    refresh.mockClear()
    stubOk()
  })
  afterEach(() => vi.restoreAllMocks())

  it('해체한 팀이 그 자리에서 사라진다', async () => {
    const user = userEvent.setup()
    render(<TeamActions teams={TWO} userId="u1" />)
    await user.click(screen.getAllByRole('button', { name: '팀 나가기' })[0])
    await user.click(await screen.findByRole('button', { name: '팀 해체하기' }))

    await waitFor(() => expect(screen.queryByText('번개FC')).toBeNull())
    // 🔴 **남은 팀은 그대로다** — 하나 없앴다고 목록을 비우면 안 된다.
    expect(screen.getByText('한강FC')).toBeInTheDocument()
  })

  /* 사라진 팀 자리에 「해체하시겠습니까」가 남아 있으면 안 된다. */
  it('해체한 뒤에는 권유도 사라진다', async () => {
    const user = userEvent.setup()
    render(<TeamActions teams={TWO} userId="u1" />)
    await user.click(screen.getAllByRole('button', { name: '팀 나가기' })[0])
    await user.click(await screen.findByRole('button', { name: '팀 해체하기' }))

    await waitFor(() => expect(screen.queryByText('번개FC')).toBeNull())
    expect(screen.queryByRole('button', { name: '팀 해체하기' })).toBeNull()
  })

  /* 나가기도 같다 — 성공했으면 그 줄이 남아 있을 이유가 없다. */
  it('나간 팀도 그 자리에서 사라진다', async () => {
    const user = userEvent.setup()
    render(<TeamActions teams={TWO} userId="u1" />)
    await user.click(screen.getAllByRole('button', { name: '팀 나가기' })[1])

    await waitFor(() => expect(screen.queryByText('한강FC')).toBeNull())
    expect(screen.getByText('번개FC')).toBeInTheDocument()
  })

  /* 🔴 마지막 팀이 사라지면 **「아직 소속된 팀이 없습니다」**로 돌아간다. */
  it('마지막 팀까지 떠나면 빈 안내로 돌아간다', async () => {
    const user = userEvent.setup()
    render(<TeamActions teams={[TWO[1]]} userId="u1" />)
    await user.click(screen.getByRole('button', { name: '팀 나가기' }))

    expect(await screen.findByText('아직 소속된 팀이 없습니다.')).toBeInTheDocument()
  })
})
