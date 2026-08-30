import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { PlayerCard } from '@/server/backend'
import { HomeBody } from './page'

// LogoutButton 이 useRouter 를 쓴다.
vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}))

// '내 프로필'은 이 줄에 없다 — 우상단 닉네임이 그 자리다.
const CARD: PlayerCard = {
  id: 'c1',
  public_slug: 'hong-gildong-4f2a',
  og_image_key: 'cards/7b4d.png',
  user: { id: 'u1', nickname: '홍길동' },
  titles: [],
}

const TITLES = ['영상 분석', '용병 매칭', '내 팀', '레슨 · 상점', '경기장 예약']

describe('홈 화면 — /', () => {
  it('워드마크와 목적지 글자를 적는다', () => {
    render(<HomeBody user={null} />)
    // 워드마크는 헤더 · 헤더의 작은 카드 · 스쿼드 판의 빈 카드에 각각 있다.
    expect(screen.getAllByText('SUPERSUB').length).toBeGreaterThan(0)
    for (const t of TITLES) {
      expect(screen.getByRole('button', { name: t })).toBeInTheDocument()
    }
  })

  // 카드는 상시 노출이 아니다 — 배경 사진을 가리지 않게 가리켰을 때만 나온다.
  it('가리키기 전에는 카드가 하나도 없다', () => {
    render(<HomeBody user={null} />)
    expect(screen.queryByText(/경기 영상을 올리면/)).toBeNull()
    expect(screen.queryByText('준비 중입니다')).toBeNull()
  })

  it('글자를 가리키면 그 카드가 나오고 원래 페이지로 가는 링크가 된다', async () => {
    const user = userEvent.setup()
    render(<HomeBody user={{ nickname: '홍길동' }} />)
    await user.hover(screen.getByRole('button', { name: '영상 분석' }))
    expect(screen.getByText(/경기 영상을 올리면/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /경기 영상을 올리면/ })).toHaveAttribute(
      'href',
      '/analysis',
    )
  })

  // '내 선수 카드'는 '내 프로필'에, '내 프로필'은 닉네임 자리에 합쳤다.
  it('목적지 글자에 내 선수 카드도 내 프로필도 없다', () => {
    render(<HomeBody user={{ nickname: '홍길동' }} />)
    expect(screen.queryByRole('button', { name: '내 선수 카드' })).toBeNull()
    expect(screen.queryByRole('button', { name: '내 프로필' })).toBeNull()
  })

  // 카드가 아직 없는 사람에게는 닉네임 글자가 그 자리를 대신한다.
  it('카드가 없으면 닉네임이 그 자리를 대신한다', () => {
    render(<HomeBody user={{ nickname: '홍길동' }} />)
    expect(screen.getByRole('link', { name: /홍길동/ })).toHaveAttribute('href', '/me')
  })

  it('카드가 있으면 그 카드를 눌러 프로필로 간다', () => {
    render(<HomeBody user={{ nickname: '홍길동' }} card={CARD} />)
    const link = screen.getByRole('link', { name: /내 프로필/ })
    expect(link).toHaveAttribute('href', '/me')
    // 헤더에 들어간 것이 선수 카드 그 자체여야 한다 — 따로 만든 축소판이 아니다.
    expect(link.querySelector('.ss-pcard')).not.toBeNull()
    // 같은 카드가 스쿼드 판 가운데에도 있으므로 헤더 것만 집는다.
    expect(link.querySelector('.ss-pcard-alias')?.textContent).toBe('THREE LUNGS')
  })

  // 카드만 있으면 눌러 보기 전엔 어디로 가는지 알 수 없다.
  it('카드 아래에 내 프로필이라고 적는다', () => {
    render(<HomeBody user={{ nickname: '홍길동' }} card={CARD} />)
    expect(screen.getByText('내 프로필')).toBeInTheDocument()
  })

  it('아직 갈 곳이 없는 목적지는 카드에 준비 중이라고 적는다', async () => {
    const user = userEvent.setup()
    render(<HomeBody user={{ nickname: '홍길동' }} />)
    await user.hover(screen.getByRole('button', { name: '경기장 예약' }))
    expect(screen.getByText('준비 중입니다')).toBeInTheDocument()
  })

  it('로그인 안 했으면 로그인 전용 목적지 카드에 안내를 붙이되 링크는 살아 있다', async () => {
    const user = userEvent.setup()
    render(<HomeBody user={null} />)
    await user.hover(screen.getByRole('button', { name: '영상 분석' }))
    expect(screen.getByText('로그인이 필요합니다')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /경기 영상을 올리면/ })).toHaveAttribute(
      'href',
      '/analysis',
    )
  })

  // 스크롤되지 않는 화면이라 SCROLL DOWN 이 참말이 아니었고, 소셜은 실제
  // 계정이 없어 글자만 있었다 — 둘 다 지웠다.
  it('SCROLL DOWN 과 소셜 글자를 두지 않는다', () => {
    render(<HomeBody user={null} />)
    expect(screen.queryByText(/SCROLL DOWN/)).toBeNull()
    expect(screen.queryByText('INSTAGRAM')).toBeNull()
  })

  it('로그인 안 했으면 인사말 자리에 로그인 · 회원가입 버튼을 보여준다', () => {
    render(<HomeBody user={null} />)
    expect(screen.getByRole('link', { name: '로그인' })).toHaveAttribute('href', '/login')
    expect(screen.getByRole('link', { name: '회원가입' })).toHaveAttribute('href', '/signup')
  })

  it('로그인했으면 로그인 · 회원가입 대신 프로필과 로그아웃을 보여준다', () => {
    render(<HomeBody user={{ nickname: '홍길동' }} />)
    expect(screen.getByText('내 프로필')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '로그아웃' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: '로그인' })).toBeNull()
    expect(screen.queryByRole('link', { name: '회원가입' })).toBeNull()
  })

  it('로그인 안 했으면 로그아웃 자리가 아예 없다', () => {
    render(<HomeBody user={null} />)
    expect(screen.queryByRole('button', { name: '로그아웃' })).toBeNull()
  })

  // 하단 내비바는 없앴다 — 목적지가 상단 글자 줄에 이미 다 있다.
  it('하단 내비바가 없다', () => {
    render(<HomeBody user={{ nickname: '홍길동' }} />)
    expect(screen.queryByRole('link', { name: '홈' })).toBeNull()
  })
})
