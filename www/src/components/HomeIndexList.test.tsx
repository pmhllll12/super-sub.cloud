import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import HomeIndexList from './HomeIndexList'
import type { Destination } from './HomeNav'

const DESTINATIONS: Destination[] = [
  { title: '영상 분석', icon: 'videocam', summary: 'a\nb', href: '/analysis' },
  { title: '용병 매칭', icon: 'sports_soccer', summary: 'c\nd' },
]

describe('홈 번호 목록 — 우하단', () => {
  it('01 부터 번호를 매겨 나열한다 — 레퍼런스처럼 제목 뒤에 번호가 온다', () => {
    render(<HomeIndexList destinations={DESTINATIONS} active={null} onActivate={() => {}} />)
    expect(screen.getByText('01')).toBeInTheDocument()
    expect(screen.getByText('02')).toBeInTheDocument()
    expect(screen.getByText('영상 분석')).toBeInTheDocument()
  })

  it('갈 수 있는 곳은 링크고 준비 중인 곳은 아니다', () => {
    render(<HomeIndexList destinations={DESTINATIONS} active={null} onActivate={() => {}} />)
    expect(screen.getByRole('link', { name: '영상 분석 01' })).toHaveAttribute('href', '/analysis')
    expect(screen.queryByRole('link', { name: /용병 매칭/ })).toBeNull()
  })

  it('가리킨 항목을 부모에게 알린다 — 상단 글자와 강조를 맞춘다', async () => {
    const user = userEvent.setup()
    const onActivate = vi.fn()
    render(<HomeIndexList destinations={DESTINATIONS} active={null} onActivate={onActivate} />)
    await user.hover(screen.getByText('영상 분석'))
    expect(onActivate).toHaveBeenCalledWith('영상 분석')
  })

  it('부모가 정한 현재 항목을 강조한다', () => {
    render(<HomeIndexList destinations={DESTINATIONS} active="용병 매칭" onActivate={() => {}} />)
    expect(screen.getByText('용병 매칭').closest('li')).toHaveAttribute('data-active', 'true')
    expect(screen.getByText('영상 분석').closest('li')).not.toHaveAttribute('data-active')
  })
})
