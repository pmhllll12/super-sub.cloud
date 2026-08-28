'use client'

import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { letterSpacingFor } from './ui/BrandMark'
import {
  BANDS,
  BOIL,
  EDGE,
  HOLD_MS,
  SWAP_AT,
  TOTAL_MS,
  glitchAmplitudeAt,
  inkProgress,
} from '@/lib/introInk'

/** 앱 이름. `flutter/lib/features/intro/presentation/brand_mark.dart`의 `kBrandText`. */
const BRAND_TEXT = 'SUPERSUB'

/** 인트로 글자 크기. */
const BRAND_SIZE = 52

/**
 * 저해상도 캔버스의 긴 변 길이(px). 전체 해상도로 CPU 픽셀 루프를 돌리면
 * 느리다 — 480~640 사이로 그려 CSS로 확대한다. 잉크가 부드러운 노이즈라
 * 확대해도 자연스럽다.
 */
const GRID_LONG_EDGE = 560

/** `ink_field.png`의 실제 크기(세로가 긴 인물 사진). `cover`로 채운다. */
const FIELD_SRC = '/ink_field.png'

function clamp(x: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, x))
}

function mix(a: number, b: number, t: number): number {
  return a + (b - a) * t
}

function smoothstep(edge0: number, edge1: number, x: number): number {
  const t = clamp((x - edge0) / (edge1 - edge0), 0, 1)
  return t * t * (3 - 2 * t)
}

function frac(x: number): number {
  return x - Math.floor(x)
}

/**
 * `flutter/shaders/ink_bleed.frag`의 `hash(vec2 p, float seed)`를 그대로 옮긴
 * 것. 좌표 해시라 결과값 자체가 아니라 "프레임마다 바뀌는 그럴듯한 잡음"이면
 * 충분하다 — 비트 단위로 같을 필요는 없다.
 */
function hash(x: number, y: number, seed: number): number {
  const a = frac(x * 0.1031 + seed * 0.0037)
  const b = frac(y * 0.1031 + seed * 0.0037)
  // q = (a, b, a) — vec3(p.x, p.y, p.x)라 x·z 성분이 같은 값에서 시작한다.
  const d = a * (b + 33.33) + b * (a + 33.33) + a * (a + 33.33)
  const qx = a + d
  const qy = b + d
  const qz = a + d
  return frac((qx + qy) * qz)
}

