import { act, fireEvent, render, screen } from '@testing-library/react'
import SpotNudge from './SpotNudge'

// 「내 프로필」 — 카드(둥근 상자) + 그 밑 글자
function profile() {
  const link = document.createElement('a')
  link.className = 'ss-home-profile'
  const card = document.createElement('article')
  card.className = 'ss-pcard'
  card.appendChild(document.createElement('div'))
  card.getBoundingClientRect = () => ({ top: 40, left: 800, width: 90, height: 120 }) as DOMRect
  const label = document.createElement('span')
  label.className = 'ss-home-profile-label'
  label.textContent = '내 프로필'
  label.getBoundingClientRect = () => ({ top: 170, left: 815, width: 60, height: 20 }) as DOMRect
  link.append(card, label)
  document.body.appendChild(link)
  return () => link.remove()
}

const TARGETS = ['.ss-home-profile .ss-pcard', '.ss-home-profile-label']

describe('한 곳만 밝게 두는 안내', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('카드와 글자에 **따로** 딱 맞는 구멍을 뚫는다 — 둘레 배경까지 뚫지 않는다', () => {
    const cleanup = profile()
    const { baseElement } = render(<SpotNudge targets={TARGETS} message="안내" onDone={() => {}} />)
    const holes = [...baseElement.querySelectorAll('mask rect[fill="black"]')]
    expect(holes.map((r) => [r.getAttribute('x'), r.getAttribute('y'), r.getAttribute('width'), r.getAttribute('height')])).toEqual([
      ['800', '40', '90', '120'],
      ['815', '170', '60', '20'],
    ])
    // 문장은 맨 아래 구멍 밑
    expect(screen.getByRole('status').style.top).toBe('204px') // 170 + 20 + 14
    cleanup()
  })

  it('다 나오기 전에 누른 것은 걷지 않고, 그 뒤 누르면 걷힌다', () => {
    const cleanup = profile()
    const onDone = vi.fn()
    render(<SpotNudge targets={TARGETS} message="안내" onDone={onDone} />)
    fireEvent.pointerDown(document.body)
    expect(screen.getByRole('status')).toHaveAttribute('data-state', 'in')
    act(() => vi.advanceTimersByTime(600))
    fireEvent.pointerDown(document.body)
    expect(screen.getByRole('status')).toHaveAttribute('data-state', 'out')
    act(() => vi.advanceTimersByTime(600))
    expect(onDone).toHaveBeenCalled()
    cleanup()
  })

  it('아무도 안 누르면 5초 뒤 걷힌다', () => {
    const cleanup = profile()
    render(<SpotNudge targets={TARGETS} message="안내" onDone={() => {}} />)
    // 가짜 시계는 한 번에 넘기면 도중에 새로 걸린 타이머를 못 돌린다 — 나눠 넘긴다.
    act(() => vi.advanceTimersByTime(600))
    act(() => vi.advanceTimersByTime(4300))
    expect(screen.getByRole('status')).toHaveAttribute('data-state', 'on')
    act(() => vi.advanceTimersByTime(200))
    expect(screen.getByRole('status')).toHaveAttribute('data-state', 'out')
    cleanup()
  })
})

describe('구멍의 둥글기', () => {
  it('알약 단추(999px)는 높이의 절반으로 — 타원이 되지 않게 rx·ry 가 같다', () => {
    const btn = document.createElement('a')
    btn.className = 'pill'
    btn.style.borderTopLeftRadius = '999px' // jsdom 은 줄임 속성을 안 펼친다
    btn.style.borderTopWidth = '1px'
    btn.style.border = '1px solid white'
    btn.textContent = '프로필 카드 수정'
    btn.getBoundingClientRect = () => ({ top: 700, left: 80, width: 180, height: 36 }) as DOMRect
    document.body.appendChild(btn)
    const { baseElement } = render(<SpotNudge targets={['.pill']} message="안내" onDone={() => {}} />)
    const hole = baseElement.querySelector('mask rect[fill="black"]')!
    expect(hole.getAttribute('rx')).toBe('18')
    expect(hole.getAttribute('ry')).toBe('18')
    // 테두리가 있으니 글자 폭이 아니라 단추 상자째 뚫는다
    expect(hole.getAttribute('width')).toBe('180')
    btn.remove()
  })
})
