import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { LEAVE_MS, PageTransitionProvider, TransitionLink, useLeaving } from './pageTransition'

const push = vi.fn()
const pathname = vi.fn(() => '/')
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push }),
  usePathname: () => pathname(),
}))

function Probe() {
  return <span data-testid="state">{useLeaving() ? 'out' : 'in'}</span>
}

function setup() {
  return render(
    <PageTransitionProvider>
      <Probe />
      <TransitionLink href="/analysis">영상 분석으로</TransitionLink>
    </PageTransitionProvider>,
  )
}

describe('화면 전환', () => {
  beforeEach(() => {
    push.mockClear()
    pathname.mockReturnValue('/')
  })

  // 🔴 이동이 먼저 일어나면 나가는 모습을 아무도 못 본다.
  it('누르면 바로 이동하지 않고 나가는 상태부터 켠다', async () => {
    const user = userEvent.setup()
    setup()
    await user.click(screen.getByRole('link', { name: '영상 분석으로' }))

    expect(screen.getByTestId('state')).toHaveTextContent('out')
    expect(push).not.toHaveBeenCalled()

    // 애니메이션이 끝나면 그때 옮겨 간다.
    await waitFor(() => expect(push).toHaveBeenCalledWith('/analysis'), {
      timeout: LEAVE_MS + 400,
    })
  })

  // 새 탭으로 여는 것은 브라우저가 하던 대로 둔다.
  it('⌘·Ctrl 을 누른 채 클릭하면 가로채지 않는다', async () => {
    const user = userEvent.setup()
    setup()
    await user.keyboard('{Meta>}')
    await user.click(screen.getByRole('link', { name: '영상 분석으로' }))
    await user.keyboard('{/Meta}')

    expect(screen.getByTestId('state')).toHaveTextContent('in')
    expect(push).not.toHaveBeenCalled()
  })

  // 🔴 provider 를 안 감싼 자리에서 링크가 조용히 죽으면 안 된다.
  it('provider 밖에서는 평범한 링크로 둔다', async () => {
    const user = userEvent.setup()
    render(<TransitionLink href="/analysis">영상 분석으로</TransitionLink>)
    // jsdom 은 실제로 이동하지 않으므로 **기본 동작을 막았는지**로 본다 —
    // preventDefault 가 걸려 있으면 브라우저에서 아무 데도 안 간다.
    let prevented: boolean | null = null
    document.addEventListener('click', (e) => {
      prevented = e.defaultPrevented
    })
    await user.click(screen.getByRole('link', { name: '영상 분석으로' }))

    expect(prevented).toBe(false)
    expect(push).not.toHaveBeenCalled()
  })

  // 🔴 회귀 방지 — 새 화면이 '나가는 중'인 채로 한 번 그려지면 깜빡인다.
  // (보였다가 → 사라졌다가 → 다시 밖에서 들어온다)
  it('경로가 바뀌면 그 렌더에서 곧바로 나가는 상태가 풀린다', async () => {
    const user = userEvent.setup()
    const view = setup()
    await user.click(screen.getByRole('link', { name: '영상 분석으로' }))
    expect(screen.getByTestId('state')).toHaveTextContent('out')

    // 라우터가 옮겨 간 뒤의 첫 렌더 — effect 가 돌기 전이어도 이미 풀려 있어야 한다.
    pathname.mockReturnValue('/analysis')
    view.rerender(
      <PageTransitionProvider>
        <Probe />
        <TransitionLink href="/analysis">영상 분석으로</TransitionLink>
      </PageTransitionProvider>,
    )
    expect(screen.getByTestId('state')).toHaveTextContent('in')
  })

  // 나가는 연출만 돌고 제자리인 이동은 아예 시작하지 않는다.
  it('지금 있는 곳으로 가는 링크는 가로채지 않는다', async () => {
    const user = userEvent.setup()
    pathname.mockReturnValue('/analysis')
    setup()
    await user.click(screen.getByRole('link', { name: '영상 분석으로' }))
    expect(screen.getByTestId('state')).toHaveTextContent('in')
    expect(push).not.toHaveBeenCalled()
  })
})
