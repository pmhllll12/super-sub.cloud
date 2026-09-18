import { act, fireEvent, render, screen } from '@testing-library/react'
import DemoVideo, { DEMO_VIDEO_SRC, exitOffset } from './DemoVideo'
import { leaveDemoVideo } from '@/lib/demoVideoExit'

let introDone = true
vi.mock('@/lib/useIntroDone', () => ({ useIntroDone: () => introDone }))
let pathname = '/login'
vi.mock('next/navigation', () => ({ usePathname: () => pathname }))

// jsdom 은 재생을 못 한다 — play/pause 가 이벤트만 쏘게 흉내 낸다.
let paused = true
beforeEach(() => {
  introDone = true
  pathname = '/login'
  paused = true
  Object.defineProperty(HTMLMediaElement.prototype, 'paused', { configurable: true, get: () => paused })
  HTMLMediaElement.prototype.play = vi.fn(function (this: HTMLMediaElement) {
    paused = false
    this.dispatchEvent(new Event('play'))
    return Promise.resolve()
  })
  HTMLMediaElement.prototype.pause = vi.fn(function (this: HTMLMediaElement) {
    paused = true
    this.dispatchEvent(new Event('pause'))
  })
})

describe('사용법 영상', () => {
  it('인트로가 끝나기 전에는 안 보이고 재생도 안 한다', () => {
    introDone = false
    const { container } = render(<DemoVideo />)
    expect(container.querySelector('.ss-demo-video')).toHaveAttribute('hidden')
    expect(HTMLMediaElement.prototype.play).not.toHaveBeenCalled()
  })

  it('인트로가 끝나면 바로 재생하고, 끝없이 돈다', () => {
    const { container } = render(<DemoVideo />)
    const video = container.querySelector('video')!
    expect(container.querySelector('.ss-demo-video')).not.toHaveAttribute('hidden')
    expect(video.getAttribute('src')).toBe(DEMO_VIDEO_SRC)
    expect(video.loop).toBe(true)
    // 자동 재생은 소리 없는 영상에만 허락된다
    expect(video.muted).toBe(true)
    expect(HTMLMediaElement.prototype.play).toHaveBeenCalledTimes(1)
  })

  it('눌러야 멈추고, 다시 누르면 이어서 돈다', async () => {
    render(<DemoVideo />)
    await act(async () => {})
    fireEvent.click(screen.getByRole('button', { name: '사용법 영상 멈춤' }))
    expect(HTMLMediaElement.prototype.pause).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: '사용법 영상 재생' }))
    expect(HTMLMediaElement.prototype.play).toHaveBeenCalledTimes(2)
  })

  it('로그인 화면이 내놓은 자리에 맞춰 앉는다', () => {
    const slot = document.createElement('div')
    slot.setAttribute('data-demo-slot', '')
    slot.getBoundingClientRect = () => ({ top: 300, left: 500, width: 280, height: 152 }) as DOMRect
    document.body.appendChild(slot)
    const { container } = render(<DemoVideo />)
    const box = container.querySelector<HTMLElement>('.ss-demo-video')!
    expect(box.dataset.slotted).toBe('true')
    expect(box.style.left).toBe('500px')
    expect(box.style.width).toBe('280px')
    slot.remove()
  })

  it('자리가 없는 화면에서는 구석에 뜬다', () => {
    const { container } = render(<DemoVideo />)
    expect(container.querySelector<HTMLElement>('.ss-demo-video')!.dataset.slotted).toBe('false')
  })
})

