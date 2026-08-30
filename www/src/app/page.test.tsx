import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HomeBody } from './page'

// LogoutButton 이 useRouter 를 쓴다.
vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}))

// '내 프로필'은 이 줄에 없다 — 우상단 닉네임이 그 자리다.
const TITLES = ['영상 분석', '용병 매칭', '내 팀', '레슨 · 상점', '경기장 예약']

describe('홈 화면 — /', () => {
  it('워드마크와 목적지 글자를 적는다', () => {
    render(<HomeBody user={null} />)
    expect(screen.getByText('SUPERSUB')).toBeInTheDocument()
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

  it('닉네임이 곧 내 프로필 링크다', () => {
    render(<HomeBody user={{ nickname: '홍길동' }} />)
    expect(screen.getByRole('link', { name: '홍길동' })).toHaveAttribute('href', '/me')
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

  it('우하단 번호 목록이 목적지 글자와 같은 것을 같은 수만큼 센다', () => {
    const { container } = render(<HomeBody user={null} />)
    const list = container.querySelector('.ss-home-index') as HTMLElement
    expect(within(list).getByText('01')).toBeInTheDocument()
    expect(within(list).getAllByRole('listitem')).toHaveLength(TITLES.length)
    for (const t of TITLES) {
      expect(within(list).getByText(t)).toBeInTheDocument()
    }
  })

  it('레퍼런스처럼 헤드라인과 하단 글자를 적는다', () => {
    render(<HomeBody user={null} />)
    expect(screen.getByRole('heading', { name: /OWN THE[\s\S]*PITCH/ })).toBeInTheDocument()
    expect(screen.getByText(/SCROLL DOWN/)).toBeInTheDocument()
    expect(screen.getByText('INSTAGRAM')).toBeInTheDocument()
    expect(screen.getByText('시작하기')).toBeInTheDocument()
  })

  it('로그인 안 했으면 인사말 자리에 로그인 · 회원가입 버튼을 보여준다', () => {
    render(<HomeBody user={null} />)
    expect(screen.getByRole('link', { name: '로그인' })).toHaveAttribute('href', '/login')
    expect(screen.getByRole('link', { name: '회원가입' })).toHaveAttribute('href', '/signup')
  })

  it('로그인했으면 인사말 자리에 닉네임과 로그아웃을 보여준다', () => {
    render(<HomeBody user={{ nickname: '홍길동' }} />)
    expect(screen.getByText('홍길동')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '로그아웃' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: '로그인' })).toBeNull()
    expect(screen.queryByRole('link', { name: '회원가입' })).toBeNull()
  })

  // 하단 내비바는 없앴다 — 목적지가 상단 글자 줄에 이미 다 있다.
  it('하단 내비바가 없다', () => {
    render(<HomeBody user={{ nickname: '홍길동' }} />)
    expect(screen.queryByRole('link', { name: '홈' })).toBeNull()
  })
})
