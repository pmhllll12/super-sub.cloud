import { render } from '@testing-library/react'
import AppFigure from './AppFigure'

let pathname = '/'
vi.mock('next/navigation', () => ({ usePathname: () => pathname }))

/* 🔴 로그아웃처럼 **링크 이동이 아닌 길로** 배경 없는 화면(로그인)에 오면, 직전 배경을
   곧바로 걷는다 — 안 그러면 몇 백 ms 동안 로그인 창의 유리 너머로 비친다(사용자 지적). */
describe('배경 층', () => {
  it('홈에서 로그인으로 곧바로 오면(로그아웃) 홈 배경이 그 자리에서 사라진다', () => {
    pathname = '/'
    const { container, rerender } = render(<AppFigure />)
    expect(container.querySelectorAll('.ss-app-figure').length).toBeGreaterThan(0)
    pathname = '/login'
    rerender(<AppFigure />)
    expect(container.querySelectorAll('.ss-app-figure')).toHaveLength(0)
  })

  it('프로필에서 로그인으로 와도 같다', () => {
    pathname = '/me'
    const { container, rerender } = render(<AppFigure />)
    expect(container.querySelectorAll('.ss-app-figure').length).toBeGreaterThan(0)
    pathname = '/login'
    rerender(<AppFigure />)
    expect(container.querySelectorAll('.ss-app-figure')).toHaveLength(0)
  })
})
