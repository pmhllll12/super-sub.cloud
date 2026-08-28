import { render, screen } from '@testing-library/react'
import DestinationCard from './DestinationCard'

describe('목적지 카드', () => {
  it('갈 수 있는 곳은 링크다', () => {
    render(<DestinationCard title="영상 분석" icon="videocam" href="/analysis" />)
    expect(screen.getByRole('link', { name: /영상 분석/ })).toHaveAttribute('href', '/analysis')
  })

  it('준비 중인 곳은 링크가 아니고 그렇게 표시한다', () => {
    render(<DestinationCard title="용병 매칭" icon="sports_soccer" />)
    expect(screen.queryByRole('link')).toBeNull()
    expect(screen.getByText(/준비 중/)).toBeInTheDocument()
  })
})
