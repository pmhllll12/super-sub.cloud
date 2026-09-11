import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { Match } from '@/server/backend'
import { BOOKED_KEY, book } from '@/lib/bookedMatches'
import type { MatchTeam } from '@/lib/teamMatch'
import MyMatches from './MyMatches'

/**
 * **내 경기** — 서버가 준 경기 + 팀 매칭으로 잡힌 것(사용자 요청, 2026-09-10).
 *
 * 🔴 **두 목록을 섞지 않는다.** 위는 서버가 준 진짜 경기, 아래는 계약이 없어
 * 브라우저에만 남은 데모다 — 한 줄로 뭉치면 어느 것이 진짜인지 모른다.
 */
const SERVER: Match = {
  id: 'm1',
  team_id: 't1',
  played_at: '2026-09-12T10:00:00Z',
  place: '강남 풋살장 2구장',
  needs: [{ position_code: 'GK', position_label: '골키퍼', head_count: 1 }],
}
const TEAM: MatchTeam = {
  id: 'mt-1',
  name: '번개FC',
  region: '서울 강남구',
  size: '5',
  playedAt: '2026-09-19T10:00:00',
  place: '강남 풋살장 1구장',
  why: ['같은 지역'],
  squad: [],
}

beforeEach(() => localStorage.clear())

describe('내 경기', () => {
  it('둘 다 없으면 다가오는 경기가 없다고 말한다', () => {
    render(<MyMatches matches={[]} />)
    expect(screen.getByText('다가오는 경기가 없습니다.')).toBeInTheDocument()
  })

  it('서버가 준 경기를 그린다', () => {
    render(<MyMatches matches={[SERVER]} />)
    expect(screen.getByText('강남 풋살장 2구장')).toBeInTheDocument()
    expect(screen.getByText('골키퍼 1')).toBeInTheDocument()
  })

  /* 🔴 **수락되면 여기 뜬다** — 이 항목의 요점이다. */
  it('팀 매칭으로 잡힌 경기가 상대 이름과 함께 뜬다', async () => {
    book(TEAM)
    render(<MyMatches matches={[]} />)
    expect(await screen.findByText('번개FC')).toBeInTheDocument()
    expect(screen.getByText('강남 풋살장 1구장')).toBeInTheDocument()
    // 서버 경기가 없어도 「없습니다」가 아니다 — 잡힌 것이 있다.
    expect(screen.queryByText('다가오는 경기가 없습니다.')).toBeNull()
  })

  /* 🔴 **어느 것이 진짜인지 표로 가른다.** 데모라는 것도 숨기지 않는다. */
  it('잡힌 줄에는 표를 달고 데모라고 적는다', async () => {
    book(TEAM)
    render(<MyMatches matches={[SERVER]} />)
    await screen.findByText('번개FC')
    expect(screen.getByText('팀 매칭')).toBeInTheDocument()
    expect(screen.getByText(/데모입니다/)).toBeInTheDocument()
    expect(document.querySelectorAll('[data-booked="true"]')).toHaveLength(1)
  })

  // 🔴 같은 팀에 두 번 신청해도 두 줄이 되지 않는다.
  it('같은 팀은 한 줄이다', async () => {
    book(TEAM)
    book({ ...TEAM, place: '고친 구장' })
    render(<MyMatches matches={[]} />)
    await screen.findByText('번개FC')
    expect(document.querySelectorAll('[data-booked="true"]')).toHaveLength(1)
    expect(screen.getByText('고친 구장')).toBeInTheDocument()
  })

  /* 저장된 값은 사람이 손댈 수 있는 자리다 — 깨져 있다고 화면이 죽으면 안 된다. */
  it('저장본이 깨져 있으면 없는 것으로 친다', () => {
    localStorage.setItem(BOOKED_KEY, '{{{')
    render(<MyMatches matches={[]} />)
    expect(screen.getByText('다가오는 경기가 없습니다.')).toBeInTheDocument()
  })
})

/**
 * 🔴 **판이 목록 하나로 길어지면 왼쪽 칸이 통째로 밀린다**(사용자 요청,
 * 2026-09-11). **다음 경기 하나만** 보이고 나머지는 「더보기」로 편다.
 *
 * ⚠️ **잘라 내는 것이 아니라 접는 것**이다 — 나머지는 처음부터 DOM 에 있고
 * 펴는 것은 높이뿐이다. 잘라 두면 낭독기와 본문 검색에서 사라진다.
 */
describe('내 경기 — 더보기', () => {
  const many: Match[] = [1, 2, 3, 4].map((n) => ({
    ...SERVER,
    id: `m${n}`,
    place: `${n}번 구장`,
  }))

  it('하나뿐이면 더보기가 없다', () => {
    render(<MyMatches matches={many.slice(0, 1)} />)
    expect(screen.queryByRole('button', { name: /더보기/ })).toBeNull()
  })

  it('둘부터는 더보기가 붙고 몇 개가 더 있는지 말한다', () => {
    render(<MyMatches matches={many} />)
    expect(screen.getByRole('button', { name: '더보기 3' })).toBeInTheDocument()
  })

  it('접혀 있어도 나머지가 DOM 에 남아 있다', () => {
    render(<MyMatches matches={many} />)
    // 🔴 감추는 것은 높이뿐이다 — 지우면 낭독기가 못 읽고 본문 검색에서도 빠진다.
    expect(screen.getByText('4번 구장')).toBeInTheDocument()
  })

  it('접힌 동안에는 나머지를 접근성 트리에서 뺀다', () => {
    render(<MyMatches matches={many} />)
    const fold = screen.getByTestId('match-fold')
    expect(fold.getAttribute('aria-hidden')).toBe('true')
    expect(fold.dataset.open).toBe('false')
  })

  it('누르면 펴지고 단추가 접기로 바뀐다', async () => {
    const user = userEvent.setup()
    render(<MyMatches matches={many} />)

    await user.click(screen.getByRole('button', { name: '더보기 3' }))

    expect(screen.getByTestId('match-fold').dataset.open).toBe('true')
    expect(screen.getByTestId('match-fold').getAttribute('aria-hidden')).toBeNull()
    expect(screen.getByRole('button', { name: '접기' })).toBeInTheDocument()
  })
})
