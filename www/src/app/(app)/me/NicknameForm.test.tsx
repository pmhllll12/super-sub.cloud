import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import NicknameForm from './NicknameForm'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}))

/**
 * 프로필이 '보여주는' 화면이 되면서 입력칸은 **접혀 있다.** 그래서 모든
 * 시험이 편집을 먼저 연다 — 화면에 늘 폼이 떠 있던 때의 시험을 그대로
 * 두면 첫 줄에서 입력칸을 못 찾고 죽는다.
 */
async function openEditor() {
  await userEvent.click(screen.getByRole('button', { name: /닉네임 편집/ }))
}

describe('닉네임 수정', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('편집을 열면 현재 닉네임이 입력칸에 들어 있다', async () => {
    render(<NicknameForm nickname="홍길동" />)
    await openEditor()
    expect(screen.getByLabelText('닉네임')).toHaveValue('홍길동')
  })

  it('저장에 성공하면 알림을 보여준다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify({ nickname: '새이름' }), { status: 200 })),
    )
    render(<NicknameForm nickname="홍길동" />)
    await openEditor()
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
    await openEditor()
    await userEvent.click(screen.getByRole('button', { name: '저장' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('nickname')
  })
})
