import { render, screen } from '@testing-library/react'
import { LandingBody } from './page'

describe('랜딩 페이지', () => {
  it('워드마크를 보여준다', () => {
    render(<LandingBody />)
    expect(screen.getByText('SUPERSUB')).toBeInTheDocument()
  })

  it('제목 요소를 가진다', () => {
    render(<LandingBody />)
    expect(screen.getByRole('heading', { name: /Super-Sub/i })).toBeInTheDocument()
  })

  it('로그인으로 가는 링크가 있다', () => {
    render(<LandingBody />)
    expect(screen.getByRole('link', { name: '로그인' })).toHaveAttribute('href', '/login')
  })
})
