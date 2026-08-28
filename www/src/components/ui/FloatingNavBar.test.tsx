import { render, screen } from '@testing-library/react'
import FloatingNavBar from './FloatingNavBar'

vi.mock('next/navigation', () => ({ usePathname: () => '/home' }))

describe('하단 내비바', () => {
  it('앱과 같은 목적지를 그린다', () => {
    render(<FloatingNavBar />)
    expect(screen.getByRole('link', { name: '홈' })).toHaveAttribute('href', '/home')
    expect(screen.getByRole('link', { name: '영상 분석' })).toHaveAttribute('href', '/analysis')
    expect(screen.getByRole('link', { name: '내 선수 카드' })).toHaveAttribute('href', '/me/card')
    expect(screen.getByRole('link', { name: '내 프로필' })).toHaveAttribute('href', '/me')
  })

  it('현재 위치를 표시한다', () => {
    render(<FloatingNavBar />)
    expect(screen.getByRole('link', { name: '홈' })).toHaveAttribute('aria-current', 'page')
  })
})
