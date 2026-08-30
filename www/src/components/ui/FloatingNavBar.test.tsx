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
    expect(screen.getByRole('link', { name: '내 프로필' })).toHaveAttribute('href', '/me')
  })

  it('용병 매칭은 아직 링크가 아니다', () => {
    render(<FloatingNavBar />)
    expect(screen.queryByRole('link', { name: /용병 매칭/ })).toBeNull()
  })

  // 카드를 프로필에 합쳤다 — 같은 데로 가는 칸을 둘 두지 않는다.
  it('내 선수 카드 칸이 따로 없다 — 프로필에 합쳤다', () => {
    render(<FloatingNavBar />)
    expect(screen.queryByRole('link', { name: '내 선수 카드' })).toBeNull()
    expect(
      screen.queryAllByRole('link').filter((a) => a.getAttribute('href') === '/me/card'),
    ).toHaveLength(0)
  })

  it('현재 위치만 표시하고 나머지에는 붙지 않는다', () => {
    render(<FloatingNavBar />)
    expect(screen.getByRole('link', { name: '홈' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: '영상 분석' })).not.toHaveAttribute('aria-current')
    expect(screen.getByRole('link', { name: '내 프로필' })).not.toHaveAttribute('aria-current')
  })
})
