import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import NicknameForm from './NicknameForm'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}))

describe('닉네임 수정', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('현재 닉네임이 입력칸에 들어 있다', () => {
    render(<NicknameForm nickname="홍길동" />)
    expect(screen.getByLabelText('닉네임')).toHaveValue('홍길동')
  })

  it('저장에 성공하면 알림을 보여준다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify({ nickname: '새이름' }), { status: 200 })),
    )
    render(<NicknameForm nickname="홍길동" />)
    await userEvent.clear(screen.getByLabelText('닉네임'))
    await userEvent.type(screen.getByLabelText('닉네임'), '새이름')
    await userEvent.click(screen.getByRole('button', { name: '저장' }))
    expect(await screen.findByRole('status')).toHaveTextContent('저장했습니다')
  })

  it('422 면 서버 message 를 보여준다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              error: { code: 'VALIDATION_ERROR', message: '요청 값이 올바르지 않습니다: nickname' },
            }),
            { status: 422 },
          ),
      ),
    )
    render(<NicknameForm nickname="홍길동" />)
    await userEvent.click(screen.getByRole('button', { name: '저장' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('nickname')
  })
})
