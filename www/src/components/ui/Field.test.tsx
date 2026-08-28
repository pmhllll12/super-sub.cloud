import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Field from './Field'

describe('Field', () => {
  it('라벨로 입력칸을 찾을 수 있다 — 기존 테스트가 이 접점을 쓴다', () => {
    render(<Field label="이메일" value="" onChange={() => {}} />)
    expect(screen.getByLabelText('이메일')).toBeInTheDocument()
  })

  it('입력하면 onChange 에 값이 온다', async () => {
    const onChange = vi.fn()
    render(<Field label="닉네임" value="" onChange={onChange} />)
    await userEvent.type(screen.getByLabelText('닉네임'), 'a')
    expect(onChange).toHaveBeenCalledWith('a')
  })

  it('hint 를 주면 함께 그린다', () => {
    render(<Field label="비밀번호" value="" onChange={() => {}} hint="8자 이상" />)
    expect(screen.getByText('8자 이상')).toBeInTheDocument()
  })
})
