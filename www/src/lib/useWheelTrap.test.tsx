import { useRef } from 'react'
import { render } from '@testing-library/react'
import { useWheelTrap } from './useWheelTrap'

/**
 * **판 위에서 굴리면 페이지가 안 움직인다** (사용자 지적, 2026-09-18).
 *
 * 🔴 두 곳에서 같은 일이 났다 — 「비슷한 팀」 판, 그리고 영상 쪽 「다음 영상」
 * 목록. 되풀이하지 않게 여기로 뺐다.
 */
function Panel({ scrollable }: { scrollable: boolean }) {
  const panel = useRef<HTMLDivElement>(null)
  const list = useRef<HTMLUListElement>(null)
  useWheelTrap(panel, list)
  return (
    <div ref={panel} data-testid="panel">
      <p data-testid="head">머리줄</p>
      <ul ref={list} data-testid="list">
        <li>한 줄</li>
      </ul>
      <p data-testid="foot">아래 안내</p>
      {/* 구를 수 있는지 시험이 정한다 — jsdom 은 크기를 안 잰다. */}
      <span hidden>{String(scrollable)}</span>
    </div>
  )
}

function sizeList(el: HTMLElement, scrollable: boolean) {
  Object.defineProperty(el, 'scrollHeight', { value: scrollable ? 900 : 100, configurable: true })
  Object.defineProperty(el, 'clientHeight', { value: 100, configurable: true })
}

const wheel = () => new WheelEvent('wheel', { deltaY: 120, bubbles: true, cancelable: true })

describe('판이 휠을 삼킨다', () => {
  it('목록 위에서 굴리면 목록이 구르고 페이지는 막힌다', () => {
    const { getByTestId } = render(<Panel scrollable />)
    const list = getByTestId('list')
    sizeList(list, true)
    list.scrollTop = 0

    const e = wheel()
    list.dispatchEvent(e)

    expect(list.scrollTop).toBe(120)
    expect(e.defaultPrevented).toBe(true)
  })

  /* 🔴 **여기가 새던 자리다** — 머리줄·아래 안내는 스크롤 상자가 아니라
     `overscroll-behavior` 가 안 걸린다. */
  it('머리줄·아래 안내에서 굴려도 목록이 구르고 페이지는 막힌다', () => {
    const { getByTestId } = render(<Panel scrollable />)
    const list = getByTestId('list')
    sizeList(list, true)
    list.scrollTop = 0

    const e = wheel()
    getByTestId('foot').dispatchEvent(e)

    expect(list.scrollTop).toBe(120)
    expect(e.defaultPrevented).toBe(true)
  })

  /* 🔴 **구를 것이 없어도 막는다** — 영상 쪽 「다음 영상」 목록이 그렇다
     (`overflow` 가 아예 없다). 거기서 굴리면 홈 위쪽으로 되돌아갔다. */
  it('구를 것이 없으면 삼키기만 한다', () => {
    const { getByTestId } = render(<Panel scrollable={false} />)
    const list = getByTestId('list')
    sizeList(list, false)
    list.scrollTop = 0

    const e = wheel()
    getByTestId('head').dispatchEvent(e)

    expect(list.scrollTop).toBe(0)
    expect(e.defaultPrevented).toBe(true)
  })

  /* 🔴 붙었는지 화면에서 볼 수 있어야 한다 — 안 붙으면 증상이 고치기 전과
     똑같아서 배포 문제인지 코드 문제인지 못 가른다. */
  it('붙었다는 표식을 남긴다', () => {
    const { getByTestId } = render(<Panel scrollable />)
    expect(getByTestId('panel')).toHaveAttribute('data-wheel-guard', 'on')
  })
})
