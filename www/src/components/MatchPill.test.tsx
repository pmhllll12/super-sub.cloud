import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { ConfirmedMatch } from '@/lib/useNotifyInbox'
import { takeMatchOpen } from '@/lib/seekingStore'
import MatchPill from './MatchPill'

const pathname = vi.fn(() => '/analysis')
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => pathname(),
}))

const MATCH: ConfirmedMatch = {
  matchId: 'm1',
  us: { id: 't-us', name: '우리 팀', squadSlug: 'us-slug' },
  them: { id: 't-them', name: '번개FC', region: '서울 강남구', squadSlug: 'them-slug' },
  playedAt: '2026-09-19T09:00:00',
  place: '강남 풋살장',
}

describe('머리칸의 「경기 잡힘」', () => {
  it('🔴 잡힌 경기가 없으면 아무것도 안 그린다', () => {
    const { container } = render(<MatchPill match={null} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('언제인지 짧게 적는다', () => {
    pathname.mockReturnValue('/analysis')
    render(<MatchPill match={MATCH} />)
    expect(screen.getByText(/9\/19 토 09:00/)).toBeInTheDocument()
  })

  /**
   * 🔴 **경기 화면을 그리는 것은 홈의 판뿐이다.** 그래서 다른 화면에서는 그
   * 자리에서 열 수 없고, 「열어 달라」를 적어 두고 홈으로 보낸다.
   */
  it('홈이 아니면 홈으로 보내면서 「열어 달라」를 적어 둔다', async () => {
    pathname.mockReturnValue('/analysis')
    window.sessionStorage.clear()
    const user = userEvent.setup()
    render(<MatchPill match={MATCH} />)

    const link = screen.getByRole('link')
    expect(link).toHaveAttribute('href', '/')
    await user.click(link)
    expect(takeMatchOpen()).toBe('m1')
  })

  it('홈에서는 그 자리에서 연다', async () => {
    pathname.mockReturnValue('/')
    const onReopen = vi.fn()
    const user = userEvent.setup()
    render(<MatchPill match={MATCH} onReopen={onReopen} />)

    await user.click(screen.getByRole('button'))
    expect(onReopen).toHaveBeenCalled()
  })

  /* 🔴 `takeMatchOpen` 은 **집으면서 지운다** — 안 지우면 그 뒤로 홈에 들어올
     때마다 경기 화면이 저절로 뜬다. 「누를 때만 뜬다」가 규칙이다. */
  it('「열어 달라」는 한 번만 집힌다', async () => {
    pathname.mockReturnValue('/analysis')
    window.sessionStorage.clear()
    const user = userEvent.setup()
    render(<MatchPill match={MATCH} />)
    await user.click(screen.getByRole('link'))

    expect(takeMatchOpen()).toBe('m1')
    expect(takeMatchOpen()).toBeNull()
  })
})
