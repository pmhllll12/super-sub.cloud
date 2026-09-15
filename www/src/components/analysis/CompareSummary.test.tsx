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
    render(<CompareSummary playerName="에스테반 로벨리" request={request} failedReason={null} onSelect={() => {}} onClose={() => {}} />)
    expect(screen.getByText(/가장 큰 차이는 접촉의 차는 다리 뻗기입니다/)).toBeInTheDocument()
    expect(screen.getByText('차는 다리 뻗기 선수 171° · 나 149° — 차는 다리를 22° 덜 폈습니다')).toBeInTheDocument()
    expect(screen.getByText('차이 5° 미만은 비슷함으로 봅니다')).toBeInTheDocument()
    expect(screen.queryByText(/브라우저에서 잰 값/)).toBeNull()
    expect(fetchSpy).not.toHaveBeenCalled()
    vi.unstubAllGlobals()
  })

  /* 🔴 선수 비교는 **저장하지 않는다**(사용자 결정, 2026-09-15) — 오른쪽 위 닫기로
     걷고 내 리포트만 남긴다. 못 찾은 경우에도 닫을 수 있어야 한다. */
  it('오른쪽 위 닫기를 누르면 닫으라고 알린다', async () => {
    const onClose = vi.fn()
    const { rerender } = render(
      <CompareSummary playerName="에스테반 로벨리" request={request} failedReason={null} onSelect={() => {}} onClose={onClose} />,
    )
    await userEvent.click(screen.getByRole('button', { name: '비교 닫기' }))
    expect(onClose).toHaveBeenCalledTimes(1)

    rerender(
      <CompareSummary playerName="에스테반 로벨리" request={null} failedReason="못 찾음" onSelect={() => {}} onClose={onClose} />,
    )
    await userEvent.click(screen.getByRole('button', { name: '비교 닫기' }))
    expect(onClose).toHaveBeenCalledTimes(2)
  })

  it('순간 줄을 누르면 그 순간을 알린다', async () => {
    const onSelect = vi.fn()
    render(<CompareSummary playerName="에스테반 로벨리" request={request} failedReason={null} onSelect={onSelect} onClose={() => {}} />)
    await userEvent.click(screen.getByRole('button', { name: /^접촉(?! 후)/ }))
    expect(onSelect).toHaveBeenCalledWith('impact')
  })

  it('순간을 못 찾았으면 이유만 적는다', () => {
    render(
      <CompareSummary
        playerName="에스테반 로벨리"
        request={null}
        failedReason="동작 앞뒤가 잘린 영상으로 보입니다"
        onSelect={() => {}}
        onClose={() => {}}
      />,
    )
    expect(screen.getByText(/슈팅 순간을 찾지 못해 비교하지 않았습니다/)).toBeInTheDocument()
    // 누를 순간 줄은 없다 — 남는 단추는 닫기 하나다.
    expect(screen.getAllByRole('button').map((b) => b.getAttribute('aria-label'))).toEqual(['비교 닫기'])
  })
})
