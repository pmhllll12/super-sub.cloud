import { render, screen } from '@testing-library/react'
import FloatingNavBar from './FloatingNavBar'

vi.mock('next/navigation', () => ({ usePathname: () => '/' }))

describe('하단 내비바', () => {
  it('로고가 홈으로 간다', () => {
    render(<FloatingNavBar />)
    expect(screen.getByRole('link', { name: '홈' })).toHaveAttribute('href', '/')
  })

  it('앱과 같은 목적지를 그린다', () => {
    render(<FloatingNavBar />)
    expect(screen.getByRole('link', { name: '영상 분석' })).toHaveAttribute('href', '/analysis')
    expect(screen.getByRole('link', { name: '내 선수 카드' })).toHaveAttribute('href', '/me/card')
    expect(screen.getByRole('link', { name: '내 프로필' })).toHaveAttribute('href', '/me')
  })

  it('용병 매칭은 아직 링크가 아니다', () => {
    render(<FloatingNavBar />)
    expect(screen.queryByRole('link', { name: /용병 매칭/ })).toBeNull()
  })

  it('현재 위치만 표시하고 나머지에는 붙지 않는다', () => {
    render(<FloatingNavBar />)
    expect(screen.getByRole('link', { name: '홈' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: '영상 분석' })).not.toHaveAttribute('aria-current')
    expect(screen.getByRole('link', { name: '내 선수 카드' })).not.toHaveAttribute('aria-current')
    expect(screen.getByRole('link', { name: '내 프로필' })).not.toHaveAttribute('aria-current')
  })
})
