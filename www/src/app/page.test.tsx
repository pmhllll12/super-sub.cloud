import { render, screen } from '@testing-library/react'
import Home from './page'

describe('랜딩 페이지', () => {
  it('서비스 이름을 보여준다', () => {
    render(<Home />)
    expect(screen.getByRole('heading', { name: /Super-Sub/i })).toBeInTheDocument()
  })

  it('로그인으로 가는 링크가 있다', () => {
    render(<Home />)
    expect(screen.getByRole('link', { name: '로그인' })).toHaveAttribute('href', '/login')
  })
})
