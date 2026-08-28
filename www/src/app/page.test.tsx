import { render, screen } from '@testing-library/react'
import { HomeBody } from './page'

// FloatingNavBar(usePathname) · LogoutButton(useRouter) 이 둘 다 필요로 한다.
vi.mock('next/navigation', () => ({
  usePathname: () => '/',
  useRouter: () => ({ refresh: vi.fn() }),
}))

describe('홈 화면 — /', () => {
  it('워드마크와 목적지 카드는 로그인 여부와 무관하게 보인다', () => {
    render(<HomeBody user={null} />)
    expect(screen.getByText('SUPERSUB')).toBeInTheDocument()
    expect(screen.getByText(/경기 영상을 올리면/)).toBeInTheDocument()
    expect(screen.getAllByText('준비 중입니다')).toHaveLength(3)
  })

  it('로그인 안 했으면 로그인 전용 카드(영상 분석 · 내 선수 카드 · 내 프로필)에 로그인 필요 안내를 보여주되 링크는 살아 있다', () => {
    render(<HomeBody user={null} />)
    expect(screen.getAllByText('로그인이 필요합니다')).toHaveLength(3)
    expect(screen.getByRole('link', { name: /영상 분석/ })).toHaveAttribute('href', '/analysis')
    expect(screen.getByRole('link', { name: /내 선수 카드/ })).toHaveAttribute('href', '/me/card')
    expect(screen.getByRole('link', { name: /내 프로필/ })).toHaveAttribute('href', '/me')
  })

  it('로그인했으면 로그인 전용 카드에 로그인 필요 안내를 보여주지 않는다', () => {
    render(<HomeBody user={{ nickname: '홍길동' }} />)
    expect(screen.queryByText('로그인이 필요합니다')).toBeNull()
    // 아직 준비 안 된 3장(용병 매칭 · 내 팀 · 레슨 · 코치)은 로그인 여부와 무관하다.
    expect(screen.getAllByText('준비 중입니다')).toHaveLength(3)
  })

  it('카드는 6장뿐이다 — 무한 루프 복제본이 없다', () => {
    render(<HomeBody user={null} />)
    expect(screen.getAllByText(/영상 분석/)).toHaveLength(1)
    expect(document.querySelectorAll('.ss-carousel-item')).toHaveLength(6)
  })

  it('로그인 안 했으면 인사말 자리에 로그인 · 회원가입 버튼을 보여준다', () => {
    render(<HomeBody user={null} />)
    expect(screen.getByRole('link', { name: '로그인' })).toHaveAttribute('href', '/login')
    expect(screen.getByRole('link', { name: '회원가입' })).toHaveAttribute('href', '/signup')
  })

  it('로그인 안 했으면 하단 내비바를 보여주지 않는다 — 갈 데가 대부분 막혀 있다', () => {
    render(<HomeBody user={null} />)
    expect(screen.queryByRole('link', { name: '홈' })).toBeNull()
  })

  it('로그인했으면 인사말 자리에 닉네임과 로그아웃을 보여준다', () => {
    render(<HomeBody user={{ nickname: '홍길동' }} />)
    expect(screen.getByText('홍길동')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '로그아웃' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: '로그인' })).toBeNull()
    expect(screen.queryByRole('link', { name: '회원가입' })).toBeNull()
  })

  it('로그인했으면 하단 내비바를 보여준다', () => {
    render(<HomeBody user={{ nickname: '홍길동' }} />)
    expect(screen.getByRole('link', { name: '홈' })).toHaveAttribute('href', '/')
  })
})
