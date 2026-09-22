import { act, fireEvent, render, screen } from '@testing-library/react'
import SeatPicker from './SeatPicker'

const SEATS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

describe('테스트 번호 고르기', () => {
  it('알약에 지금 번호를 적고, 누르면 1~10 판이 펼쳐진다', () => {
    render(<SeatPicker label="테스트 번호" seat={3} seats={SEATS} onPick={() => {}} />)
    const pill = screen.getByRole('button', { name: '테스트 번호 3번' })
    expect(pill).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('group')).toBeNull()
    fireEvent.click(pill)
    expect(pill).toHaveAttribute('aria-expanded', 'true')
    const nums = screen.getAllByRole('button', { name: /^\d+번$/ })
    expect(nums.map((b) => b.textContent)).toEqual(SEATS.map((n) => `${n}번`))
    expect(screen.getByRole('button', { name: '3번' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('아직 안 골랐으면 「자동」', () => {
    render(<SeatPicker label="테스트 번호" seat={null} seats={SEATS} onPick={() => {}} />)
    expect(screen.getByRole('button', { name: '테스트 번호 자동' })).toHaveTextContent('자동')
  })

  it('번호를 누르면 고르고 판이 걷힌다', () => {
    vi.useFakeTimers()
    const onPick = vi.fn()
    render(<SeatPicker label="테스트 번호" seat={1} seats={SEATS} onPick={onPick} />)
    fireEvent.click(screen.getByRole('button', { name: '테스트 번호 1번' }))
    fireEvent.click(screen.getByRole('button', { name: '7번' }))
    expect(onPick).toHaveBeenCalledWith(7)
    expect(screen.getByRole('group')).toHaveAttribute('data-state', 'closing')
    act(() => vi.advanceTimersByTime(300))
    expect(screen.queryByRole('group')).toBeNull()
    vi.useRealTimers()
  })

  it('바깥을 누르거나 Esc 면 닫힌다', () => {
    render(<SeatPicker label="테스트 번호" seat={1} seats={SEATS} onPick={() => {}} />)
    const pill = screen.getByRole('button', { name: '테스트 번호 1번' })
    fireEvent.click(pill)
    fireEvent.pointerDown(document.body)
    expect(screen.getByRole('group')).toHaveAttribute('data-state', 'closing')
  })
})
