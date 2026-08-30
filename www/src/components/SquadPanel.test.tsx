import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SquadPanel from './SquadPanel'

describe('스쿼드 판', () => {
  it('풋살 5인 자리를 빈 칸으로 보여준다', () => {
    render(<SquadPanel />)
    expect(screen.getAllByRole('button', { name: '+ 선수 추가' })).toHaveLength(5)
    expect(screen.getByText('0 / 5')).toBeInTheDocument()
  })

  it('이름을 넣으면 그 자리에 앉고 채운 수가 늘어난다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel />)
    await user.click(screen.getAllByRole('button', { name: '+ 선수 추가' })[0])
    await user.type(screen.getByLabelText('GK 선수 이름'), '홍길동{Enter}')
    expect(screen.getByText('홍길동')).toBeInTheDocument()
    expect(screen.getByText('1 / 5')).toBeInTheDocument()
  })

  it('빈 이름은 넣지 않는다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel />)
    await user.click(screen.getAllByRole('button', { name: '+ 선수 추가' })[0])
    await user.type(screen.getByLabelText('GK 선수 이름'), '   {Enter}')
    expect(screen.getByText('0 / 5')).toBeInTheDocument()
  })

  it('Esc 를 누르면 넣지 않고 닫는다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel />)
    await user.click(screen.getAllByRole('button', { name: '+ 선수 추가' })[1])
    await user.type(screen.getByLabelText('DF 선수 이름'), '김철수{Escape}')
    expect(screen.queryByText('김철수')).toBeNull()
    expect(screen.getByText('0 / 5')).toBeInTheDocument()
  })

  it('넣은 선수를 뺄 수 있다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel />)
    await user.click(screen.getAllByRole('button', { name: '+ 선수 추가' })[0])
    await user.type(screen.getByLabelText('GK 선수 이름'), '홍길동{Enter}')
    await user.click(screen.getByRole('button', { name: '홍길동 빼기' }))
    expect(screen.queryByText('홍길동')).toBeNull()
    expect(screen.getByText('0 / 5')).toBeInTheDocument()
  })
})
