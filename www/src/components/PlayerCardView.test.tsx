import { render, screen } from '@testing-library/react'
import PlayerCardView from './PlayerCardView'

const card = {
  public_slug: 'hong-gildong-4f2a',
  og_image_key: 'cards/7b4d.png',
  user: { id: '3f1c', nickname: '홍길동' },
  titles: [
    { code: 'sharp_shooter', label: '슈팅이 매서운', category: '강점', granted_at: '2026-08-20T12:00:00Z' },
    { code: 'weekend_regular', label: '주말 개근', category: '활동', granted_at: '2026-08-01T09:00:00Z' },
  ],
}

describe('선수 카드', () => {
  it('받은 호칭을 보여준다', () => {
    render(<PlayerCardView card={card} />)
    expect(screen.getByText('슈팅이 매서운')).toBeInTheDocument()
    expect(screen.getByText('주말 개근')).toBeInTheDocument()
  })

  // 카드에 이름을 글자로 적지 않는다(인물이 가운데를 차지한다). 그래도
  // 누구 카드인지는 읽어 주는 기계에 남아야 한다.
  it('닉네임을 글자로 적지 않되 카드의 이름으로는 남긴다', () => {
    render(<PlayerCardView card={card} />)
    expect(screen.queryByRole('heading', { name: '홍길동' })).toBeNull()
    expect(screen.getByRole('article', { name: '홍길동' })).toBeInTheDocument()
  })

  it('호칭이 없으면 빈 상태를 보여준다', () => {
    render(<PlayerCardView card={{ ...card, titles: [] }} />)
    expect(screen.getByText(/아직 받은 호칭이 없습니다/)).toBeInTheDocument()
  })

  it('수치를 그리지 않는다 — 점수·등급·별점이 없어야 한다', () => {
    const { container } = render(<PlayerCardView card={card} />)
    expect(container.textContent).not.toMatch(/[0-9]+\s*점/)
    expect(container.textContent).not.toMatch(/등급/)
    expect(container.textContent).not.toMatch(/★|☆/) // 별점
    expect(container.textContent).not.toMatch(/[0-9]+\s*%/) // 백분율
    expect(container.textContent).not.toMatch(/[0-9]+\.[0-9]/) // 소수 점수
    expect(container.querySelector('progress')).toBeNull()
    expect(container.querySelector('meter')).toBeNull()
  })
})
