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