describe('되감기 막대', () => {
  it('분:초 로 적는다', async () => {
    const { formatTime } = await import('./DemoVideo')
    expect(formatTime(0)).toBe('0:00')
    expect(formatTime(83.4)).toBe('1:23')
    expect(formatTime(120.07)).toBe('2:00')
    expect(formatTime(NaN)).toBe('0:00')
  })

  it('막대를 누른 자리로 건너뛰고, 멈춤으로 새지 않는다', async () => {
    const { container } = render(<DemoVideo />)
    const video = container.querySelector('video')!
    Object.defineProperty(video, 'duration', { configurable: true, value: 120 })
    fireEvent(video, new Event('loadedmetadata'))
    await act(async () => {})
    const seek = screen.getByRole('slider', { name: '사용법 영상 재생 위치' })
    seek.getBoundingClientRect = () => ({ left: 100, width: 200, top: 0, height: 15 }) as DOMRect
    ;(HTMLMediaElement.prototype.pause as ReturnType<typeof vi.fn>).mockClear()
    fireEvent.pointerDown(seek, { clientX: 150, pointerId: 1 })
    fireEvent.click(seek)
    expect(video.currentTime).toBe(30) // 200px 막대의 1/4 → 120초의 1/4
    expect(HTMLMediaElement.prototype.pause).not.toHaveBeenCalled()
    expect(screen.getByText('0:30 / 2:00')).toBeInTheDocument()
  })

  it('자판 ←→ 로 5초씩 움직인다', async () => {
    const { container } = render(<DemoVideo />)
    const video = container.querySelector('video')!
    Object.defineProperty(video, 'duration', { configurable: true, value: 120 })
    fireEvent(video, new Event('loadedmetadata'))
    await act(async () => {})
    const seek = screen.getByRole('slider')
    fireEvent.keyDown(seek, { key: 'End' })
    expect(video.currentTime).toBe(120)
    fireEvent.keyDown(seek, { key: 'ArrowLeft' })
    expect(video.currentTime).toBe(115)
  })
})

describe('닫기 · 크기 조절', () => {
  it('닫으면 멈추고 「시연 영상 다시보기」만 남는다 — 누르면 다시 뜬다', async () => {
    const { container } = render(<DemoVideo />)
    await act(async () => {})
    fireEvent.click(screen.getByRole('button', { name: '시연영상 닫기' }))
    expect(HTMLMediaElement.prototype.pause).toHaveBeenCalled()
    expect(container.querySelector('.ss-demo-video')).toHaveAttribute('hidden')
    fireEvent.click(screen.getByRole('button', { name: '시연 영상 다시보기' }))
    expect(container.querySelector('.ss-demo-video')).not.toHaveAttribute('hidden')
    expect(screen.queryByRole('button', { name: '시연 영상 다시보기' })).not.toBeInTheDocument()
  })

  function setup() {
    const slot = document.createElement('div')
    slot.setAttribute('data-demo-slot', '')
    slot.getBoundingClientRect = () => ({ top: 300, left: 400, width: 400, height: 200 }) as DOMRect
    document.body.appendChild(slot)
    const utils = render(<DemoVideo />)
    const box = utils.container.querySelector<HTMLElement>('.ss-demo-video')!
    const handle = (c: string) => utils.container.querySelector<HTMLElement>(`[data-corner="${c}"]`)!
    // jsdom 에는 포인터 붙잡기가 없다 — 붙잡은 것으로 친다.
    HTMLElement.prototype.setPointerCapture = () => {}
    HTMLElement.prototype.hasPointerCapture = () => true
    return { box, handle, cleanup: () => slot.remove() }
  }

  it('오른쪽 아래 모서리를 끌면 왼쪽 위를 붙박고 커진다', () => {
    const { box, handle, cleanup } = setup()
    fireEvent.pointerDown(handle('br'), { clientX: 800, clientY: 500, pointerId: 1 })
    fireEvent.pointerMove(handle('br'), { clientX: 1000, clientY: 500, pointerId: 1 })
    expect(box.style.left).toBe('400px')
    expect(box.style.top).toBe('300px')
    expect(box.style.width).toBe('600px')
    expect(box.style.height).toBe('300px') // 비율 유지
    cleanup()
  })

  it('작게는 기본의 딱 절반까지만', () => {
    const { box, handle, cleanup } = setup()
    fireEvent.pointerDown(handle('tl'), { clientX: 400, clientY: 300, pointerId: 1 })
    fireEvent.pointerMove(handle('tl'), { clientX: 790, clientY: 495, pointerId: 1 })
    expect(box.style.width).toBe('200px')
    expect(box.style.height).toBe('100px')
    // 맞은편(오른쪽 아래)이 그대로다
    expect(box.style.left).toBe('600px')
    expect(box.style.top).toBe('400px')
    cleanup()
  })
})

