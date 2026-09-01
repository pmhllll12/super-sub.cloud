import { render, screen } from '@testing-library/react'
import DestinationCard from './DestinationCard'

describe('목적지 카드', () => {
  it('갈 수 있는 곳은 링크다', () => {
    render(<DestinationCard title="영상 분석" icon="videocam" href="/analysis" />)
    expect(screen.getByRole('link', { name: /영상 분석/ })).toHaveAttribute('href', '/analysis')
  })

  // 🔴 '준비 중입니다' 는 안 적는다(사용자 요청) — 개발 진행 상태는 화면이
  // 할 말이 아니고, 갈 곳이 없으면 **링크가 아닌 것**으로 이미 드러난다.
  it('갈 곳이 없으면 링크가 아니다 — 준비 중이라고 적지도 않는다', () => {
    render(<DestinationCard title="용병 매칭" icon="sports_soccer" />)
    expect(screen.queryByRole('link')).toBeNull()
    expect(screen.queryByText(/준비 중/)).toBeNull()
  })

  it('두 줄 설명을 보여준다', () => {
    render(
      <DestinationCard
        title="영상 분석"
        icon="videocam"
        href="/analysis"
        summary={'경기 영상을 올리면\n실력 리포트가 나옵니다'}
      />,
    )
    const link = screen.getByRole('link', { name: /영상 분석/ })
    expect(link.textContent).toContain('경기 영상을 올리면')
    expect(link.textContent).toContain('실력 리포트가 나옵니다')
  })

  it('로그인이 필요한 곳은 링크는 그대로 두고 로그인 필요 안내만 보여준다', () => {
    render(<DestinationCard title="내 프로필" icon="person" href="/me" locked />)
    const link = screen.getByRole('link', { name: /내 프로필/ })
    expect(link).toHaveAttribute('href', '/me')
    expect(screen.getByText('로그인이 필요합니다')).toBeInTheDocument()
  })

  it('로그인이 필요 없거나 이미 로그인한 카드는 안내문을 보여주지 않는다', () => {
    render(<DestinationCard title="내 프로필" icon="person" href="/me" locked={false} />)
    expect(screen.queryByText('로그인이 필요합니다')).toBeNull()
    expect(screen.queryByText('준비 중입니다')).toBeNull()
  })
})
