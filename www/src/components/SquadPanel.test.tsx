import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { PlayerCard } from '@/server/backend'
import SquadPanel from './SquadPanel'

const CARD: PlayerCard = {
  id: 'c1',
  public_slug: 'hong-gildong-4f2a',
  og_image_key: 'cards/7b4d.png',
  user: { id: 'u1', nickname: '홍길동' },
  titles: [],
}

describe('스쿼드', () => {
  it('판 위에 카드 다섯 장을 포지션 자리대로 앉힌다', () => {
    const { container } = render(<SquadPanel card={CARD} />)
    expect(container.querySelectorAll('.ss-pcard')).toHaveLength(5)
    expect(screen.getAllByRole('button', { name: /자리에 선수 넣기/ })).toHaveLength(4)
    expect(['FW', 'MF', 'DF', 'GK'].every((p) => screen.getAllByText(p).length > 0)).toBe(true)
    expect(screen.getByText('THREE LUNGS')).toBeInTheDocument()
  })

  // + 만 눌리면 카드를 눌렀는데 아무 일도 안 일어나는 순간이 생긴다.
  it('카드 전체가 버튼이다 — + 는 장식일 뿐이다', () => {
    const { container } = render(<SquadPanel card={CARD} />)
    const seat = screen.getByRole('button', { name: 'GK 자리에 선수 넣기' })
    // 버튼 안에 카드가 통째로 들어 있고, 그 안에 또 버튼이 있지 않다.
    expect(seat.querySelector('.ss-pcard')).not.toBeNull()
    expect(seat.querySelector('button')).toBeNull()
    expect(container.querySelector('.ss-squad-plus')).toHaveAttribute('aria-hidden', 'true')
  })

  it('빈 카드에도 같은 머리글이 있다 — 눌러 보기 전에 무슨 자리인지 안다', () => {
    render(<SquadPanel card={CARD} />)
    expect(screen.getAllByText('PLAYER CARD')).toHaveLength(5)
  })

  it('가만히 두면 추천 판이 없다', () => {
    render(<SquadPanel card={CARD} />)
    expect(screen.queryByRole('complementary')).toBeNull()
  })

  // 이름을 직접 적는 게 아니라 추천에서 고른다.
  it('빈 자리를 누르면 그 포지션의 추천 판이 나온다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel card={CARD} />)
    await user.click(screen.getByRole('button', { name: 'GK 자리에 선수 넣기' }))
    expect(screen.getByRole('complementary', { name: 'GK 추천 선수' })).toBeInTheDocument()
    // 제목이 곧 몇 명이 왔는지다 — 자리마다 추천 수가 다르다.
    expect(screen.getByRole('heading', { name: 'AI 추천 GK 2명' })).toBeInTheDocument()
    // 이름을 적는 칸은 없다.
    expect(screen.queryByRole('textbox')).toBeNull()
  })

  it('자리마다 다른 추천이, 다른 수만큼 나온다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel card={CARD} />)
    await user.click(screen.getAllByRole('button', { name: 'MF 자리에 선수 넣기' })[0])
    expect(screen.getByRole('heading', { name: 'AI 추천 MF 3명' })).toBeInTheDocument()
    expect(screen.getAllByRole('listitem')).toHaveLength(3)
  })

  it('추천에서 고르면 그 자리에 앉고 판이 닫힌다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel card={CARD} />)
    await user.click(screen.getByRole('button', { name: 'DF 자리에 선수 넣기' }))
    await user.click(screen.getByRole('button', { name: /박도현/ }))
    expect(screen.getByRole('button', { name: '박도현 빼기' })).toBeInTheDocument()
    await waitFor(() => expect(screen.queryByRole('complementary')).toBeNull())
  })

  it('닫기 버튼과 Esc 로 닫는다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel card={CARD} />)
    await user.click(screen.getByRole('button', { name: 'GK 자리에 선수 넣기' }))
    await user.click(screen.getByRole('button', { name: '추천 닫기' }))
    await waitFor(() => expect(screen.queryByRole('complementary')).toBeNull())

    await user.click(screen.getByRole('button', { name: 'GK 자리에 선수 넣기' }))
    await user.keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByRole('complementary')).toBeNull())
  })

  it('넣은 선수를 눌러 뺀다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel card={CARD} />)
    await user.click(screen.getByRole('button', { name: 'DF 자리에 선수 넣기' }))
    await user.click(screen.getByRole('button', { name: /박도현/ }))
    await user.click(screen.getByRole('button', { name: '박도현 빼기' }))
    expect(screen.getByRole('button', { name: 'DF 자리에 선수 넣기' })).toBeInTheDocument()
  })

  it('내 카드가 없으면 그 자리에 그렇게 적는다', () => {
    const { container } = render(<SquadPanel card={null} />)
    expect(container.querySelectorAll('.ss-pcard')).toHaveLength(5)
    expect(screen.getByText('아직 카드가 없습니다')).toBeInTheDocument()
  })
})

