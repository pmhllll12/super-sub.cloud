import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LogoutButton from './LogoutButton'

const refresh = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh }),
}))

describe('로그아웃', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    refresh.mockClear()
  })

  it('성공하면 서버 컴포넌트를 다시 그리게 한다(이동하지 않는다)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
    )
    render(<LogoutButton />)
    await userEvent.click(screen.getByRole('button', { name: '로그아웃' }))
    expect(refresh).toHaveBeenCalledTimes(1)
  })

  it('실패하면 서버 message 를 보여주고 다시 그리지 않는다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({ error: { code: 'NETWORK_ERROR', message: '서버에 연결하지 못했습니다.' } }),
            { status: 500 },
          ),
      ),
    )
    render(<LogoutButton />)
    await userEvent.click(screen.getByRole('button', { name: '로그아웃' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('서버에 연결하지 못했습니다')
    expect(refresh).not.toHaveBeenCalled()
  })
})
