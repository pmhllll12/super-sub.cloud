import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LoginPage from './page'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}))

describe('로그인 화면', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('이메일과 비밀번호 입력칸이 있다', () => {
    render(<LoginPage />)
    expect(screen.getByLabelText('이메일')).toBeInTheDocument()
    expect(screen.getByLabelText('비밀번호')).toBeInTheDocument()
  })

  it('실패하면 서버가 준 message 를 보여준다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              error: { code: 'INVALID_CREDENTIALS', message: '이메일 또는 비밀번호가 올바르지 않습니다.' },
            }),
            { status: 401 },
          ),
      ),
    )
    render(<LoginPage />)
    await userEvent.type(screen.getByLabelText('이메일'), 'a@b.com')
    await userEvent.type(screen.getByLabelText('비밀번호'), 'supersub2026')
    await userEvent.click(screen.getByRole('button', { name: '로그인' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      '이메일 또는 비밀번호가 올바르지 않습니다.',
    )
  })

  /**
   * 🔴 **429 뒤에는 같은 요청이 다시 안 나간다** — 계약 1번(SEC-009),
   * 미결 `jin` 2번. 창이 지나기 전에 다시 보내면 계속 거부되고 서버 자원만
   * 쓴다. 기다릴 시간은 **서버가 준 `Retry-After`** 다.
   */
  describe('요청이 너무 잦을 때(429)', () => {
    function limited(retryAfter: string | null) {
      const fn = vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              error: { code: 'TOO_MANY_REQUESTS', message: '요청이 너무 잦습니다.' },
            }),
            {
              status: 429,
              ...(retryAfter === null ? {} : { headers: { 'Retry-After': retryAfter } }),
            },
          ),
      )
      vi.stubGlobal('fetch', fn)
      return fn
    }

    async function submit() {
      await userEvent.type(screen.getByLabelText('이메일'), 'a@b.com')
      await userEvent.type(screen.getByLabelText('비밀번호'), 'supersub2026')
      await userEvent.click(screen.getByRole('button', { name: '로그인' }))
    }

    it('서버가 준 남은 시간을 그대로 보여준다', async () => {
      limited('37')
      render(<LoginPage />)
      await submit()
      // 🔴 임의의 상수(무조건 60초)가 아니라 그 시점에 남은 시간이다.
      expect(await screen.findByRole('alert')).toHaveTextContent('37초')
    })

    it('잠긴 동안 다시 눌러도 요청이 안 나간다', async () => {
      const fn = limited('37')
      render(<LoginPage />)
      await submit()
      await screen.findByRole('alert')
      expect(fn).toHaveBeenCalledTimes(1)

      await userEvent.click(screen.getByRole('button', { name: '로그인' }))
      expect(fn).toHaveBeenCalledTimes(1)
      expect(screen.getByRole('button', { name: '로그인' })).toBeDisabled()
    })

    /* 🔴 헤더가 중간에서 사라지는 일이 실제로 있었다(그걸 고치는 것이 이
       항목이다). 그때 0 으로 읽어 곧바로 풀리면 제한을 못 지킨다. */
    it('서버가 시간을 안 줘도 곧바로 풀리지 않는다', async () => {
      const fn = limited(null)
      render(<LoginPage />)
      await submit()
      await screen.findByRole('alert')

      await userEvent.click(screen.getByRole('button', { name: '로그인' }))
      expect(fn).toHaveBeenCalledTimes(1)
    })
  })
})
