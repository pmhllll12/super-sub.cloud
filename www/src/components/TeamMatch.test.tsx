import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PREFS_KEY, type MatchPrefs } from '@/lib/matchPrefs'
import TeamMatch from './TeamMatch'

/**
 * **비슷한 팀 명단** — 「팀 매칭」이 여는 판(사용자 요청, 2026-09-10).
 *
 * ⚠️ 목록도 신청도 **전부 mock 이다**(`lib/teamMatch.ts`). 그래서 이 시험은
 * 서버로 무엇이 나갔는지가 아니라 **화면이 무엇을 말하는지**를 붙든다.
 */
/** 이미 정해 둔 조건 — 이게 없으면 판이 명단 대신 **조건부터 묻는다**. */
const PREFS: MatchPrefs = {
  regions: ['서울 강남구'],
  times: [{ day: 6, from: '09:00', to: '11:00' }],
  positions: [],
}

describe('비슷한 팀 명단', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem(PREFS_KEY, JSON.stringify({ team: PREFS }))
  })

  const open = (onMatched = vi.fn()) => {
    render(<TeamMatch size="5" closing={false} onClose={() => {}} onMatched={onMatched} />)
    return onMatched
  }

  /* mock 이 일부러 늦게 답한다 — 즉시 답하면 「찾는 중」 화면을 안 만들게 되고,
     진짜 경로가 붙는 날 그 화면이 없다는 것을 알게 된다. */
  it('찾는 동안 그렇게 말한다', () => {
    open()
    expect(screen.getByText('비슷한 팀을 찾고 있습니다…')).toBeInTheDocument()
  })

  it('우리와 같은 크기의 팀만 나온다', async () => {
    open()
    expect(await screen.findByText('번개FC')).toBeInTheDocument()
    // mock 의 세 팀이 다 5:5 다 — 7:7 을 넣으면 아무도 안 나온다.
    expect(screen.getAllByRole('button', { name: '경기 신청' })).toHaveLength(3)
  })

  /* 🔴 **크기마다 팀이 나온다.** 5:5 만 mock 에 넣어 뒀더니 판을 7:7 로 바꾼
     사람에게 「조건이 맞는 팀이 없습니다」만 떴다(사용자 지적, 2026-09-10) —
     mock 이 비어 있는 것과 조건이 안 맞는 것이 화면에서 같아 보인다. */
  it.each([
    ['3', '삼삼오오'],
    ['5', '번개FC'],
    ['7', '강남 세븐스'],
  ])('%s:%s 판에도 팀이 나온다', async (size, first) => {
    render(<TeamMatch size={size} closing={false} onClose={() => {}} onMatched={vi.fn()} />)
    expect(await screen.findByText(first)).toBeInTheDocument()
  })

  /* 🔴 **크기가 섞이지 않는다** — 5:5 를 짜 놓고 7:7 팀이 나오면 그 자체로
     「비슷하다」가 아니다. */
  it('우리와 다른 크기의 팀은 안 나온다', async () => {
    open()
    await screen.findByText('번개FC')
    expect(screen.queryByText('강남 세븐스')).toBeNull()
    expect(screen.queryByText('삼삼오오')).toBeNull()
  })

  /* 🔴 **근거를 지어내지 않는다 — 조건과 대조해서 만든다.** 손으로 적어 두면
     「토요일」이라 해 놓고 날짜가 일요일인 일이 생긴다(실제로 있었다). */
  it('조건과 실제로 겹치는 것만 근거로 적는다', async () => {
    open()
    await screen.findByText('번개FC')
    /* 조건은 「서울 강남구 · 토 09:00~11:00」.
       지역은 번개FC(강남구) 하나, 시간은 토요일 둘(번개 10시 · 망원 9시)이
       겹치고 수원(일요일)은 안 겹친다. */
    expect(screen.getAllByText('같은 지역')).toHaveLength(1)
    expect(screen.getAllByText('시간이 맞음')).toHaveLength(2)
    // 크기는 늘 같으므로 셋 다 붙는다.
    expect(screen.getAllByText('5 : 5')).toHaveLength(3)
  })

  /* 🔴 **안 겹친다고 빼지 않는다.** 조건은 「이런 걸 찾는다」이지 「이것만
     보겠다」가 아니다 — 다 빼면 조건을 조금 잘못 적은 사람에게 빈 화면만 남는다.
     대신 근거가 많은 쪽이 위로 온다. */
  it('근거가 많은 팀이 앞에 온다', async () => {
    open()
    await screen.findByText('번개FC')
    const names = [...document.querySelectorAll('.ss-tm-name')].map((el) => el.textContent)
    expect(names[0]).toBe('번개FC')
    expect(names).toHaveLength(3)
  })

  /* 🔴 조건을 아직 안 정했으면 **명단 대신 묻는다**(사용자 결정). */
  it('조건이 없으면 먼저 묻는다', async () => {
    localStorage.clear()
    open()
    expect(await screen.findByText('어떤 경기를 찾으세요?')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '경기 신청' })).toBeNull()
  })

  it('정해 둔 조건이 있으면 고칠 길만 둔다', async () => {
    open()
    await screen.findByText('번개FC')
    expect(screen.queryByText('어떤 경기를 찾으세요?')).toBeNull()
    expect(screen.getByRole('button', { name: '설정 수정' })).toBeInTheDocument()
  })

  it('신청하면 수락을 기다린다고 말하고, 수락되면 알린다', async () => {
    const user = userEvent.setup()
    const onMatched = open()
    await screen.findByText('번개FC')

    await user.click(screen.getAllByRole('button', { name: '경기 신청' })[0])
    expect(screen.getByRole('button', { name: '수락을 기다립니다…' })).toBeInTheDocument()

    await waitFor(() => expect(onMatched).toHaveBeenCalled(), { timeout: 3000 })
    expect(onMatched.mock.calls[0][0].name).toBe('번개FC')
  })

  /* 🔴 **한 번에 한 곳에만 신청한다.** 여러 곳에 걸어 두면 둘이 동시에
     수락했을 때 어느 경기가 잡힌 것인지 화면이 답할 수 없다. */
  it('기다리는 동안 다른 팀에는 신청하지 못한다', async () => {
    const user = userEvent.setup()
    open()
    await screen.findByText('번개FC')

    await user.click(screen.getAllByRole('button', { name: '경기 신청' })[0])
    for (const b of screen.getAllByRole('button', { name: '경기 신청' })) {
      expect(b).toBeDisabled()
    }
  })

  // ⚠️ 아무 데도 안 보낸다는 것을 숨기지 않는다 — 숨기면 진짜 신청된 줄 안다.
  it('데모라는 것을 적어 둔다', () => {
    open()
    expect(screen.getByText(/데모입니다/)).toBeInTheDocument()
  })
})
