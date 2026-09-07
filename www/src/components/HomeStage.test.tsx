import { render, act } from '@testing-library/react'
import HomeStage from './HomeStage'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh: vi.fn() }),
  // 등장 애니메이션이 "이번에 인트로가 도는가" 를 경로로 판단한다
  // (`useIntroDone`) — 이미 본 것으로 쳐 바로 들어오게 둔다.
  usePathname: () => '/',
}))

/**
 * 🔴 **휠 한 번(튕김)은 기록에 한 걸음만 남겨야 한다.**
 *
 * 마우스 휠은 한 번 튕기면 `wheel` 이벤트가 **여러 개** 온다. 그 전부가 각자
 * 기록을 건드리면 내려갈 때 `pushState` 가 몇 번씩 쌓이고, 올라올 때
 * `history.back()` 이 몇 번씩 나가 **화면 밖으로 걸어 나간다** — 도메인에 올린
 * 뒤 데스크톱 사용자들이 겪은 것이 이것이다(영상 모음에서 휠을 올렸더니
 * `/market` 으로 가거나 사이트 밖으로 나갔다. 2026-09-06 헤드리스로 재현).
 *
 * 한 태스크 안에서 여러 개를 흘리는 것이 그 상황이다 — 실제로도 입력 큐에
 * 쌓인 휠들이 `popstate` 보다 먼저 처리되면서 전부 옛 상태를 본다.
 */
function wheelBurst(deltaY: number, n = 5) {
  act(() => {
    for (let k = 0; k < n; k++) {
      window.dispatchEvent(new WheelEvent('wheel', { deltaY, bubbles: true, cancelable: true }))
    }
  })
}

function setup() {
  return render(
    <HomeStage
      user={{ nickname: '홍길동' }}
      destinations={[]}
      featured={[]}
    />,
  )
}

describe('홈 — 굴림으로 영상 모음을 오간다', () => {
  let push: ReturnType<typeof vi.spyOn>
  let back: ReturnType<typeof vi.spyOn>

  // jsdom 의 `play()` 는 약속을 안 돌려줘서 `.catch` 에서 죽는다(영상 모음이
  // 내려오면 바로 튼다). 이 시험이 보는 것은 기록이지 재생이 아니다.
  beforeAll(() => {
    vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue(undefined)
    vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => {})
  })

  beforeEach(() => {
    window.history.replaceState(null, '')
    push = vi.spyOn(window.history, 'pushState')
    back = vi.spyOn(window.history, 'back').mockImplementation(() => {})
  })

  afterEach(() => {
    push.mockRestore()
    back.mockRestore()
  })

  it('휠 한 번을 세게 굴려도 기록은 한 걸음만 쌓인다', () => {
    setup()
    wheelBurst(100)
    expect(push).toHaveBeenCalledTimes(1)
  })

  it('영상 모음에서 휠을 올릴 때 뒤로 가기를 한 번만 부른다', () => {
    setup()
    wheelBurst(100)
    push.mockClear()
    wheelBurst(-100)
    expect(back).toHaveBeenCalledTimes(1)
  })

  it('기록에 우리 걸음이 없으면 뒤로 가기를 부르지 않는다 — 사이트를 벗어난다', () => {
    setup()
    wheelBurst(-100)
    expect(back).not.toHaveBeenCalled()
  })
})
