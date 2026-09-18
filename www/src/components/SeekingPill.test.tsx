import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { CandidateTeam } from '@/lib/teamMatch'
import type { TeamSeeking } from '@/lib/useTeamSeeking'
import SeekingPill from './SeekingPill'

const pathname = vi.fn(() => '/analysis')
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => pathname(),
}))

const team = (id: string): CandidateTeam => ({
  id,
  name: `팀${id}`,
  region: '서울 강남구',
  size: '5',
  why: [],
})

function state(over: Partial<TeamSeeking> = {}): TeamSeeking {
  return {
    seeking: { teamId: 't1', startedAt: 0, seen: [] },
    teams: [],
    fresh: [],
    loaded: true,
    start: vi.fn(),
    stop: vi.fn(),
    acknowledge: vi.fn(),
    ...over,
  }
}

describe('머리칸의 「팀 찾는 중」', () => {
  it('🔴 안 찾는 중이면 아무것도 안 그린다', () => {
    const { container } = render(<SeekingPill seeking={state({ seeking: null })} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('찾는 중이면 어느 화면에서도 보인다', () => {
    pathname.mockReturnValue('/analysis')
    render(<SeekingPill seeking={state()} />)
    expect(screen.getByText(/팀 찾는 중/)).toBeInTheDocument()
  })

  it('홈이 아니면 눌러서 홈으로 갈 수 있다', () => {
    pathname.mockReturnValue('/analysis')
    render(<SeekingPill seeking={state()} />)
    expect(screen.getByRole('link')).toHaveAttribute('href', '/')
  })

  it('🔴 홈에서는 고리를 안 만든다 — 판이 이미 옆에 떠 있다', () => {
    pathname.mockReturnValue('/')
    render(<SeekingPill seeking={state()} />)
    expect(screen.queryByRole('link')).toBeNull()
    expect(screen.getByText(/팀 찾는 중/)).toBeInTheDocument()
  })

  it('잡히는 후보 수를 함께 적는다', () => {
    pathname.mockReturnValue('/analysis')
    render(<SeekingPill seeking={state({ teams: [team('a'), team('b')] })} />)
    expect(screen.getByText(/2곳/)).toBeInTheDocument()
  })

  it('🔴 아직 한 번도 못 읽었으면 「0곳」이라고 적지 않는다', () => {
    pathname.mockReturnValue('/analysis')
    render(<SeekingPill seeking={state({ loaded: false })} />)
    expect(screen.queryByText(/곳/)).toBeNull()
  })

  it('🔴 새로 생긴 곳은 전체 수와 **따로** 적는다', () => {
    /* 한 곳이 빠지고 다른 곳이 들어오면 전체 수는 그대로다 — 그 칸만 보면
       새 팀이 생긴 것이 화면에 아예 안 나타난다. */
    pathname.mockReturnValue('/analysis')
    render(
      <SeekingPill seeking={state({ teams: [team('a'), team('b')], fresh: [team('b')] })} />,
    )
    expect(screen.getByText(/2곳/)).toBeInTheDocument()
    expect(screen.getByText(/새로 1곳/)).toBeInTheDocument()
  })
})
