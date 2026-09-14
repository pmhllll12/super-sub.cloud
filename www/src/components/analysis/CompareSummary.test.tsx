import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { SummaryRequest } from '@/lib/motion/summaryContract'
import CompareSummary from './CompareSummary'

const request: SummaryRequest = {
  player: '에스테반 로벨리',
  kickingLeg: { player: 'right', user: 'right' },
  mirrored: false,
  measuredBy: 'browser',
  moments: [
    { key: 'before', metrics: [] },
    {
      key: 'impact',
      metrics: [{ id: 'swing_knee_extension', label: '차는 다리 뻗기', player: 171, user: 149, unit: '°' }],
    },
    { key: 'after', metrics: [] },
  ],
}

describe('비교 요약 절', () => {
  it('총평과 순간별 줄을 바로 그린다 — 서버를 부르지 않는다', () => {
    const fetchSpy = vi.fn()
    vi.stubGlobal('fetch', fetchSpy)
    render(<CompareSummary playerName="에스테반 로벨리" request={request} failedReason={null} onSelect={() => {}} />)
    expect(screen.getByText(/가장 큰 차이는 임팩트의 차는 다리 뻗기입니다/)).toBeInTheDocument()
    expect(screen.getByText('차는 다리 뻗기 선수 171° · 나 149° — 차는 다리를 22° 덜 폈습니다')).toBeInTheDocument()
    expect(screen.getByText(/브라우저에서 잰 값/)).toBeInTheDocument()
    expect(fetchSpy).not.toHaveBeenCalled()
    vi.unstubAllGlobals()
  })

  it('순간 줄을 누르면 그 순간을 알린다', async () => {
    const onSelect = vi.fn()
    render(<CompareSummary playerName="에스테반 로벨리" request={request} failedReason={null} onSelect={onSelect} />)
    await userEvent.click(screen.getByRole('button', { name: /^임팩트/ }))
    expect(onSelect).toHaveBeenCalledWith('impact')
  })

  it('순간을 못 찾았으면 이유만 적는다', () => {
    render(
      <CompareSummary
        playerName="에스테반 로벨리"
        request={null}
        failedReason="동작 앞뒤가 잘린 영상으로 보입니다"
        onSelect={() => {}}
      />,
    )
    expect(screen.getByText(/슈팅 순간을 찾지 못해 비교하지 않았습니다/)).toBeInTheDocument()
    expect(screen.queryByRole('button')).toBeNull()
  })
})