/** `seed`로 결정되는 [-1, 1) 사이 값 7개(띠 수만큼). 표준 mulberry32 PRNG. */
function bandShifts(seed: number, amplitude: number): number[] {
  let a = seed >>> 0
  const next = () => {
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
  return Array.from({ length: BANDS }, () => (next() * 2 - 1) * amplitude * 14)
}

/** 화면을 `cover`로 채우는 그리기 사각형(대상 캔버스 기준). */
function coverRect(
  srcW: number,
  srcH: number,
  dstW: number,
  dstH: number,
): { dx: number; dy: number; dw: number; dh: number } {
  const scale = Math.max(dstW / srcW, dstH / srcH)
  const dw = srcW * scale
  const dh = srcH * scale
  return { dx: (dstW - dw) / 2, dy: (dstH - dh) / 2, dw, dh }
}

/**
 * 가지런한 Rubik으로 시작해 잉크 진행도 [SWAP_AT]에서 RubikGlitch로 갈아
 * 끼우는 워드마크. 흔들리는 동안은 가로 [BANDS]개 띠로 잘라 띠마다 다른 양
 * 만큼 어긋낸다 — 통째로 미는 게 아니라 화면이 찢어진 것처럼 보여야 한다.
 */
function GlitchText({
  glitched,
  amplitude,
  seed,
}: {
  glitched: boolean
  amplitude: number
  seed: number
}) {
  const style: CSSProperties = {
    fontFamily: glitched ? 'var(--font-rubik-glitch)' : 'var(--font-rubik)',
    fontWeight: 900,
    fontVariationSettings: "'wght' 900",
    fontSize: `${BRAND_SIZE}px`,
    letterSpacing: glitched
      ? `${letterSpacingFor(BRAND_SIZE)}px`
      : `${letterSpacingFor(BRAND_SIZE) + 0.9}px`,
    color: 'var(--ss-accent)',
    lineHeight: 1,
    whiteSpace: 'nowrap',
  }

  if (amplitude <= 0) {
    return <span style={style}>{BRAND_TEXT}</span>
  }

  const shifts = bandShifts(seed, amplitude)

  return (
    <span style={{ position: 'relative', display: 'inline-block' }}>
      {/* 크기만 잡는 숨은 사본 — 아래 절대배치 띠들의 기준 상자가 된다. */}
      <span style={{ ...style, visibility: 'hidden' }}>{BRAND_TEXT}</span>
      {shifts.map((shift, i) => (
        <span
          key={i}
          style={{
            ...style,
            position: 'absolute',
            inset: 0,
            clipPath: `inset(${(i / BANDS) * 100}% 0 ${100 - ((i + 1) / BANDS) * 100}% 0)`,
            transform: `translateX(${shift}px)`,
          }}
        >
          {BRAND_TEXT}
        </span>
      ))}
    </span>
  )
}

/**
 * 앱 진입 인트로. 민트 종이 위에 검은 잉크가 번지고, 그 대비로 같은 민트색
 * 글자가 드러난다 — 글자는 나타나는 게 아니라 처음부터 거기 있었다.
 *
 * 원본: `flutter/lib/features/intro/presentation/screens/glitch_intro_screen.dart`,
 * `flutter/lib/core/widgets/ink_bleed.dart`. 셰이더 대신 canvas 2D로 같은
 * 일을 한다 — `ink_field.png`를 "잉크가 앉는 순서 지도"로 읽고, 지도값이
 * 진행도보다 작은 픽셀에 잉크를 칠한다.
 */
export default function GlitchIntro({ onDone }: { onDone: () => void }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [glitched, setGlitched] = useState(false)
  const [amplitude, setAmplitude] = useState(0)
  const [seedStep, setSeedStep] = useState(0)

  useEffect(() => {
    let cancelled = false
    let rafId = 0
    let done = false

    let reducedMotion = false
    try {
      reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    } catch {
      reducedMotion = false
    }

    const finish = () => {
      if (done) return
      done = true
      onDone()
    }

    let orderMap: Float32Array | null = null
    let gridW = 0
    let gridH = 0
    let outImage: ImageData | null = null
    let outCtx: CanvasRenderingContext2D | null = null

    /** `ink_field.png`를 오프스크린 저해상도 캔버스에 그려 밝기 지도를 뽑는다. */
    function buildMap(img: HTMLImageElement) {
      const rect = containerRef.current?.getBoundingClientRect()
      const vw = rect?.width || window.innerWidth || 1
      const vh = rect?.height || window.innerHeight || 1
      const aspect = vw / vh

      if (aspect >= 1) {
        gridW = GRID_LONG_EDGE
        gridH = Math.max(1, Math.round(GRID_LONG_EDGE / aspect))
      } else {
        gridH = GRID_LONG_EDGE
        gridW = Math.max(1, Math.round(GRID_LONG_EDGE * aspect))
      }

      const off = document.createElement('canvas')
      off.width = gridW
      off.height = gridH
      const octx = off.getContext('2d', { willReadFrequently: true })
      if (!octx) throw new Error('오프스크린 2D 컨텍스트를 못 만들었다')

      const { dx, dy, dw, dh } = coverRect(img.naturalWidth, img.naturalHeight, gridW, gridH)
      octx.drawImage(img, dx, dy, dw, dh)
      const data = octx.getImageData(0, 0, gridW, gridH).data

      const map = new Float32Array(gridW * gridH)
      for (let i = 0; i < map.length; i++) map[i] = data[i * 4] / 255
      orderMap = map

      const canvas = canvasRef.current
      if (!canvas) throw new Error('캔버스가 아직 안 붙었다')
      canvas.width = gridW
      canvas.height = gridH
      outCtx = canvas.getContext('2d')
      if (!outCtx) throw new Error('캔버스 2D 컨텍스트를 못 만들었다')
      outImage = outCtx.createImageData(gridW, gridH)
    }

    /** 진행도 `p`, 씨앗 `seed`로 저해상도 캔버스 한 프레임을 채운다. */
    function paintInk(p: number, seed: number) {
      if (!orderMap || !outImage || !outCtx) return
      const buf = outImage.data
      const boilAmt = BOIL * p * (1 - p) * 4
      const threshold = mix(-EDGE, 1 + EDGE, p)

      let i = 0
      for (let y = 0; y < gridH; y++) {
        for (let x = 0; x < gridW; x++, i++) {
          const order = orderMap[i]
          const n = hash(x, y, seed) - 0.5
          const th = threshold + n * boilAmt
          const inked = smoothstep(order - EDGE, order + EDGE, th)
          const o = i * 4
          buf[o] = 0
          buf[o + 1] = 0
          buf[o + 2] = 0
          buf[o + 3] = Math.round(inked * 255)
        }
      }
      outCtx.putImageData(outImage, 0, 0)
    }

    let start: number | null = null

    function tick(now: number) {
      if (cancelled) return
      if (start === null) start = now
      const elapsed = now - start
      const t = Math.min(elapsed / TOTAL_MS, 1)
      const p = inkProgress(t)

      paintInk(p, Math.round(elapsed))

      setGlitched(p >= SWAP_AT)
      setAmplitude(reducedMotion ? 0 : glitchAmplitudeAt(p))
      setSeedStep(Math.floor(elapsed / HOLD_MS))

      if (elapsed >= TOTAL_MS) {
        finish()
        return
      }
      rafId = requestAnimationFrame(tick)
    }

    const img = new Image()
    img.onload = () => {
      if (cancelled) return
      try {
        buildMap(img)
      } catch {
        // 캔버스를 못 쓰면 연출 없이 즉시 끝낸다 — 인트로 때문에 앱이
        // 안 열리면 안 된다.
        finish()
        return
      }
      rafId = requestAnimationFrame(tick)
    }
    img.onerror = () => {
      if (cancelled) return
      finish()
    }
    img.src = FIELD_SRC

    return () => {
      cancelled = true
      cancelAnimationFrame(rafId)
    }
    // onDone은 IntroGate에서 useCallback으로 안정적으로 넘어온다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 z-50 overflow-hidden"
      style={{ background: 'var(--ss-accent)' }}
    >
      <canvas
        ref={canvasRef}
        className="absolute inset-0 h-full w-full"
        style={{ imageRendering: 'auto' }}
      />
      <div className="absolute inset-0 flex items-center justify-center">
        <GlitchText glitched={glitched} amplitude={amplitude} seed={seedStep} />
      </div>
    </div>
  )
}
