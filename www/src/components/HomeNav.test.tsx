import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import HomeNav from './HomeNav'
import type { Destination } from './HomeNav'

const DESTINATIONS: Destination[] = [
  {
    title: '영상 분석',
    icon: 'videocam',
    summary: '경기 영상을 올리면\n실력 리포트가 나옵니다',
    href: '/analysis',
    authRequired: true,
  },
  { title: '용병 매칭', icon: 'sports_soccer', summary: '경기를 찾고\n지원 현황을 봅니다' },
]

function setup(props: Partial<React.ComponentProps<typeof HomeNav>> = {}) {
  return render(
    <HomeNav destinations={DESTINATIONS} loggedIn active={null} onActivate={() => {}} {...props} />,
  )
}

describe('홈 글자 내비 — 상단', () => {
  it('목적지를 글자로 한 줄에 적는다', () => {
    setup()
    expect(screen.getByRole('button', { name: '영상 분석' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '용병 매칭' })).toBeInTheDocument()
  })

  // 글자는 카드를 부르는 자리고, 실제 이동은 카드가 한다.
  it('아무것도 가리키지 않으면 카드가 없다', () => {
    setup()
    expect(screen.queryByText(/경기 영상을 올리면/)).toBeNull()
  })

  it('글자에 마우스를 가져다 대면 그 카드가 나온다', async () => {
    const user = userEvent.setup()
    setup()
    await user.hover(screen.getByRole('button', { name: '영상 분석' }))
    expect(screen.getByText(/경기 영상을 올리면/)).toBeInTheDocument()
  })

  it('마우스를 치우면 카드가 사라진다', async () => {
    const user = userEvent.setup()
    setup()
    const item = screen.getByRole('button', { name: '영상 분석' })
    await user.hover(item)
    await user.unhover(item)
    expect(screen.queryByText(/경기 영상을 올리면/)).toBeNull()
  })

  // 터치 · 키보드에서는 hover 가 없다 — 눌러도 나와야 한다.
  it('글자를 누르면 카드가 나오고, 한 번 더 누르면 닫힌다', async () => {
    const user = userEvent.setup()
    setup()
    const item = screen.getByRole('button', { name: '영상 분석' })
    await user.click(item)
    await user.unhover(item)
    expect(screen.getByText(/경기 영상을 올리면/)).toBeInTheDocument()
    await user.click(item)
    await user.unhover(item)
    expect(screen.queryByText(/경기 영상을 올리면/)).toBeNull()
  })

  it('키보드로 글자에 닿아도 카드가 나온다', async () => {
    const user = userEvent.setup()
    setup()
    await user.tab()
    expect(screen.getByRole('button', { name: '영상 분석' })).toHaveFocus()
    expect(screen.getByText(/경기 영상을 올리면/)).toBeInTheDocument()
  })

  it('나온 카드를 누르면 그 페이지로 간다', async () => {
    const user = userEvent.setup()
    setup()
    await user.hover(screen.getByRole('button', { name: '영상 분석' }))
    expect(screen.getByRole('link', { name: /영상 분석/ })).toHaveAttribute('href', '/analysis')
  })

  it('준비 중인 곳은 카드가 나오되 링크가 아니다', async () => {
    const user = userEvent.setup()
    setup()
    await user.hover(screen.getByRole('button', { name: '용병 매칭' }))
    expect(screen.getByText('준비 중입니다')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /용병 매칭/ })).toBeNull()
  })

  it('로그인 안 했으면 로그인 전용 카드에 안내를 붙이되 링크는 살려 둔다', async () => {
    const user = userEvent.setup()
    setup({ loggedIn: false })
    await user.hover(screen.getByRole('button', { name: '영상 분석' }))
    expect(screen.getByText('로그인이 필요합니다')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /영상 분석/ })).toHaveAttribute('href', '/analysis')
  })

  // 우하단 번호 목록과 강조를 맞추기 위해 부모가 현재 항목을 안다.
  it('가리킨 항목을 부모에게 알린다', async () => {
    const user = userEvent.setup()
    const onActivate = vi.fn()
    setup({ onActivate })
    await user.hover(screen.getByRole('button', { name: '용병 매칭' }))
    expect(onActivate).toHaveBeenCalledWith('용병 매칭')
  })

  it('부모가 정한 현재 항목을 강조한다', () => {
    setup({ active: '용병 매칭' })
    expect(screen.getByRole('button', { name: '용병 매칭' })).toHaveAttribute('data-active', 'true')
    expect(screen.getByRole('button', { name: '영상 분석' })).not.toHaveAttribute('data-active')
  })
})
