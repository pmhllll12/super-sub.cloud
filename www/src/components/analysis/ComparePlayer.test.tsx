import { render, waitFor } from '@testing-library/react'
import ComparePlayer from './ComparePlayer'

/**
 * 🔴 검출기는 대역으로 세운다 — `AnalysisStage.test.tsx` 와 같은 이유
 * (jsdom 에는 진짜 검출 모델을 올릴 수 없다).
 */
const detectPeople = vi.hoisted(() => vi.fn())
const refinePose = vi.hoisted(() => vi.fn())

vi.mock('@/lib/personDetector', () => ({
  detectPeople,
  refinePose,
}))

const KEYPOINTS = Array.from({ length: 17 }, (_, i) => ({
  x: 0.4 + (i % 3) * 0.02,
  y: 0.25 + i * 0.02,
  score: 0.8,
}))

/** `AnalysisStage.test.tsx` 의 `loadVideo` 와 같다 — jsdom `<video>` 는 `readyState` ·
 * `videoWidth` 가 0 이라, 세우지 않으면 검출 루프가 영영 되돌아간다. */
function loadVideo() {
  for (const el of document.querySelectorAll('video')) {
    Object.defineProperty(el, 'readyState', { value: 4, configurable: true })
    Object.defineProperty(el, 'videoWidth', { value: 640, configurable: true })
    Object.defineProperty(el, 'videoHeight', { value: 360, configurable: true })
  }
}

beforeEach(() => {
  detectPeople.mockReset()
  refinePose.mockReset()
  refinePose.mockResolvedValue(null)
  detectPeople.mockResolvedValue([
    { box: { x: 0.3, y: 0.2, w: 0.25, h: 0.5 }, score: 0.9, keypoints: KEYPOINTS },
  ])
})

/* 🔴 **멈춰 있어도 seek 하면 다시 잰다**(리뷰 지적, 2026-09-15 — 카드를 눌러 세
   순간으로 옮긴 뒤 하늘색 뼈대가 seek 전 자리에 남는다는 사용자 스크린샷으로
   확인). jsdom `<video>` 는 `paused` 가 기본 `true`(대역 play/pause 가 내부 상태를
   안 바꾼다) 라, "멈춰 있으면 그림이 안 바뀐다" 는 가정만으로는 실제 seek 를
   놓친다 — `currentTime` 이 달라졌는데도 다시 재지 않으면 그림이 그 자리에 멎는다. */
describe('ComparePlayer', () => {
  it('멈춘 채로는 다시 재지 않다가, currentTime 이 바뀌면 다시 잰다', async () => {
    render(<ComparePlayer src="blob:test" label="선수 영상" closing={false} />)
    loadVideo()
    const video = document.querySelector('video') as HTMLVideoElement
    expect(video.paused).toBe(true)

    await waitFor(() => expect(detectPeople).toHaveBeenCalled(), { timeout: 1000 })
    const callsAfterFirst = detectPeople.mock.calls.length

    // 같은 시각(0)으로 몇 바퀴 더 돈다 — 그림이 안 바뀌었으니 다시 잴 이유가 없다.
    await new Promise((r) => setTimeout(r, 300))
    expect(detectPeople.mock.calls.length).toBe(callsAfterFirst)

    // 세 순간 카드를 누른 것과 같다 — 멈춘 채로 다른 시각으로 옮긴다.
    video.currentTime = 3

    await waitFor(() => expect(detectPeople.mock.calls.length).toBeGreaterThan(callsAfterFirst), {
      timeout: 1000,
    })
  })
})
