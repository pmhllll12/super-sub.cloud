/**
 * **브라우저가 관절을 뽑는다** — 데모용(설계 §2). 최종에는 에이전트 결과를 받는다
 * (`source.ts` 만 바꾼다, 미결 paik 29 · 30).
 *
 * 🔴 **보이지 않는 `<video>` 를 따로 만든다** — 화면의 영상은 계속 재생되어야 한다.
 * 🔴 검출기는 화면 쪽과 같은 것(`personDetector`)이다. 캔버스를 읽는 부분이 동기라
 * 두 영상이 번갈아 불러도 섞이지 않는다.
 */
import type { Box } from '@/lib/box'
import { detectPeople, refinePose } from '@/lib/personDetector'
import { createPersonTracker, snapToDetection, type Det, type Frame } from '@/lib/personTrack'
import type { Point } from '@/lib/pose'
import type { Motion } from './types'

/**
 * 초당 몇 장을 볼까. 검출 한 장이 GPU 에서 수십 ms 라 13초 영상이 몇 초에 끝난다.
 *
 * 🔴 **15 → 10 으로 내렸다**(2026-09-19, 사용자 지적 — "결과가 너무 늦게 나와요").
 * 이 수치는 **13초 영상 기준**이었는데, 업로드 상한(60초)에 가까운 긴 영상은
 * 프레임 수가 그만큼 늘어(60초 × 15fps ≈ 900장, player·user 각각) 순서대로
 * `seek` 하는 비용이 쌓여 눈에 띄게 느려진다. 10fps 로도 무릎 각속도 피크(임팩트)를
 * 잡는 데는 충분하다 — `detectMoments` 의 여유 폭(`impact - first < 2` 등)이
 * 프레임 수가 아니라 **fps 상대**라 값을 낮춰도 판정 기준 자체는 그대로 따라온다.
 */
export const EXTRACT_FPS = 10

/** 추적기용 축소본 가로 픽셀 — 화면 쪽 `TRACK_W` 와 같은 값. */
const TRACK_W = 256

/**
 * 누구를 뽑나. `largest` 는 선수 영상 — 에이전트 `_largest_person_box` 와 같은 규칙.
 * 박스는 내 영상 — 사람이 묶은 자리(`subject`)에서 시작해 앞뒤로 따라간다.
 */
export type Pick = 'largest' | { box: Box; atMs: number }

export type ExtractDeps = {
  detect: (v: HTMLVideoElement) => Promise<Det[]>
  refine: (v: HTMLVideoElement, box: Box) => Promise<Point[] | null>
  grab: (v: HTMLVideoElement) => Frame
}

export type ExtractOptions = {
  pick: Pick
  fps?: number
  signal?: AbortSignal
  onProgress?: (ratio: number) => void
  /** 시험에서 검출기 · 프레임 캡처를 갈아 끼운다. */
  deps?: Partial<ExtractDeps>
  createVideo?: () => HTMLVideoElement
}

function once(target: EventTarget, type: string, ms = 5000): Promise<void> {
  return new Promise((resolve, reject) => {
    const on = () => {
      clearTimeout(timer)
      resolve()
    }
    const timer = setTimeout(() => {
      target.removeEventListener(type, on)
      reject(new Error(`${type} 시간 초과`))
    }, ms)
    target.addEventListener(type, on, { once: true })
  })
}

function canvasGrab(): (v: HTMLVideoElement) => Frame {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  return (v) => {
    if (!ctx) throw new Error('캔버스를 쓸 수 없습니다')
    if (!canvas.width) {
      canvas.width = TRACK_W
      canvas.height = Math.max(1, Math.round((TRACK_W * v.videoHeight) / v.videoWidth))
    }
    ctx.drawImage(v, 0, 0, canvas.width, canvas.height)
    return ctx.getImageData(0, 0, canvas.width, canvas.height)
  }
}

const largest = (dets: Det[]) =>
  dets.slice().sort((a, b) => b.box.w * b.box.h - a.box.w * a.box.h)[0] ?? null

export async function extractMotion(src: string, opts: ExtractOptions): Promise<Motion> {
  const fps = opts.fps ?? EXTRACT_FPS
  let grabFn: ((v: HTMLVideoElement) => Frame) | null = null
  const deps: ExtractDeps = {
    detect: detectPeople,
    refine: refinePose,
    grab: (v) => (grabFn ??= canvasGrab())(v),
    ...opts.deps,
  }
  const video = (opts.createVideo ?? (() => document.createElement('video')))()
  video.muted = true
  video.playsInline = true
  video.preload = 'auto'

  const stopIfAborted = () => {
    if (opts.signal?.aborted) throw new DOMException('뽑기를 멈췄습니다', 'AbortError')
  }
  const poseOf = async (d: Det): Promise<Point[] | null> => {
    const fine = await deps.refine(video, d.box).catch(() => null)
    return fine ?? d.keypoints ?? null
  }

  try {
    const loaded = once(video, 'loadeddata', 15000)
    video.src = src
    video.load()
    await loaded
    stopIfAborted()

    const total = Math.max(1, Math.floor(video.duration * fps + 1e-6) + 1)
    const frames: (Point[] | null)[] = new Array(total).fill(null)
    let done = 0
    const tick = () => {
      done += 1
      opts.onProgress?.(Math.min(1, done / total))
    }
    const seek = async (i: number) => {
      const seeked = once(video, 'seeked')
      video.currentTime = Math.min(i / fps, video.duration)
      await seeked
      stopIfAborted()
    }
    const detectAt = async (i: number) => {
      await seek(i)
      const dets = await deps.detect(video)
      stopIfAborted()
      return dets
    }

    if (opts.pick === 'largest') {
      for (let i = 0; i < total; i += 1) {
        const big = largest(await detectAt(i))
        frames[i] = big ? await poseOf(big) : null
        tick()
      }
    } else {
      const drawn = opts.pick.box
      const start = Math.min(total - 1, Math.max(0, Math.round((opts.pick.atMs / 1000) * fps)))
      for (const dir of [1, -1] as const) {
        const dets0 = await detectAt(start)
        const box0 = snapToDetection(drawn, dets0) ?? drawn
        const tracker = createPersonTracker(deps.grab(video), box0)
        if (dir === 1) {
          const me = dets0.find((d) => d.box === box0)
          frames[start] = me ? await poseOf(me) : null
          tick()
        }
        for (let i = start + dir; i >= 0 && i < total; i += dir) {
          const dets = await detectAt(i)
          const r = tracker.step(dets, deps.grab(video))
          frames[i] = r.det && !r.lost ? await poseOf(r.det) : null
          tick()
        }
      }
    }

    return { fps, aspect: video.videoWidth / video.videoHeight, frames, measuredBy: 'browser' }
  } finally {
    video.removeAttribute('src')
    video.load()
  }
}
