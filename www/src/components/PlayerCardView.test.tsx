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

/**
 * **카드 그림은 따라 나오지 않는다** (사용자 지적, 2026-09-18).
 *
 * 「카드가 있는 모든 곳에서 저 사람 이미지가 계속 클릭해서 옮기면 따라
 * 나오는데, 아예 이미지가 따라 나오지 않게 만들고」
 *
 * 🔴 **`user-select: none` 으로는 못 막는다.** `.ss-squad-seat` 에 그것과
 * `touch-action: none` 이 걸려 있고 주석도 「브라우저가 그림·글자를 대신
 * 끌어가지 않게 한다」인데, `user-select` 가 막는 것은 **글자 선택**이다.
 * `<img>` 의 네이티브 드래그(반투명 유령 그림)는 따로 꺼야 한다.
 *
 * 🔴 **여기 하나만 고치면 전부 덮인다** — 스쿼드 판·헤더·프로필·공개 카드·
 * 대기 팝업·리뷰가 전부 이 컴포넌트를 통해 사진을 그린다.
 */
describe('선수 카드 — 그림이 끌려 나오지 않는다', () => {
  it('누끼 인물은 끌 수 없다', () => {
    const { container } = render(<PlayerCardView card={card} />)
    const img = container.querySelector('.ss-pcard-figure img') as HTMLImageElement
    expect(img).not.toBeNull()
    expect(img.draggable).toBe(false)
  })

  /* 사진을 통째로 까는 모드도 같은 `<img>` 다 — 갈래가 둘이라 둘 다 본다. */
  it('사진을 통째로 깐 모드에서도 끌 수 없다', () => {
    const { container } = render(
      <PlayerCardView
        card={card}
        look={{ mode: 'full', photo: 'data:image/png;base64,iVBORw0KGgo=' }}
      />,
    )
    /* 🔴 **정말 `full` 갈래를 밟았는지 먼저 본다.** prop 이름을 틀리면
       (`style` 로 준 적이 있다) 조용히 누끼 갈래가 그려지고, 시험은
       같은 선택자를 찾아 **통과해 버린다.** */
    expect(container.querySelector('.ss-pcard')).toHaveAttribute('data-photo', 'full')
    const img = container.querySelector('.ss-pcard-figure img') as HTMLImageElement
    expect(img).not.toBeNull()
    expect(img.draggable).toBe(false)
  })
})