describe('스쿼드 — 지인 찾기', () => {
  function openFriends() {
    return render(<SquadPanel card={CARD} friendSearch />)
  }

  it('켜면 판 옆에 검색창과 지인 목록이 나온다', () => {
    openFriends()
    expect(screen.getByRole('complementary', { name: '지인 찾기' })).toBeInTheDocument()
    expect(screen.getByLabelText('지인 닉네임')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /홍길동/ })).toBeInTheDocument()
  })

  it('닉네임을 치면 그 사람만 남는다', async () => {
    const user = userEvent.setup()
    openFriends()
    await user.type(screen.getByLabelText('지인 닉네임'), '김철')
    expect(screen.getByRole('button', { name: /김철수/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /홍길동/ })).toBeNull()
  })

  it('찾는 사람이 없으면 그렇게 적는다', async () => {
    const user = userEvent.setup()
    openFriends()
    await user.type(screen.getByLabelText('지인 닉네임'), '없는사람')
    expect(screen.getByText('찾는 지인이 없습니다')).toBeInTheDocument()
  })

  // 🔴 자리는 **왼쪽 진짜 판**에서 고른다 — 작은 스쿼드 판을 여기 하나 더
  // 그리면 판이 둘이 되고, MF 가 둘이라 포지션 이름만으로는 못 고른다.
  it('지인을 고르면 빈 자리 버튼이 넣기 버튼으로 바뀐다', async () => {
    const user = userEvent.setup()
    openFriends()
    expect(screen.getAllByRole('button', { name: /자리에 선수 넣기/ })).toHaveLength(4)

    await user.click(screen.getByRole('button', { name: /김철수/ }))
    expect(screen.getAllByRole('button', { name: /자리에 김철수 넣기/ })).toHaveLength(4)
    expect(screen.queryByRole('button', { name: /자리에 선수 넣기/ })).toBeNull()
  })

  it('빈 자리를 누르면 그 자리에 앉는다', async () => {
    const user = userEvent.setup()
    openFriends()
    await user.click(screen.getByRole('button', { name: /김철수/ }))
    await user.click(screen.getByRole('button', { name: 'GK 자리에 김철수 넣기' }))

    expect(screen.getByRole('button', { name: '김철수 빼기' })).toBeInTheDocument()
    // 여러 명을 이어 넣는 게 보통이라 판은 열어 둔다.
    expect(screen.getByRole('complementary', { name: '지인 찾기' })).toBeInTheDocument()
  })

  it('고른 사람을 한 번 더 누르면 고르기가 풀린다', async () => {
    const user = userEvent.setup()
    openFriends()
    const row = screen.getByRole('button', { name: /김철수/ })
    await user.click(row)
    await user.click(row)
    expect(screen.getAllByRole('button', { name: /자리에 선수 넣기/ })).toHaveLength(4)
  })

  // 두 판은 같은 자리에 뜬다 — 동시에 열면 겹친다.
  it('지인 찾기가 열려 있으면 빈 자리를 눌러도 추천이 안 열린다', async () => {
    const user = userEvent.setup()
    openFriends()
    await user.click(screen.getByRole('button', { name: 'GK 자리에 선수 넣기' }))
    expect(screen.queryByRole('complementary', { name: /추천 선수/ })).toBeNull()
    expect(screen.getByRole('complementary', { name: '지인 찾기' })).toBeInTheDocument()
  })

  // 🔴 표식이 없으면 방금 넣은 사람이 평범한 줄로 남아 또 고르게 된다.
  it('이미 넣은 사람은 목록에서 자리 이름과 함께 잠긴다', async () => {
    const user = userEvent.setup()
    openFriends()
    await user.click(screen.getByRole('button', { name: /김철수/ }))
    await user.click(screen.getByRole('button', { name: 'GK 자리에 김철수 넣기' }))

    const row = screen.getByRole('button', { name: /김철수.*GK/ })
    expect(row).toBeDisabled()
    // 다른 사람은 그대로 고를 수 있다.
    expect(screen.getByRole('button', { name: /홍길동/ })).toBeEnabled()
  })

  it('빼면 목록에서 다시 고를 수 있다', async () => {
    const user = userEvent.setup()
    openFriends()
    await user.click(screen.getByRole('button', { name: /김철수/ }))
    await user.click(screen.getByRole('button', { name: 'GK 자리에 김철수 넣기' }))
    await user.click(screen.getByRole('button', { name: '김철수 빼기' }))

    expect(screen.getByRole('button', { name: /김철수/ })).toBeEnabled()
  })

  // 카드 전체가 이미 '빼기' 버튼이다 — 표식은 장식이라 버튼이 아니어야 한다.
  it('넣은 자리에는 빼기 표식이 붙는다', async () => {
    const user = userEvent.setup()
    const { container } = openFriends()
    expect(container.querySelector('.ss-squad-remove')).toBeNull()

    await user.click(screen.getByRole('button', { name: /김철수/ }))
    await user.click(screen.getByRole('button', { name: 'GK 자리에 김철수 넣기' }))

    const badge = container.querySelector('.ss-squad-remove')
    expect(badge).not.toBeNull()
    expect(badge).toHaveAttribute('aria-hidden', 'true')
    expect(badge?.closest('button')).toBe(screen.getByRole('button', { name: '김철수 빼기' }))
  })

  it('닫기를 누르면 부모에게 알린다', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(<SquadPanel card={CARD} friendSearch onCloseFriendSearch={onClose} />)
    await user.click(screen.getByRole('button', { name: '지인 찾기 닫기' }))
    expect(onClose).toHaveBeenCalled()
  })
})
