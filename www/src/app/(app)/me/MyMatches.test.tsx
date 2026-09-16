import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { Match } from '@/server/backend'
import MyMatches from './MyMatches'

/**
 * **내 경기** — 서버가 준 다가오는 경기.
 *
 * ✅ **2026-09-16 — 브라우저에만 남던 「팀 매칭으로 잡힌 것」을 걷었다.**
 * 계약 3-15절이 생기면서 수락하면 서버에 진짜 `match` 가 만들어지고 이
 * 목록에 그대로 온다 — 둘 다 두면 같은 경기가 두 번 보였고, localStorage 는
 * mock 이 아니라 브라우저라 **진짜 도메인에서도** 그랬다.
 */
const SERVER: Match = {
  id: 'm1',
  team_id: 't1',
  played_at: '2026-09-12T10:00:00Z',
  place: '강남 풋살장 2구장',
  needs: [{ position_code: 'GK', position_label: '골키퍼', head_count: 1 }],
}
describe('내 경기', () => {
  it('없으면 다가오는 경기가 없다고 말한다', () => {
    render(<MyMatches matches={[]} />)
    expect(screen.getByText('다가오는 경기가 없습니다.')).toBeInTheDocument()
  })

  it('서버가 준 경기를 그린다', () => {
    render(<MyMatches matches={[SERVER]} />)
    expect(screen.getByText('강남 풋살장 2구장')).toBeInTheDocument()
    expect(screen.getByText('골키퍼 1')).toBeInTheDocument()
  })



  // 🔴 같은 팀에 두 번 신청해도 두 줄이 되지 않는다.

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
