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
  tagline: null,
  style: null,
}

describe('선수 카드', () => {
  // 카드 얼굴에는 별명 하나뿐이다. 호칭은 화면 밖 목록으로만 남는다 —
  // 카드에 무엇이 담겼는지 읽어 주는 기계가 알 수 있어야 해서다.
  it('받은 호칭을 화면 밖 목록으로 남긴다', () => {
    render(<PlayerCardView card={card} />)
    expect(screen.getByText(/슈팅이 매서운/)).toBeInTheDocument()
    expect(screen.getByText(/주말 개근/)).toBeInTheDocument()
  })

  it('가운데에 별명을 크게 적는다 — 안 정했으면 자리 표시', () => {
    render(<PlayerCardView card={card} />)
    expect(screen.getByText('THREE LUNGS')).toBeInTheDocument()
  })

  // ✅ CCC 18·35 — 사람이 정한 값이 붙박이 문구를 대신한다.
  it('tagline을 정했으면 그것을 적는다', () => {
    render(<PlayerCardView card={{ ...card, tagline: '숨은 왼발' }} />)
    expect(screen.getByText('숨은 왼발')).toBeInTheDocument()
    expect(screen.queryByText('THREE LUNGS')).toBeNull()
  })

  // ✅ CCC 35 — `look` 을 안 넘겨도 `card.style` 이 있으면 꾸며진 대로 그린다
  // (편집기 밖 · 공개 카드 화면이 이 경로를 쓴다).
  it('look 없이도 card.style 을 입는다', () => {
    const styled = {
      ...card,
      style: {
        bg: '#111111',
        logo: '#222222',
        text_color: '#333333',
        text_x: 10,
        text_y: 20,
        brush: 3,
        brush_color: '#444444',
        brush_scale: 2,
        brush_x: 5,
        brush_y: 6,
      },
    }
    const { container } = render(<PlayerCardView card={styled} />)
    const article = container.querySelector('.ss-pcard') as HTMLElement
    expect(article.getAttribute('data-text-free')).toBe('true')
    expect(article.style.getPropertyValue('--ss-pcard-bg')).toBe('#111111')
    expect(article.style.getPropertyValue('--ss-pcard-text-x')).toBe('10%')
  })

  it('style이 없으면 지금까지처럼 자리 흐름대로 그린다', () => {
    const { container } = render(<PlayerCardView card={card} />)
    const article = container.querySelector('.ss-pcard') as HTMLElement
    expect(article.getAttribute('data-text-free')).toBeNull()
  })

  // 카드에 이름을 글자로 적지 않는다(인물이 가운데를 차지한다). 그래도
  // 누구 카드인지는 읽어 주는 기계에 남아야 한다.
  it('닉네임을 글자로 적지 않되 카드의 이름으로는 남긴다', () => {
    render(<PlayerCardView card={card} />)
    expect(screen.queryByRole('heading', { name: '홍길동' })).toBeNull()
    expect(screen.getByRole('article', { name: '홍길동' })).toBeInTheDocument()
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
