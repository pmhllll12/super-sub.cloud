import { render } from '@testing-library/react'
import { useFitToViewport } from './useFitToViewport'

/**
 * **판이 화면 아래로 안 넘치게 재는 것** (2026-09-17).
 *
 * jsdom 은 배치를 안 그려서 실제 픽셀은 못 잰다 — 그래서 **부모 상자의 자리와
 * 키를 흉내 내** 셈이 맞는지만 본다. 진짜 값은 헤드리스 크롬으로 쟀고 그 수치는
 * `globals.test.ts` 의 「홈의 두 판에 화면 높이 상한이 걸려 있다」에 적어 뒀다.
 */
describe('useFitToViewport', () => {
  function Panel() {
    const ref = useFitToViewport<HTMLDivElement>()
    return (
      <div data-testid="box">
        <div ref={ref} data-testid="panel" />
      </div>
    )
  }

  /** 부모 상자가 `top` 에서 시작해 `height` 만큼 서 있다고 꾸민다. */
  function stubBox(top: number, height: number, innerHeight: number) {
    vi.spyOn(window, 'innerHeight', 'get').mockReturnValue(innerHeight)
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
      top,
      bottom: top + height,
      height,
      left: 0,
      right: 0,
      width: 0,
      x: 0,
      y: top,
      toJSON: () => ({}),
    } as DOMRect)
    vi.spyOn(HTMLElement.prototype, 'offsetHeight', 'get').mockReturnValue(height)
  }

  afterEach(() => vi.restoreAllMocks())

  /**
   * 🔴 **낮은 창** — 판(702)이 125 에서 시작하면 827 이라 720 짜리 창을 107
   * 넘는다. 화면 아래 16px 을 남기고 멈춰야 한다: 720 − 125 − 16 = **579**.
   */
  it('창을 넘치면 남은 높이로 상한을 건다', () => {
    stubBox(125, 702, 720)
    const { getByTestId } = render(<Panel />)
    expect(getByTestId('panel').style.getPropertyValue('--ss-fit-h')).toBe('579px')
  })

  /**
   * 🔴 **넉넉한 창에서는 아무것도 안 건다.** 들어가는데 값을 박으면 판이
   * 공연히 짧아진다 — 큰 모니터에서 지금까지와 똑같이 서야 한다.
   */
  it('다 들어가면 none 이라 지금까지와 똑같이 선다', () => {
    stubBox(248, 702, 1080)
    const { getByTestId } = render(<Panel />)
    expect(getByTestId('panel').style.getPropertyValue('--ss-fit-h')).toBe('none')
  })

  /* 🔴 **아주 낮은 창에서도 읽을 수 있을 만큼은 남긴다** — 더 줄면 판이
     제목과 닫기 단추만 남는다. */
  it('아무리 낮아도 260px 밑으로는 안 줄인다', () => {
    stubBox(400, 702, 500)
    const { getByTestId } = render(<Panel />)
    expect(getByTestId('panel').style.getPropertyValue('--ss-fit-h')).toBe('260px')
  })
})
