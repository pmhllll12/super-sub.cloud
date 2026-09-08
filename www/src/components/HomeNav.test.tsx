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
  /* 🔴 **갈 곳이 있으면 링크, 없으면 버튼**이다(2026-09-08). `<a>` 를 href
     없이 두면 Tab 으로 닿지도 않고 눌러도 아무 일이 없다 — 아직 안 열린
     목적지가 있어 그 경우를 갈라야 한다. */
  it('갈 곳이 있는 목적지는 아이콘과 글자를 감싼 링크다', () => {
    setup()
    expect(screen.getByRole('link', { name: '영상 분석' })).toHaveAttribute('href', '/analysis')
    expect(screen.getByRole('button', { name: '용병 매칭' })).toBeInTheDocument()
  })

  // 설명은 상시 노출이 아니다 — 배경 사진을 가리지 않게 가리켰을 때만 나온다.
  it('아무것도 가리키지 않으면 설명이 없다', () => {
    setup()
    expect(screen.queryByText(/경기 영상을 올리면/)).toBeNull()
  })

  it('글자에 마우스를 가져다 대면 그 카드가 나온다', async () => {
    const user = userEvent.setup()
    setup()
    await user.hover(screen.getByRole('link', { name: '영상 분석' }))
    expect(screen.getByText(/경기 영상을 올리면/)).toBeInTheDocument()
  })

  // 바로 없애지 않고 흐려지며 물러난다 — 사라질 때까지 기다린다.
  it('마우스를 치우면 카드가 사라진다', async () => {
    const user = userEvent.setup()
    setup()
    const item = screen.getByRole('link', { name: '영상 분석' })
    await user.hover(item)
    expect(screen.getByText(/경기 영상을 올리면/)).toBeInTheDocument()
    await user.unhover(item)
    await waitFor(() => expect(screen.queryByText(/경기 영상을 올리면/)).toBeNull())
  })

  /* ⚠️ **눌러서 고정하는 것은 없앴다**(2026-09-08). 누르는 것이 이동이 되면서
     고정할 자리가 없어졌고, 그것을 풀던 「바깥 클릭」·「Esc」 시험 둘도 함께
     걷어냈다 — 풀 것이 없는 자리를 지키는 시험이었다. */

  it('키보드로 글자에 닿아도 설명이 나온다', async () => {
    const user = userEvent.setup()
    setup()
    await user.tab()
    expect(screen.getByRole('link', { name: '영상 분석' })).toHaveFocus()
    expect(screen.getByText(/경기 영상을 올리면/)).toBeInTheDocument()
  })

  /* 🔴 **한 항목에 링크는 하나다.** 떠오른 설명까지 링크로 두면 같은 곳으로
     가는 링크가 둘이 되어 낭독기에서도 시험에서도 어느 쪽인지 모호해진다 —
     예전에 글자를 버튼으로 둔 이유가 그것이었고, 이제 반대쪽이 버튼이다. */
  it('떠오른 설명은 링크가 아니다 — 이동은 아이콘과 글자가 한다', async () => {
    const user = userEvent.setup()
    setup()
    await user.hover(screen.getByRole('link', { name: '영상 분석' }))
    expect(screen.getByText(/경기 영상을 올리면/)).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /경기 영상을 올리면/ })).toBeNull()
    expect(screen.getAllByRole('link', { name: '영상 분석' })).toHaveLength(1)
  })

  it('떠오른 설명에는 제목을 다시 적지 않는다', async () => {
    const user = userEvent.setup()
    setup()
    await user.hover(screen.getByRole('link', { name: '영상 분석' }))
    // '영상 분석' 이라고 적힌 것은 글자 줄의 링크 하나뿐이어야 한다.
    expect(screen.getAllByText('영상 분석')).toHaveLength(1)
  })

  it('준비 중인 곳은 설명이 나오되 링크가 아니다', async () => {
    const user = userEvent.setup()
    setup()
    await user.hover(screen.getByRole('button', { name: '용병 매칭' }))
    expect(screen.getByText(/경기를 찾고/)).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /경기를 찾고/ })).toBeNull()
    // '준비 중입니다' 는 안 적는다 — 링크가 아닌 것으로 이미 드러난다.
    expect(screen.queryByText('준비 중입니다')).toBeNull()
  })

  /* 🔴 **판이 없어져도 안내는 남는다.** 이건 개발 진행 상태가 아니라 사용자가
     할 일이라, 못 들어가는 곳을 눌러 보고 나서야 알게 하면 안 된다. */
  it('로그인 안 했으면 안내를 붙이되 링크는 살려 둔다', async () => {
    const user = userEvent.setup()
    setup({ loggedIn: false })
    const link = screen.getByRole('link', { name: '영상 분석' })
    await user.hover(link)
    expect(screen.getByText('로그인이 필요합니다')).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/analysis')
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
    expect(screen.getByRole('link', { name: '영상 분석' })).not.toHaveAttribute('data-active')
  })

  /* 🔴 **아이콘이 글자 위에 선다**(사용자 요청). 원래 떠오르는 유리 카드
     안에 있었고, 그 판을 없애면서 갈 데가 없어졌다. */
  it('아이콘이 링크 안, 글자 앞에 있다', () => {
    const { container } = setup()
    const link = screen.getByRole('link', { name: '영상 분석' })
    const icon = link.querySelector('.ss-home-nav-icon')
    expect(icon).not.toBeNull()
    expect(icon).toHaveTextContent('videocam')
    // 글자보다 앞에 있어야 세로로 쌓았을 때 위에 온다.
    expect(icon?.nextElementSibling).toHaveTextContent('영상 분석')
    expect(container.querySelector('.ss-home-nav-item--stack')).toBe(link)
  })
})
