import { act, fireEvent, render, screen } from '@testing-library/react'
import SpotNudge from './SpotNudge'

function target() {
  const el = document.createElement('a')
  el.className = 'ss-home-profile'
  el.getBoundingClientRect = () => ({ top: 40, left: 800, width: 90, height: 150 }) as DOMRect
  document.body.appendChild(el)
  return () => el.remove()
}

describe('한 곳만 밝게 두는 안내', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('과녁 둘레에 구멍을 두고, 그 밑에 문장을 띄운다', () => {
    const cleanup = target()
    const { baseElement } = render(<SpotNudge target=".ss-home-profile" message="안내" onDone={() => {}} />)
    const dim = baseElement.querySelector<HTMLElement>('.ss-nudge-dim')!
    expect(dim.style.left).toBe('792px') // 800 - 8
    expect(dim.style.width).toBe('106px') // 90 + 16
    expect(screen.getByRole('status')).toHaveTextContent('안내')
    expect(screen.getByRole('status').style.top).toBe('210px') // 32 + 166 + 12
    cleanup()
  })

  it('다 나오기 전에 누른 것은 걷지 않고, 그 뒤 누르면 걷힌다', () => {
    const cleanup = target()
    const onDone = vi.fn()
    render(<SpotNudge target=".ss-home-profile" message="안내" onDone={onDone} />)
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
    const cleanup = target()
    render(<SpotNudge target=".ss-home-profile" message="안내" onDone={() => {}} />)
    // 가짜 시계는 한 번에 넘기면 도중에 새로 걸린 타이머를 못 돌린다 — 나눠 넘긴다.
    act(() => vi.advanceTimersByTime(600))
    act(() => vi.advanceTimersByTime(4300))
    expect(screen.getByRole('status')).toHaveAttribute('data-state', 'on')
    act(() => vi.advanceTimersByTime(200))
    expect(screen.getByRole('status')).toHaveAttribute('data-state', 'out')
    cleanup()
  })
})