describe('끌어 옮기기', () => {
  function setup() {
    const slot = document.createElement('div')
    slot.setAttribute('data-demo-slot', '')
    slot.getBoundingClientRect = () => ({ top: 300, left: 400, width: 400, height: 200 }) as DOMRect
    document.body.appendChild(slot)
    HTMLElement.prototype.setPointerCapture = () => {}
    HTMLElement.prototype.hasPointerCapture = () => true
    const utils = render(<DemoVideo />)
    const box = utils.container.querySelector<HTMLElement>('.ss-demo-video')!
    return { box, cleanup: () => slot.remove() }
  }

  it('영상을 끌면 옮겨지고, 끈 것은 멈춤으로 치지 않는다', async () => {
    const { box, cleanup } = setup()
    await act(async () => {})
    const video = screen.getByRole('button', { name: '사용법 영상 멈춤' })
    ;(HTMLMediaElement.prototype.pause as ReturnType<typeof vi.fn>).mockClear()
    fireEvent.pointerDown(video, { clientX: 500, clientY: 400, button: 0, pointerId: 1 })
    fireEvent.pointerMove(video, { clientX: 400, clientY: 350, pointerId: 1 })
    fireEvent.pointerUp(video, { pointerId: 1 })
    fireEvent.click(video)
    expect(box.style.left).toBe('300px')
    expect(box.style.top).toBe('250px')
    expect(HTMLMediaElement.prototype.pause).not.toHaveBeenCalled()
    cleanup()
  })

  it('조금 흔들린 것(4px 미만)은 그냥 누른 것 — 멈춘다', async () => {
    const { box, cleanup } = setup()
    await act(async () => {})
    const video = screen.getByRole('button', { name: '사용법 영상 멈춤' })
    fireEvent.pointerDown(video, { clientX: 500, clientY: 400, button: 0, pointerId: 1 })
    fireEvent.pointerMove(video, { clientX: 502, clientY: 401, pointerId: 1 })
    fireEvent.pointerUp(video, { pointerId: 1 })
    fireEvent.click(video)
    expect(box.style.left).toBe('400px')
    expect(HTMLMediaElement.prototype.pause).toHaveBeenCalled()
    cleanup()
  })

  it('창 밖으로 끌어도 창 안에 남는다(닫기 단추 자리까지)', async () => {
    const { box, cleanup } = setup()
    await act(async () => {})
    const video = screen.getByRole('button', { name: '사용법 영상 멈춤' })
    fireEvent.pointerDown(video, { clientX: 500, clientY: 400, button: 0, pointerId: 1 })
    fireEvent.pointerMove(video, { clientX: -3000, clientY: -3000, pointerId: 1 })
    expect(box.style.left).toBe('8px')
    expect(box.style.top).toBe('42px') // 8 + 닫기 단추 34
    fireEvent.pointerMove(video, { clientX: 9000, clientY: 9000, pointerId: 1 })
    expect(box.style.left).toBe(`${window.innerWidth - 8 - 400}px`)
    expect(box.style.top).toBe(`${window.innerHeight - 8 - 200}px`)
    cleanup()
  })
})

describe('가운데 아이콘', () => {
  it('멈추면 ▶ 하나만 뜨고, 다시 틀면 그 ▶ 가 사라지는 연출 하나만 — ❚❚ 는 없다', async () => {
    const { container } = render(<DemoVideo />)
    await act(async () => {})
    const btn = container.querySelector<HTMLElement>('.ss-demo-video-toggle')!
    expect(btn.querySelectorAll('.ss-demo-video-icon')).toHaveLength(0) // 재생 중엔 없다
    fireEvent.click(btn) // 멈춤
    expect(btn.querySelectorAll('.ss-demo-video-icon')).toHaveLength(1)
    expect(btn.querySelector('.ss-demo-video-flash')).toBeNull()
    fireEvent.click(btn) // 재생
    expect(btn.querySelectorAll('.ss-demo-video-icon')).toHaveLength(1)
    expect(btn.querySelector('.ss-demo-video-flash')).not.toBeNull()
  })
})

