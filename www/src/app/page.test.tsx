import { render, screen } from '@testing-library/react'
import { HomeBody } from './page'

// FloatingNavBar(usePathname) · LogoutButton(useRouter) 이 둘 다 필요로 한다.
vi.mock('next/navigation', () => ({
  usePathname: () => '/',
  useRouter: () => ({ refresh: vi.fn() }),
}))

// 캐러셀 무한 루프가 카드 6장을 3벌 이어붙인다(HomeParallax 의
// LOOP_COPIES) — 복제본 2벌은 aria-hidden="true" 로 스크린리더에서
// 숨긴 채로 화면엔 그대로 존재한다. getByText 는 aria-hidden 을 안 걸러
// 주므로(getByRole 과 다르게), 진짜 한 벌(스크린리더가 읽는 쪽)만 세려면
// 여기서 걸러야 한다.
function visibleTexts(text: string | RegExp) {
  return screen.queryAllByText(text).filter((el) => !el.closest('[aria-hidden="true"]'))
}

describe('홈 화면 — /', () => {
  it('워드마크와 목적지 카드는 로그인 여부와 무관하게 보인다', () => {
    render(<HomeBody user={null} />)
    expect(screen.getByText('SUPERSUB')).toBeInTheDocument()
    expect(visibleTexts(/경기 영상을 올리면/)).toHaveLength(1)
    expect(visibleTexts('준비 중입니다')).toHaveLength(3)
  })

  it('로그인 안 했으면 로그인 전용 카드(영상 분석 · 내 선수 카드 · 내 프로필)에 로그인 필요 안내를 보여주되 링크는 살아 있다', () => {
    render(<HomeBody user={null} />)
    expect(visibleTexts('로그인이 필요합니다')).toHaveLength(3)
    expect(screen.getByRole('link', { name: /영상 분석/ })).toHaveAttribute('href', '/analysis')
    expect(screen.getByRole('link', { name: /내 선수 카드/ })).toHaveAttribute('href', '/me/card')
    expect(screen.getByRole('link', { name: /내 프로필/ })).toHaveAttribute('href', '/me')
  })

  it('로그인했으면 로그인 전용 카드에 로그인 필요 안내를 보여주지 않는다', () => {
    render(<HomeBody user={{ nickname: '홍길동' }} />)
    expect(visibleTexts('로그인이 필요합니다')).toHaveLength(0)
    // 아직 준비 안 된 3장(용병 매칭 · 내 팀 · 레슨 · 코치)은 로그인 여부와 무관하다.
    expect(visibleTexts('준비 중입니다')).toHaveLength(3)
  })

  it('캐러셀 무한 루프의 복제본은 스크린리더 · 탭 순서에서 빠진다', () => {
    render(<HomeBody user={null} />)
    // 카드 6장 × 3벌 = 18, 그중 링크(href 있는 카드)는 3장 × 3벌 = 9.
    const allAnalysisLinks = screen.getAllByText(/영상 분석/)
    expect(allAnalysisLinks).toHaveLength(3)
    // getByRole 은 기본적으로 aria-hidden 인 요소를 걸러내므로 진짜 한 장만 남는다.
    expect(screen.getAllByRole('link', { name: /영상 분석/ })).toHaveLength(1)
    // 복제본 링크는 tabIndex={-1} 로 탭 순서에서도 빠진다.
    const hiddenLinks = allAnalysisLinks
      .map((el) => el.closest('a'))
      .filter((a): a is HTMLAnchorElement => a !== null && a.closest('[aria-hidden="true"]') !== null)
    expect(hiddenLinks.length).toBeGreaterThan(0)
    for (const a of hiddenLinks) {
      expect(a).toHaveAttribute('tabindex', '-1')
    }
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
