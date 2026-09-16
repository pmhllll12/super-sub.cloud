import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SearchablePref from './SearchablePref'

const refresh = vi.fn()
vi.mock('next/navigation', () => ({ useRouter: () => ({ refresh }) }))

/**
 * **지인 검색 노출 스위치** (계약 3-12절, CCC 37번).
 *
 * 🔴 이 화면이 없으면 기본값(`true`)에 갇힌다 — 검색에서 빠지고 싶은 사람이
 * 뺄 자리가 없다. 계약은 2026-09-15 에 왔는데 화면이 비어 있었다.
 */
describe('프로필 — 지인 검색 노출', () => {
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
        // `PATCH /me` 는 **고쳐진 사용자를 그대로** 돌려준다(계약) — 화면이
        // 그 값으로 맞추므로 시험도 그 모양을 세운다.
        const body = typeof init?.body === 'string' ? JSON.parse(init.body) : {}
        return Promise.resolve(
          new Response(
            JSON.stringify({ is_nickname_searchable: body.is_nickname_searchable }),
            { status: 200 },
          ),
        )
      },
    )
  })

  afterEach(() => vi.restoreAllMocks())

  it('켜져 있으면 스위치가 켜진 것으로 읽힌다', () => {
    render(<SearchablePref searchable />)
    expect(screen.getByRole('switch', { name: '지인 검색에 나를 보이기' })).toBeChecked()
  })

  /* 🔴 **켜짐/꺼짐의 뜻을 글로 적는다** — 스위치 모양만으로는 무엇이
     달라지는지 알 수 없다. */
  it('끄면 무엇이 달라지는지 글로 적는다', () => {
    render(<SearchablePref searchable={false} />)
    expect(screen.getByRole('switch')).not.toBeChecked()
    expect(screen.getByText(/아무도 나를 찾을 수 없습니다/)).toBeInTheDocument()
    // 이미 맺은 지인은 그대로라는 것도 말해 준다 — 안 적으면 끊길까 봐 못 끈다.
    expect(screen.getByText(/이미 맺은 지인은 그대로/)).toBeInTheDocument()
  })

  /* 🔴 **이 칸만 보낸다.** 닉네임을 같이 실으면 계약상 그것도 고치는 요청이
     된다 — 여기서 이름을 건드릴 이유가 없다. */
  it('누르면 그 칸만 반대로 보낸다', async () => {
    const user = userEvent.setup()
    render(<SearchablePref searchable />)
    await user.click(screen.getByRole('switch'))

    await waitFor(() => expect(sent.length).toBe(1))
    expect(sent[0].url).toBe('/api/me')
    expect(JSON.parse(sent[0].body!)).toEqual({ is_nickname_searchable: false })
  })

  /**
   * 🔴 **서버가 답한 값으로 스위치가 실제로 움직인다.**
   *
   * 서버 컴포넌트가 준 prop 만 믿으면 개발 모드에서 영영 안 움직인다 — Next 가
   * mock 을 두 벌 컴파일해서 고친 쪽과 그리는 쪽이 갈린다(`mock.ts` 머리말).
   * 사용자가 「버튼이 안 된다」고 한 것이 이것이다.
   */
  it('서버가 답하면 스위치가 실제로 꺼진다', async () => {
    const user = userEvent.setup()
    render(<SearchablePref searchable />)
    const sw = screen.getByRole('switch')
    expect(sw).toBeChecked()

    await user.click(sw)

    await waitFor(() => expect(sw).not.toBeChecked())
    // 글도 따라 바뀐다 — 스위치만 움직이면 무엇이 달라졌는지 안 읽힌다.
    expect(screen.getByText(/아무도 나를 찾을 수 없습니다/)).toBeInTheDocument()
  })

  /**
   * 🔴 **낙관적으로 바꾸지 않는다.** 화면만 먼저 끄면 저장이 실패했을 때 그
   * 사람은 꺼진 줄 알고 떠난다 — 검색에는 계속 뜨는데.
   */
  it('저장에 실패하면 스위치가 안 바뀌고 이유를 적는다', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({ error: { code: 'UNKNOWN_ERROR', message: '저장하지 못했습니다.' } }),
          { status: 500 },
        ),
      ),
    )
    const user = userEvent.setup()
    render(<SearchablePref searchable />)
    await user.click(screen.getByRole('switch'))

    expect(await screen.findByRole('alert')).toHaveTextContent('저장하지 못했습니다.')
    // 🔴 여전히 켜져 있다 — 서버가 안 받았으므로.
    expect(screen.getByRole('switch')).toBeChecked()
    expect(refresh).not.toHaveBeenCalled()
  })
})
