import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MatchPrefsForm from './MatchPrefs'

/**
 * **경기 조건 판** — 팀장 · 팀원이 같은 조각을 쓴다(사용자 결정, 2026-09-10).
 *
 * 🔴 이 값이 **RAG 가 「비슷하다」를 판단할 근거**다. 그래서 시험이 붙드는
 * 것은 모양이 아니라 **저장되는 값의 성질**이다.
 */
describe('경기 조건 판', () => {
  const open = (over: Partial<React.ComponentProps<typeof MatchPrefsForm>> = {}) => {
    const onDone = vi.fn()
    render(<MatchPrefsForm kind="team" onDone={onDone} {...over} />)
    return onDone
  }
  const go = () => screen.getByRole('button', { name: '팀 찾기' })

  /* 🔴 **동네와 시간이 하나씩은 있어야 한다** — 빈 조건으로는 아무것도 못 좁힌다. */
  it('비어 있으면 찾을 수 없다', () => {
    open()
    expect(go()).toBeDisabled()
  })

  /* 🔴 **자유 입력이지만 저장은 목록의 값이다.** 안 그러면 「강남구」·「서울
     강남구」가 다른 값이 되어 대조가 안 된다. */
  it('적으면 후보가 나오고, 고른 것만 담긴다', async () => {
    const user = userEvent.setup()
    const onDone = open()
    await user.type(screen.getByRole('textbox'), '강남')

    // 후보에서 고르기 전에는 아무것도 안 담긴다.
    expect(screen.queryByRole('button', { name: '서울 강남구 빼기' })).toBeNull()
    await user.click(screen.getByRole('button', { name: '서울 강남구' }))
    expect(screen.getByRole('button', { name: '서울 강남구 빼기' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '+ 시간 추가' }))
    await user.click(go())
    expect(onDone.mock.calls[0][0].regions).toEqual(['서울 강남구'])
  })

  // 목록에 없으면 그렇게 말한다 — 조용히 비어 있으면 고장으로 읽힌다.
  it('목록에 없는 동네는 없다고 말한다', async () => {
    const user = userEvent.setup()
    open()
    await user.type(screen.getByRole('textbox'), '없는동네')
    expect(screen.getByText('그런 동네가 목록에 없습니다.')).toBeInTheDocument()
  })

  it('같은 동네를 두 번 담지 않는다', async () => {
    const user = userEvent.setup()
    open({ value: { regions: ['서울 강남구'], times: [], positions: [] } })
    await user.type(screen.getByRole('textbox'), '강남')
    // 이미 담긴 것은 후보에서 빠진다.
    expect(screen.queryByRole('button', { name: '서울 강남구' })).toBeNull()
  })

  /* 🔴 **뒤집힌 시간을 만들 수 없다.** 시작이 끝을 넘으면 겹침 계산이 늘
     거짓이 되어 조용히 아무것도 안 걸린다. */
  it('시작을 끝 뒤로 옮기면 끝이 밀린다', async () => {
    const user = userEvent.setup()
    const onDone = open({ value: { regions: ['서울 강남구'], times: [], positions: [] } })
    await user.click(screen.getByRole('button', { name: '+ 시간 추가' }))
    await user.selectOptions(screen.getByLabelText('시작 시각'), '13:00')

    await user.click(go())
    const slot = onDone.mock.calls[0][0].times[0]
    expect(slot.from).toBe('13:00')
    expect(slot.to > slot.from).toBe(true)
  })

  it('시간을 뺄 수 있다', async () => {
    const user = userEvent.setup()
    open({ value: { regions: ['서울 강남구'], times: [], positions: [] } })
    await user.click(screen.getByRole('button', { name: '+ 시간 추가' }))
    // 지역 칩의 「빼기」와 겹치지 않게 시간 쪽을 이름으로 집는다.
    await user.click(screen.getByRole('button', { name: '토 09:00~11:00 빼기' }))
    expect(screen.queryByLabelText('요일')).toBeNull()
    expect(go()).toBeDisabled()
  })

  /* 🔴 **「내 자리」는 팀원 쪽에만 있다** — 팀은 자리를 고르지 않는다. */
  it('팀 조건에는 내 자리 칸이 없다', async () => {
    const user = userEvent.setup()
    open({ value: { regions: ['서울 강남구'], times: [], positions: [] } })
    await user.click(screen.getByRole('button', { name: '+ 시간 추가' }))
    expect(screen.queryByText('내 자리')).toBeNull()
  })

  /* 처음 묻는 자리에서는 그만둘 데가 없다 — 고칠 때만 준다. */
  it('처음 물을 때는 그만두기가 없다', () => {
    open()
    expect(screen.queryByRole('button', { name: '그만두기' })).toBeNull()
  })

  it('고치는 중이면 그만둘 수 있다', () => {
    const onCancel = vi.fn()
    open({ value: { regions: [], times: [], positions: [] }, onCancel })
    expect(screen.getByRole('button', { name: '그만두기' })).toBeInTheDocument()
  })

  // ⚠️ 어디에 남는지 밝힌다 — 계약에 자리가 없다.
  it('브라우저에만 남는다고 적어 둔다', () => {
    open()
    expect(screen.getByText(/이 브라우저에만/)).toBeInTheDocument()
  })
})
