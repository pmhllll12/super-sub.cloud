import type { Det } from '@/lib/personTrack'
import { extractMotion } from './extract'

// 진짜 검출기(tfjs)를 올리지 않는다 — 대역만 쓴다.
vi.mock('@/lib/personDetector', () => ({
  detectPeople: () => Promise.resolve([]),
  refinePose: () => Promise.resolve(null),
}))

/** jsdom 의 `<video>` 는 재생 · 탐색을 못 한다 — 필요한 만큼만 흉내 낸다. */
class FakeVideo extends EventTarget {
  videoWidth = 1280
  videoHeight = 720
  duration = 1
  muted = false
  playsInline = false
  preload = ''
  private t = 0
  private _src = ''
  get src() {
    return this._src
  }
  set src(v: string) {
    this._src = v
  }
  get currentTime() {
    return this.t
  }
  set currentTime(v: number) {
    this.t = v
    queueMicrotask(() => this.dispatchEvent(new Event('seeked')))
  }
  load() {
    if (this._src) queueMicrotask(() => this.dispatchEvent(new Event('loadeddata')))
  }
  removeAttribute() {
    this._src = ''
  }
}

const kp = Array.from({ length: 17 }, () => ({ x: 0.5, y: 0.5, score: 0.9 }))
const det = (w: number, x = 0.1): Det => ({ box: { x, y: 0.1, w, h: 0.5 }, score: 0.9, keypoints: kp })
const flat = () => ({ data: new Uint8ClampedArray(256 * 144 * 4).fill(120), width: 256, height: 144 })

describe('관절 뽑기', () => {
  it('fps 대로 영상 전체를 훑어 프레임 수를 채운다', async () => {
    const seen: number[] = []
    const video = new FakeVideo()
    const m = await extractMotion('/clip.mp4', {
      pick: 'largest',
      fps: 10,
      createVideo: () => video as unknown as HTMLVideoElement,
      deps: {
        detect: async (v) => {
          seen.push(v.currentTime)
          return [det(0.2)]
        },
        refine: async () => null,
      },
    })
    expect(m.frames).toHaveLength(11) // 0.0 ~ 1.0 초
    expect(seen[1]).toBeCloseTo(0.1, 5)
    expect(m.fps).toBe(10)
    expect(m.aspect).toBeCloseTo(16 / 9, 5)
    expect(m.measuredBy).toBe('browser')
  })

  it('선수 영상은 가장 큰 사람의 관절을 쓰고, 2단계가 되면 그 값을 쓴다', async () => {
    const fine = kp.map((p) => ({ ...p, x: 0.42 }))
    const m = await extractMotion('/clip.mp4', {
      pick: 'largest',
      fps: 2,
      createVideo: () => new FakeVideo() as unknown as HTMLVideoElement,
      deps: {
        detect: async () => [det(0.1), det(0.3, 0.5)],
        refine: async (_v, box) => (box.w === 0.3 ? fine : null),
      },
    })
    expect(m.frames[0]?.[0].x).toBe(0.42)
  })

  it('아무도 못 잡은 프레임은 null 로 자리를 지킨다', async () => {
    const m = await extractMotion('/clip.mp4', {
      pick: 'largest',
      fps: 2,
      createVideo: () => new FakeVideo() as unknown as HTMLVideoElement,
      deps: { detect: async () => [], refine: async () => null },
    })
    expect(m.frames).toEqual([null, null, null])
  })

  it('진행률은 0 초과 1 이하로 늘어나 1 로 끝난다', async () => {
    const ratios: number[] = []
    await extractMotion('/clip.mp4', {
      pick: 'largest',
      fps: 4,
      onProgress: (r) => ratios.push(r),
      createVideo: () => new FakeVideo() as unknown as HTMLVideoElement,
      deps: { detect: async () => [det(0.2)], refine: async () => null },
    })
    expect(ratios.at(-1)).toBe(1)
    expect([...ratios].sort((a, b) => a - b)).toEqual(ratios)
  })

  it('내 영상은 묶은 자리에서 앞뒤로 따라가 전체를 채운다', async () => {
    const m = await extractMotion('blob:me', {
      pick: { box: { x: 0.1, y: 0.1, w: 0.2, h: 0.5 }, atMs: 500 },
      fps: 4,
      createVideo: () => new FakeVideo() as unknown as HTMLVideoElement,
      deps: { detect: async () => [det(0.2)], refine: async () => null, grab: flat },
    })
    expect(m.frames).toHaveLength(5)
    expect(m.frames.every((f) => f !== null)).toBe(true)
  })

  // 🔴 선수를 바꾸거나 닫으면 돌던 뽑기가 새 화면에 끼어들면 안 된다.
  it('중단 신호가 오면 AbortError 로 멈춘다', async () => {
    const ctrl = new AbortController()
    let calls = 0
    const run = extractMotion('/clip.mp4', {
      pick: 'largest',
      fps: 10,
      signal: ctrl.signal,
      createVideo: () => new FakeVideo() as unknown as HTMLVideoElement,
      deps: {
        detect: async () => {
          calls += 1
          if (calls === 2) ctrl.abort()
          return [det(0.2)]
        },
        refine: async () => null,
      },
    })
    await expect(run).rejects.toMatchObject({ name: 'AbortError' })
    expect(calls).toBe(2)
  })
})
