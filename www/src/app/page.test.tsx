import { render, screen } from '@testing-library/react'
import Home from './page'

describe('랜딩 페이지', () => {
  it('워드마크를 보여준다', () => {
    render(<Home />)
    expect(screen.getByText('SUPERSUB')).toBeInTheDocument()
  })

  it('로그인으로 가는 링크가 있다', () => {
    render(<Home />)
    expect(screen.getByRole('link', { name: '로그인' })).toHaveAttribute('href', '/login')
  })
})