describe('「시연영상을 참고해 주세요」', () => {
  // 🔴 jsdom 에는 `AnimationEvent` 가 없어 React 가 `animationend` 대신 접두사 붙은
  // 이름(webkitAnimationEnd 등)을 듣는다 — `fireEvent.animationEnd` 는 안 닿는다.
  // 셋 다 쏘면 React 가 듣는 하나만 받는다.
  function landed(el: HTMLElement) {
    for (const type of ['animationend', 'webkitAnimationEnd', 'mozAnimationEnd', 'MSAnimationEnd', 'oanimationend'])
      act(() => {
        el.dispatchEvent(new Event(type, { bubbles: true }))
      })
  }

  function landOnLogin() {
    const slot = document.createElement('div')
    slot.setAttribute('data-demo-slot', '')
    slot.getBoundingClientRect = () => ({ top: 300, left: 400, width: 400, height: 200 }) as DOMRect
    document.body.appendChild(slot)
    const utils = render(<DemoVideo />)
    const box = utils.container.querySelector<HTMLElement>('.ss-demo-video')!
    landed(box) // 다 내려왔다
    return { ...utils, cleanup: () => slot.remove() }
  }

  it('로그인 화면에서 다 내려오면 어둡게 하고 영상 바로 밑에 두 줄 띄운다', () => {
    const { container, cleanup } = landOnLogin()
    expect(container.querySelector('.ss-demo-spot')).not.toBeNull()
    const note = screen.getByRole('status')
    expect(note).toHaveTextContent('시연영상을 참고해 주세요.')
    expect(note).toHaveTextContent('모서리를 끌어 크기를, 영상을 끌어 위치를 바꿀 수 있습니다.')
    expect(note.style.top).toBe('514px') // 300 + 200 + 14
    expect(note.style.left).toBe('600px') // 가운데
    cleanup()
  })

  it('어디든 한 번 누르면 둘이 함께 걷힌다(문장이 다 나온 뒤)', () => {
    vi.useFakeTimers()
    const { container, cleanup } = landOnLogin()
    act(() => vi.advanceTimersByTime(600)) // 문장이 다 나와 잠금이 풀렸다
    fireEvent.pointerDown(document.body)
    expect(container.querySelector('.ss-demo-spot')).toHaveAttribute('data-state', 'out')
    expect(screen.getByRole('status')).toHaveAttribute('data-state', 'out')
    act(() => vi.advanceTimersByTime(700))
    expect(container.querySelector('.ss-demo-spot')).toBeNull()
    expect(screen.queryByText('시연영상을 참고해 주세요.')).toBeNull()
    cleanup()
    vi.useRealTimers()
  })

  it('아무도 안 누르면 5초 뒤 걷힌다', () => {
    vi.useFakeTimers()
    const { container, cleanup } = landOnLogin()
    act(() => vi.advanceTimersByTime(4900))
    expect(container.querySelector('.ss-demo-spot')).toHaveAttribute('data-state', 'on')
    act(() => vi.advanceTimersByTime(200))
    expect(container.querySelector('.ss-demo-spot')).toHaveAttribute('data-state', 'out')
    cleanup()
    vi.useRealTimers()
  })

  it('로그인 화면이 아니면 띄우지 않는다', () => {
    const { container } = render(<DemoVideo />)
    landed(container.querySelector<HTMLElement>('.ss-demo-video')!)
    expect(container.querySelector('.ss-demo-spot')).toBeNull()
  })
})

describe('로그인 화면 잠금 — 영상·문장이 다 나오기 전엔 못 누른다', () => {
  function onLogin() {
    const slot = document.createElement('div')
    slot.setAttribute('data-demo-slot', '')
    slot.getBoundingClientRect = () => ({ top: 300, left: 400, width: 400, height: 200 }) as DOMRect
    document.body.appendChild(slot)
    const utils = render(<DemoVideo />)
    const box = utils.container.querySelector<HTMLElement>('.ss-demo-video')!
    const land = () => {
      for (const type of ['animationend', 'webkitAnimationEnd', 'mozAnimationEnd', 'MSAnimationEnd', 'oanimationend'])
        act(() => {
          box.dispatchEvent(new Event(type, { bubbles: true }))
        })
    }
    return { ...utils, land, cleanup: () => slot.remove() }
  }

  it('내려오는 동안·문장이 나오는 동안 잠겨 있다가, 문장이 다 나오면 풀린다', () => {
    vi.useFakeTimers()
    const { land, cleanup } = onLogin()
    expect(screen.getByTestId('demo-lock')).toBeInTheDocument()
    land()
    act(() => vi.advanceTimersByTime(500))
    expect(screen.getByTestId('demo-lock')).toBeInTheDocument()
    // 잠긴 동안 누른 것은 안내를 걷지도 않는다
    fireEvent.pointerDown(document.body)
    expect(screen.getByRole('status')).toHaveAttribute('data-state', 'on')
    act(() => vi.advanceTimersByTime(100))
    expect(screen.queryByTestId('demo-lock')).toBeNull()
    cleanup()
    vi.useRealTimers()
  })

  it('잠긴 동안 Enter 와 폼 제출을 막는다 — 영상 쪽 자판은 그대로', () => {
    const { container, cleanup } = onLogin()
    const enter = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true })
    document.body.dispatchEvent(enter)
    expect(enter.defaultPrevented).toBe(true)
    const submit = new Event('submit', { bubbles: true, cancelable: true })
    document.body.dispatchEvent(submit)
    expect(submit.defaultPrevented).toBe(true)
    const inVideo = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true })
    container.querySelector('.ss-demo-video-toggle')!.dispatchEvent(inVideo)
    expect(inVideo.defaultPrevented).toBe(false)
    cleanup()
  })

  it('도중에 영상을 닫으면 곧바로 풀린다(내려오기가 끊겨 끝 신호가 안 온다)', async () => {
    const { cleanup } = onLogin()
    await act(async () => {})
    fireEvent.click(screen.getByRole('button', { name: '시연영상 닫기' }))
    expect(screen.queryByTestId('demo-lock')).toBeNull()
    cleanup()
  })

  it('무슨 일이 있어도 12초 뒤엔 풀린다', () => {
    vi.useFakeTimers()
    const { cleanup } = onLogin()
    act(() => vi.advanceTimersByTime(12000))
    expect(screen.queryByTestId('demo-lock')).toBeNull()
    cleanup()
    vi.useRealTimers()
  })

  it('로그인 화면이 아니면 잠그지 않는다', () => {
    render(<DemoVideo />)
    expect(screen.queryByTestId('demo-lock')).toBeNull()
  })
})

