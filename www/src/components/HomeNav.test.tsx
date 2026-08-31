import { render, screen, waitFor } from '@testing-library/react'
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

  // 바로 없애지 않고 흐려지며 물러난다 — 사라질 때까지 기다린다.
  it('마우스를 치우면 카드가 사라진다', async () => {
    const user = userEvent.setup()
    setup()
    const item = screen.getByRole('button', { name: '영상 분석' })
    await user.hover(item)
    expect(screen.getByText(/경기 영상을 올리면/)).toBeInTheDocument()
    await user.unhover(item)
    await waitFor(() => expect(screen.queryByText(/경기 영상을 올리면/)).toBeNull())
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
    await waitFor(() => expect(screen.queryByText(/경기 영상을 올리면/)).toBeNull())
  })

  // 🔴 회귀 방지 — 눌러서 고정한 카드가 화면에 계속 떠 있었다.
  it('눌러 띄운 카드는 다른 데를 누르면 사라진다', async () => {
    const user = userEvent.setup()
    render(
      <div>
        <HomeNav destinations={DESTINATIONS} loggedIn active={null} onActivate={() => {}} />
        <p>바깥</p>
      </div>,
    )
    const item = screen.getByRole('button', { name: '영상 분석' })
    await user.click(item)
    await user.unhover(item)
    expect(screen.getByText(/경기 영상을 올리면/)).toBeInTheDocument()
    await user.click(screen.getByText('바깥'))
    await waitFor(() => expect(screen.queryByText(/경기 영상을 올리면/)).toBeNull())
  })

  it('눌러 띄운 카드는 Esc 로도 사라진다', async () => {
    const user = userEvent.setup()
    setup()
    const item = screen.getByRole('button', { name: '영상 분석' })
    await user.click(item)
    await user.unhover(item)
    expect(screen.getByText(/경기 영상을 올리면/)).toBeInTheDocument()
    await user.keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByText(/경기 영상을 올리면/)).toBeNull())
  })

  it('키보드로 글자에 닿아도 카드가 나온다', async () => {
    const user = userEvent.setup()
    setup()
    await user.tab()
    expect(screen.getByRole('button', { name: '영상 분석' })).toHaveFocus()
    expect(screen.getByText(/경기 영상을 올리면/)).toBeInTheDocument()
  })

  // 작은 판은 제목을 안 그린다(글자 줄에 이미 있다) — 링크의 이름은 설명이다.
  it('나온 카드를 누르면 그 페이지로 간다', async () => {
    const user = userEvent.setup()
    setup()
    await user.hover(screen.getByRole('button', { name: '영상 분석' }))
    expect(screen.getByRole('link', { name: /경기 영상을 올리면/ })).toHaveAttribute(
      'href',
      '/analysis',
    )
  })

  it('작은 판에는 제목을 다시 적지 않는다', async () => {
    const user = userEvent.setup()
    setup()
    await user.hover(screen.getByRole('button', { name: '영상 분석' }))
    // '영상 분석' 이라고 적힌 것은 글자 줄의 버튼 하나뿐이어야 한다.
    expect(screen.getAllByText('영상 분석')).toHaveLength(1)
  })

  it('준비 중인 곳은 카드가 나오되 링크가 아니다', async () => {
    const user = userEvent.setup()
    setup()
    await user.hover(screen.getByRole('button', { name: '용병 매칭' }))
    expect(screen.getByText(/경기를 찾고/)).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /경기를 찾고/ })).toBeNull()
    // '준비 중입니다' 는 안 적는다 — 링크가 아닌 것으로 이미 드러난다.
    expect(screen.queryByText('준비 중입니다')).toBeNull()
  })

  it('로그인 안 했으면 로그인 전용 카드에 안내를 붙이되 링크는 살려 둔다', async () => {
    const user = userEvent.setup()
    setup({ loggedIn: false })
    await user.hover(screen.getByRole('button', { name: '영상 분석' }))
    expect(screen.getByText('로그인이 필요합니다')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /경기 영상을 올리면/ })).toHaveAttribute(
      'href',
      '/analysis',
    )
  })

  // 우하단 번호 목록과 강조를 맞추기 위해 부모가 현재 항목을 안다.
  it('가리킨 항목을 부모에게 알린다', async () => {
    const user = userEvent.setup()
    const onActivate = vi.fn()
    setup({ onActivate })
    await user.hover(screen.getByRole('button', { name: '용병 매칭' }))
    expect(onActivate).toHaveBeenCalledWith('용병 매칭')
  })

  function order(container: HTMLElement) {
    const items = [...container.querySelectorAll('.ss-home-nav-list > li')]
    expect(items).toHaveLength(DESTINATIONS.length)
    return items.map((li) => (li as HTMLElement).style.getPropertyValue('--ss-nav-i'))
  }

  // 두 변형의 순서가 서로 반대다 — 둘 다 사용자가 고른 것이라 하나로
  // 합칠 수 없다. 어긋나면 등장이 뒤집히므로 양쪽을 다 잡아 둔다.
  it('글자 줄은 맨 왼쪽부터 등장한다', () => {
    expect(order(setup().container)).toEqual(['0', '1'])
  })

  it('알약은 맨 오른쪽부터 등장한다', () => {
    expect(order(setup({ variant: 'pill' }).container)).toEqual(['1', '0'])
  })

  it('부모가 정한 현재 항목을 강조한다', () => {
    setup({ active: '용병 매칭' })
    expect(screen.getByRole('button', { name: '용병 매칭' })).toHaveAttribute('data-active', 'true')
    expect(screen.getByRole('button', { name: '영상 분석' })).not.toHaveAttribute('data-active')
  })
})
