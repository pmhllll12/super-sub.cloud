import { act, fireEvent, render, screen } from '@testing-library/react'
import DemoVideo, { DEMO_VIDEO_SRC } from './DemoVideo'

let introDone = true
vi.mock('@/lib/useIntroDone', () => ({ useIntroDone: () => introDone }))
vi.mock('next/navigation', () => ({ usePathname: () => '/login' }))

// jsdom 은 재생을 못 한다 — play/pause 가 이벤트만 쏘게 흉내 낸다.
let paused = true
beforeEach(() => {
  introDone = true
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