describe('로그인 → 홈: 가장 가까운 가장자리로 빠졌다가 같은 자리로', () => {
  it('가장 가까운 변을 고른다', () => {
    // 1000×800 창
    expect(exitOffset({ left: 20, top: 300, width: 200, height: 100 }, 1000, 800)).toEqual({ x: -244, y: 0 })
    expect(exitOffset({ left: 760, top: 300, width: 200, height: 100 }, 1000, 800)).toEqual({ x: 264, y: 0 })
    expect(exitOffset({ left: 400, top: 10, width: 200, height: 100 }, 1000, 800)).toEqual({ x: 0, y: -134 })
    expect(exitOffset({ left: 400, top: 680, width: 200, height: 100 }, 1000, 800)).toEqual({ x: 0, y: 144 })
  })

  it('빠르게 빠진 뒤에 로그인이 이어지고, 홈에서 같은 자리·크기로 들어온다', async () => {
    vi.useFakeTimers()
    const slot = document.createElement('div')
    slot.setAttribute('data-demo-slot', '')
    slot.getBoundingClientRect = () => ({ top: 300, left: 400, width: 400, height: 200 }) as DOMRect
    document.body.appendChild(slot)
    const { container, rerender } = render(<DemoVideo />)
    const box = container.querySelector<HTMLElement>('.ss-demo-video')!
    const before = { left: box.style.left, top: box.style.top, width: box.style.width }

    let resolved = false
    // 신호는 React 밖(창 이벤트)에서 온다 — act 안에서 쏴야 상태가 반영된다.
    act(() => {
      void leaveDemoVideo().then(() => (resolved = true))
    })
    expect(box.dataset.travel).toBe('leaving')
    expect(box.style.getPropertyValue('--ss-demo-off-x')).not.toBe('0px')
    await act(async () => vi.advanceTimersByTime(260))
    expect(resolved).toBe(true)
    expect(box.dataset.travel).toBe('away')

    // 홈으로 — 로그인 자리가 없어지고 경로가 바뀐다
    slot.remove()
    pathname = '/'
    rerender(<DemoVideo />)
    act(() => vi.advanceTimersByTime(40)) // 다음 프레임에 새 기준 상자를 잰다
    expect(box.dataset.travel).toBe('entering')
    expect({ left: box.style.left, top: box.style.top, width: box.style.width }).toEqual(before)
    act(() => vi.advanceTimersByTime(600))
    expect(box.dataset.travel).toBe('none')
    vi.useRealTimers()
  })

  it('닫아 둔 채면 「다시보기」 단추가 빠졌다 들어온다', async () => {
    vi.useFakeTimers()
    render(<DemoVideo />)
    act(() => {})
    fireEvent.click(screen.getByRole('button', { name: '시연영상 닫기' }))
    const reopen = screen.getByRole('button', { name: '시연 영상 다시보기' })
    act(() => {
      void leaveDemoVideo()
    })
    expect(reopen.dataset.travel).toBe('leaving')
    await act(async () => vi.advanceTimersByTime(260))
    expect(reopen.dataset.travel).toBe('away')
    vi.useRealTimers()
  })

  it('영상이 아직 안 나왔으면(인트로 중) 기다리지 않고 곧바로 풀린다', async () => {
    introDone = false
    render(<DemoVideo />)
    let resolved = false
    void leaveDemoVideo().then(() => (resolved = true))
    await act(async () => {})
    expect(resolved).toBe(true)
  })
})
