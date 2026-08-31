import { render } from '@testing-library/react'
import PlayerCardBrush from './PlayerCardBrush'

const paths = (el: HTMLElement) =>
  [...el.querySelectorAll('path')].map((p) => p.getAttribute('d')).join('|')

describe('카드 붓자국', () => {
  // 🔴 이게 이 컴포넌트의 존재 이유다. Math.random() 을 쓰면 서버가 그린
  // 것과 브라우저가 다시 그린 것이 달라 하이드레이션이 깨진다.
  it('같은 씨앗이면 늘 같은 모양이다', () => {
    const a = render(<PlayerCardBrush seed="hong-gildong-4f2a" />)
    const b = render(<PlayerCardBrush seed="hong-gildong-4f2a" />)
    expect(paths(a.container)).toBe(paths(b.container))
  })

  it('씨앗이 다르면 모양도 다르다 — 사람마다 다른 자국이 나온다', () => {
    const a = render(<PlayerCardBrush seed="hong-gildong-4f2a" />)
    const b = render(<PlayerCardBrush seed="kim-cheolsu-9b1e" />)
    expect(paths(a.container)).not.toBe(paths(b.container))
  })

  // 위쪽 절반은 워드마크와 별명의 자리다 — 자국이 거기까지 올라오면 안 된다.
  it('자국이 카드 위쪽 절반을 침범하지 않는다', () => {
    const { container } = render(<PlayerCardBrush seed="hong-gildong-4f2a" />)
    const HALF = 70 // viewBox 는 100×140

    for (const g of container.querySelectorAll('g')) {
      // 세로만 본다 — 가로 위치는 이 규칙과 무관하다.
      const [, , ty] = /translate\(([-\d.]+) ([-\d.]+)\)/.exec(
        g.getAttribute('transform') ?? '',
      )!
      const [, deg] = /rotate\(([-\d.]+)\)/.exec(g.getAttribute('transform') ?? '')!
      const rad = (Number(deg) * Math.PI) / 180

      for (const path of g.querySelectorAll('path')) {
        for (const [px, py] of (path.getAttribute('d') ?? '')
          .replace(/[MLZ]/g, ' ')
          .trim()
          .split(/\s+/)
          .map((pair) => pair.split(',').map(Number))) {
          const y = Number(ty) + px * Math.sin(rad) + py * Math.cos(rad)
          expect(y).toBeGreaterThan(HALF)
        }
      }
    }
  })
})
