import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TitlesForm from './TitlesForm'

const refresh = vi.fn()
vi.mock('next/navigation', () => ({ useRouter: () => ({ refresh }) }))

/**
 * **호칭 — 사람이 직접 적는다** (2026-09-16 결정, 미결 `paik` 36번).
 *
 * 🔴 방향이 뒤집힌 자리다. 원래는 분석이 붙이는 값이라 화면이 읽기만 했다.
 * 근거: *"참이든 거짓이든 경기 후 리뷰로 남겨지니까 상관없다"*.
 */
describe('프로필 — 호칭 정하기', () => {
  let sent: { url: string; body: string | null }[]

  beforeEach(() => {
    sent = []
    refresh.mockClear()
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        sent.push({
          url: String(input),
          body: typeof init?.body === 'string' ? init.body : null,
        })
        return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }))
      },
    )
  })

  afterEach(() => vi.restoreAllMocks())

  /* 🔴 **「없음」을 부정적으로 적지 않는다**(계약 4장) — 빈 것은 정상이다. */
  it('없으면 그렇게 적고, 정하는 자리를 낸다', () => {
    render(<TitlesForm titles={[]} />)
    expect(screen.getByText('아직 정한 호칭이 없습니다.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '호칭 정하기' })).toBeInTheDocument()
  })

  it('있으면 알약으로 보이고 고칠 수 있다', () => {
    render(<TitlesForm titles={['시야가 넓은']} />)
    expect(screen.getByText('시야가 넓은')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '호칭 고치기' })).toBeInTheDocument()
  })

  it('적어서 저장하면 카드 경로로 보낸다', async () => {
    const user = userEvent.setup()
    render(<TitlesForm titles={[]} />)
    await user.click(screen.getByRole('button', { name: '호칭 정하기' }))
    await user.type(screen.getByLabelText('호칭 1'), '시야가 넓은')
    await user.click(screen.getByRole('button', { name: '저장' }))

    await waitFor(() => expect(refresh).toHaveBeenCalled())
    expect(sent[0].url).toBe('/api/me/card')
    expect(JSON.parse(sent[0].body!)).toEqual({ titles: ['시야가 넓은'] })
  })

  /* 🔴 **빈 칸은 안 보낸다** — 비우는 것이 지우는 뜻이고, 빈 문자열을 그대로
     보내면 서버에 빈 호칭이 남는다. */
  it('빈 칸은 빼고 보낸다', async () => {
    const user = userEvent.setup()
    render(<TitlesForm titles={['하나']} />)
    await user.click(screen.getByRole('button', { name: '호칭 고치기' }))
    await user.click(screen.getByRole('button', { name: '저장' }))

    await waitFor(() => expect(sent.length).toBe(1))
    expect(JSON.parse(sent[0].body!)).toEqual({ titles: ['하나'] })
  })

  /* 🔴 **분류(강점·활동)를 안 묻는다**(사용자 결정) — 사람이 적은 글에 분류를
     매길 사람이 없다. */
  it('분류를 묻지 않는다', async () => {
    const user = userEvent.setup()
    render(<TitlesForm titles={[]} />)
    await user.click(screen.getByRole('button', { name: '호칭 정하기' }))
    expect(screen.queryByText(/강점|활동/)).toBeNull()
  })

  /**
   * ⚠️ **저장 경로가 아직 계약에 없다**(36번) — 실서버가 그 칸을 열기 전까지는
   * 실패한다. 🔴 숨기지 않고 그대로 말한다: 조용히 넘어가면 그 사람은 저장된
   * 줄 알고 화면을 떠난다.
   */
  it('서버가 안 받으면 이유를 그대로 보여 준다', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({ error: { code: 'VALIDATION_ERROR', message: '호칭은 20자까지입니다.' } }),
          { status: 422 },
        ),
      ),
    )
    const user = userEvent.setup()
    render(<TitlesForm titles={[]} />)
    await user.click(screen.getByRole('button', { name: '호칭 정하기' }))
    await user.type(screen.getByLabelText('호칭 1'), '아주 긴 호칭')
    await user.click(screen.getByRole('button', { name: '저장' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('호칭은 20자까지입니다.')
  })
})

/**
 * 🔴 **서버가 답한 값으로 화면이 실제로 바뀐다.**
 *
 * 서버 컴포넌트가 준 prop 만 믿으면 개발 모드에서 저장해도 안 바뀐다 — Next 가
 * mock 을 두 벌 컴파일해서 고친 쪽과 그리는 쪽이 갈린다(`mock.ts` 머리말).
 * 사용자가 「고치고 저장하는데 안 바뀐다」고 한 것이 이것이다.
 */
describe('프로필 — 호칭이 저장 뒤 바로 바뀐다', () => {
  beforeEach(() => {
    refresh.mockClear()
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      (_input: RequestInfo | URL, init?: RequestInit) => {
        const body = typeof init?.body === 'string' ? JSON.parse(init.body) : {}
        // 계약대로 **고쳐진 카드를 그대로** 돌려준다.
        return Promise.resolve(
          new Response(
            JSON.stringify({
              titles: (body.titles ?? []).map((label: string, i: number) => ({
                code: `self-${i + 1}`,
                label,
              })),
            }),
            { status: 200 },
          ),
        )
      },
    )
  })

  afterEach(() => vi.restoreAllMocks())

  it('저장하면 알약이 새 호칭으로 바뀐다', async () => {
    const user = userEvent.setup()
    render(<TitlesForm titles={['옛 호칭']} />)
    expect(screen.getByText('옛 호칭')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '호칭 고치기' }))
    const first = screen.getByLabelText('호칭 1')
    await user.clear(first)
    await user.type(first, '새 호칭')
    await user.click(screen.getByRole('button', { name: '저장' }))

    expect(await screen.findByText('새 호칭')).toBeInTheDocument()
    expect(screen.queryByText('옛 호칭')).toBeNull()
  })

  it('다 비우면 「아직 정한 호칭이 없습니다」로 돌아간다', async () => {
    const user = userEvent.setup()
    render(<TitlesForm titles={['하나']} />)
    await user.click(screen.getByRole('button', { name: '호칭 고치기' }))
    await user.clear(screen.getByLabelText('호칭 1'))
    await user.click(screen.getByRole('button', { name: '저장' }))

    expect(await screen.findByText('아직 정한 호칭이 없습니다.')).toBeInTheDocument()
  })
})
