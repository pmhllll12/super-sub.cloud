'use client'

import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { letterSpacingFor } from './ui/BrandMark'
import {
  BANDS,
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
 * 저해상도 캔버스의 긴 변 길이(px). **CPU 폴백 전용.** 전체 해상도로 CPU
 * 픽셀 루프를 돌리면 느리다 — 낮춰 그려 CSS로 확대한다. WebGL 경로는
 * 프래그먼트 셰이더가 GPU에서 픽셀마다 도니 이 제약이 없다(아래 GPU 경로
 * 참고).
 *
 * **1400으로 실측해 정했다.** 안쪽 루프는 "지도값과 문턱값 비교 후 알파
 * 1픽셀 쓰기"뿐이라 저해상도에서는 여유가 크다 — 정사각형에 가까운 화면비가
 * 최악의 경우인데(긴 변 기준 그리드가 두 변 다 꽉 찬다), 900×900 뷰포트·
 * Apple Silicon 헤드리스 Chromium 기준으로 프레임당 평균 7.85ms, p95
 * 9.5ms였다. 2000까지 올리면 p95가 17.4ms로 16ms 예산을 넘는다(같은 뷰포트
 * 평균 13.73ms). 1400은 실제(더 느릴 수 있는) 기기와 이 프레임 안에서 함께
 * 도는 React 리렌더·컴포지팅을 위한 여유를 절반 가까이 남긴다.
 */
const GRID_LONG_EDGE = 1400

/** `ink_field.png`의 실제 크기(세로가 긴 인물 사진). `cover`로 채운다. */
const FIELD_SRC = '/ink_field.png'

/**
 * 문턱 경계 폭 — **CPU 폴백 전용.**
 *
 * Flutter 셰이더(`ink_bleed.frag`)의 `uEdge`는 0.02다(아래 `EDGE_GPU`) —
 * 하지만 그건 **픽셀마다** 계산하는 값이라 0.02로도 경계가 부드럽다. CPU
 * 폴백은 저해상도 캔버스를 CSS로 확대하는 방식이라 같은 0.02가 또렷한
 * 계단으로 보인다. 0.06~0.12 사이를 눈으로 비교해 0.09를 골랐다 — 이보다
 * 좁으면 격자가 남고, 넓으면 잉크가 안개처럼 퍼져 "번진다"는 느낌 대신
 * 흐릿해진다.
 */
const EDGE_CPU = 0.09

/**
 * 문턱 경계 폭 — **WebGL 경로용.** `flutter/lib/core/widgets/ink_bleed.dart`의
 * `_kEdge`를 그대로 옮겼다. GPU는 실제 화면 픽셀마다 계산하므로 CPU처럼
 * 넓힐 필요가 없다 — 원본 값 그대로가 앱과 같은 밀도를 낸다.
 */
const EDGE_GPU = 0.02

/**
 * 끓음 최대 폭. 문턱값을 이만큼 흔든다. `ink_bleed.dart`의 `_kBoil`과 같은
 * 값이라 CPU·GPU 두 경로가 함께 쓴다.
 */
const BOIL = 0.06

/**
 * 잉크 캔버스에만 거는 CSS blur(px, 표시 크기 기준) — **CPU 폴백 전용.**
 *
 * 확대로 생긴 격자를 지우는 데 가장 효과적이었다 — GPU 컴포지팅이라 거의
 * 공짜다. **글자 레이어에는 걸지 않는다** — 글자가 흐려지면 글리치(띠
 * 어긋남)가 죽는다. WebGL 경로는 이미 실제 픽셀 단위로 그리므로 이 blur가
 * 필요 없다.
 */
const INK_BLUR_PX = 1.5

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
 * 것(CPU 폴백용). 좌표 해시라 결과값 자체가 아니라 "프레임마다 바뀌는
 * 그럴듯한 잡음"이면 충분하다 — 비트 단위로 같을 필요는 없다. WebGL 경로는
 * 같은 식을 GLSL로 직접 쓴다(`FRAGMENT_BODY` 참고).
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

/** 화면을 `cover`로 채우는 그리기 사각형(대상 캔버스 기준) — CPU 폴백용. */
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

// ---------------------------------------------------------------------------
// WebGL — `flutter/shaders/ink_bleed.frag`의 이식.
//
// Flutter runtime effect 관례(FlutterFragCoord(), 유니폼 선언 순서 바인딩)를
// WebGL 관례(gl_FragCoord, getUniformLocation 이름 바인딩)로 바꿨을 뿐,
// 문턱값·해시·smoothstep 수식은 그대로다. 두 가지만 추가했다:
//
// 1. `uSize.y - gl_FragCoord.y`로 y를 뒤집는다 — WebGL의 gl_FragCoord는
//    좌하단이 원점(y 위로 증가)이고, Flutter의 FlutterFragCoord()는 좌상단이
//    원점(y 아래로 증가, 2D 캔버스·CPU 폴백과 같은 좌표계)이다. 텍스처는
//    기본 업로드(UNPACK_FLIP_Y_WEBGL=false)로 두면 v=0이 이미 이미지의 첫
//    행(맨 위)이라 이 y-뒤집기 하나로 CPU 폴백과 같은 결과가 나온다.
// 2. `coverUV` — `ink_field.png`(1080×2340 세로 인물 사진)를 CPU 폴백의
//    `coverRect`와 같은 "cover" 방식으로 화면에 맞춘다. 원본 앱은 위젯이
//    지도와 같은 화면비로 굽혀 있어 이 변환이 필요 없었지만, 웹은 임의의
//    뷰포트 화면비를 받으므로 필요하다. `uFieldSize`는 그래서 추가한
//    유니폼이다(원본 8개 + 샘플러에는 없다).
// ---------------------------------------------------------------------------

const VERTEX_GL2 = `#version 300 es
in vec2 aPos;
void main() {
  gl_Position = vec4(aPos, 0.0, 1.0);
}
`

const VERTEX_GL1 = `
attribute vec2 aPos;
void main() {
  gl_Position = vec4(aPos, 0.0, 1.0);
}
`

/** GL1/GL2 공용 본문. `SAMPLE`·`OUT_COLOR` 매크로만 헤더에서 갈아 끼운다. */
const FRAGMENT_BODY = `
uniform vec2 uSize;       // 캔버스 크기, 실제 화면 픽셀(framebuffer px)
uniform vec2 uFieldSize;  // uField 원본 텍셀 크기 — cover 계산용(웹 전용 추가)
uniform float uProgress;
uniform float uSeed;
uniform float uBoil;
uniform float uEdge;
uniform float uErase;
uniform vec3 uInk;
uniform sampler2D uField;

float hash(vec2 p, float seed) {
  vec3 q = fract(vec3(p.x, p.y, p.x) * 0.1031 + seed * 0.0037);
  q += dot(q, vec3(q.y, q.z, q.x) + 33.33);
  return fract((q.x + q.y) * q.z);
}

vec2 coverUV(vec2 f, vec2 size, vec2 fieldSize) {
  float scale = max(size.x / fieldSize.x, size.y / fieldSize.y);
  vec2 disp = fieldSize * scale;
  vec2 offset = (size - disp) * 0.5;
  return (f - offset) / disp;
}

void main() {
  vec2 frag = vec2(gl_FragCoord.x, uSize.y - gl_FragCoord.y);
  vec2 clampedFrag = clamp(frag, vec2(0.5), uSize - 0.5);
  vec2 uv = coverUV(clampedFrag, uSize, uFieldSize);

  float order = SAMPLE(uField, uv).r;
  float n = hash(frag, uSeed) - 0.5;

  float boil = uBoil * uProgress * (1.0 - uProgress) * 4.0;
  float t = mix(-uEdge, 1.0 + uEdge, uProgress) + n * boil;
  float inked = smoothstep(order - uEdge, order + uEdge, t);

  float a = mix(inked, 1.0 - inked, uErase);
  OUT_COLOR = vec4(uInk * a, a);
}
`

const FRAGMENT_GL2 = `#version 300 es
precision highp float;
out vec4 fragColorOut;
#define OUT_COLOR fragColorOut
#define SAMPLE texture
${FRAGMENT_BODY}`

const FRAGMENT_GL1 = `
precision highp float;
#define OUT_COLOR gl_FragColor
#define SAMPLE texture2D
${FRAGMENT_BODY}`

const UNIFORM_NAMES = [
  'uSize',
  'uFieldSize',
  'uProgress',
  'uSeed',
  'uBoil',
  'uEdge',
  'uErase',
  'uInk',
  'uField',
] as const

type UniformName = (typeof UNIFORM_NAMES)[number]
type GL = WebGL2RenderingContext | WebGLRenderingContext

function compileShader(gl: GL, type: number, source: string): WebGLShader | null {
  const shader = gl.createShader(type)
  if (!shader) return null
  gl.shaderSource(shader, source)
  gl.compileShader(shader)
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    console.warn('[GlitchIntro] WebGL 셰이더 컴파일 실패:', gl.getShaderInfoLog(shader))
    gl.deleteShader(shader)
    return null
  }
  return shader
}

/** 셰이더 컴파일 → 링크 → 유니폼/attribute 위치 조회까지 한 번에. 실패하면 null(호출부가 CPU로 물러선다). */
function buildGpuProgram(
  gl: GL,
  isGL2: boolean,
): { program: WebGLProgram; uniforms: Record<UniformName, WebGLUniformLocation>; aPos: number } | null {
  const vs = compileShader(gl, gl.VERTEX_SHADER, isGL2 ? VERTEX_GL2 : VERTEX_GL1)
  if (!vs) return null
  const fs = compileShader(gl, gl.FRAGMENT_SHADER, isGL2 ? FRAGMENT_GL2 : FRAGMENT_GL1)
  if (!fs) {
    gl.deleteShader(vs)
    return null
  }
  const program = gl.createProgram()
  if (!program) {
    gl.deleteShader(vs)
    gl.deleteShader(fs)
    return null
  }
  gl.attachShader(program, vs)
  gl.attachShader(program, fs)
  gl.linkProgram(program)
  // 링크 후에는 셰이더 오브젝트가 더 필요 없다 — 프로그램에 이미 붙었다.
  gl.deleteShader(vs)
  gl.deleteShader(fs)
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    console.warn('[GlitchIntro] WebGL 프로그램 링크 실패:', gl.getProgramInfoLog(program))
    gl.deleteProgram(program)
    return null
  }

  const aPos = gl.getAttribLocation(program, 'aPos')
  if (aPos < 0) {
    gl.deleteProgram(program)
    return null
  }

  const uniforms = {} as Record<UniformName, WebGLUniformLocation>
  for (const name of UNIFORM_NAMES) {
    const loc = gl.getUniformLocation(program, name)
    if (!loc) {
      gl.deleteProgram(program)
      return null
    }
    uniforms[name] = loc
  }

  return { program, uniforms, aPos }
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
 * `flutter/lib/core/widgets/ink_bleed.dart`, `flutter/shaders/ink_bleed.frag`.
 * `ink_field.png`를 "잉크가 앉는 순서 지도"로 읽고, 지도값이 진행도보다
 * 작은 픽셀에 잉크를 칠한다.
 *
 * 그리기는 WebGL2 → WebGL1 → CPU(canvas 2D) 순으로 시도한다. 앱과 같은
 * 알갱이 밀도를 내려면 GPU가 실제 화면 픽셀마다 계산해야 하기 때문이다 —
 * CPU 폴백은 저해상도로 그려 확대하므로 격자가 굵다(위 CPU 전용 상수들
 * 참고). 컨텍스트를 얻지 못하거나 셰이더 컴파일·링크가 실패하면 CPU로
 * 조용히 물러선다. 다 그린 뒤 **컨텍스트를 잃으면**(`webglcontextlost`)
 * 복구를 시도하지 않고 인트로를 즉시 끝낸다 — 연출 때문에 앱이 안 열리면
 * 안 된다.
 */
export default function GlitchIntro({ onDone }: { onDone: () => void }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [glitched, setGlitched] = useState(false)
  const [amplitude, setAmplitude] = useState(0)
  const [seedStep, setSeedStep] = useState(0)

  useEffect(() => {
    let cancelled = false
    let rafId = 0
    let done = false
    let start: number | null = null

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

    // 어느 경로(GPU/CPU)든 이 두 훅만 채우면 tick()은 신경 쓸 필요가 없다.
    let renderFrame: ((p: number, seed: number) => void) | null = null
    let cleanupRender: () => void = () => {}

    /** WebGL2 → WebGL1 순으로 컨텍스트를 얻어 셰이더 경로를 세운다. 실패하면 false. */
    function trySetupGpu(img: HTMLImageElement): boolean {
      const container = containerRef.current
      if (!container) return false

      const canvas = document.createElement('canvas')
      canvas.className = 'absolute inset-0 h-full w-full'
      // CPU 폴백과 달리 blur를 걸지 않는다 — GPU는 이미 실제 픽셀 단위로
      // 그리므로 확대 격자를 감출 필요가 없다.

      let gl: GL | null = null
      let isGL2 = true
      try {
        gl = canvas.getContext('webgl2') as WebGL2RenderingContext | null
        if (!gl) {
          isGL2 = false
          gl = canvas.getContext('webgl') as WebGLRenderingContext | null
        }
      } catch {
        gl = null
      }
      if (!gl) return false
      // TS는 `let gl`이 아래 클로저(renderFrame 등) 안에서 재할당됐을지
      // 모른다고 보고 null 좁힘을 안 지켜준다 — const로 한 번 더 못박는다.
      const glc: GL = gl

      const built = buildGpuProgram(glc, isGL2)
      if (!built) return false
      const { program, uniforms, aPos } = built

      const buffer = glc.createBuffer()
      if (!buffer) {
        glc.deleteProgram(program)
        return false
      }
      glc.bindBuffer(glc.ARRAY_BUFFER, buffer)
      glc.bufferData(
        glc.ARRAY_BUFFER,
        new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]),
        glc.STATIC_DRAW,
      )

      const texture = glc.createTexture()
      if (!texture) {
        glc.deleteProgram(program)
        glc.deleteBuffer(buffer)
        return false
      }
      glc.bindTexture(glc.TEXTURE_2D, texture)
      glc.texParameteri(glc.TEXTURE_2D, glc.TEXTURE_MIN_FILTER, glc.LINEAR)
      glc.texParameteri(glc.TEXTURE_2D, glc.TEXTURE_MAG_FILTER, glc.LINEAR)
      glc.texParameteri(glc.TEXTURE_2D, glc.TEXTURE_WRAP_S, glc.CLAMP_TO_EDGE)
      glc.texParameteri(glc.TEXTURE_2D, glc.TEXTURE_WRAP_T, glc.CLAMP_TO_EDGE)
      try {
        glc.texImage2D(glc.TEXTURE_2D, 0, glc.RGBA, glc.RGBA, glc.UNSIGNED_BYTE, img)
      } catch {
        glc.deleteProgram(program)
        glc.deleteBuffer(buffer)
        glc.deleteTexture(texture)
        return false
      }

      const dpr = window.devicePixelRatio || 1
      const rect = container.getBoundingClientRect()
      const vw = rect.width || window.innerWidth || 1
      const vh = rect.height || window.innerHeight || 1
      // **실제 화면 픽셀** — devicePixelRatio를 반영해야 앱과 같은 밀도가 난다.
      canvas.width = Math.max(1, Math.round(vw * dpr))
      canvas.height = Math.max(1, Math.round(vh * dpr))

      glc.viewport(0, 0, canvas.width, canvas.height)
      glc.disable(glc.DEPTH_TEST)
      glc.disable(glc.BLEND)

      glc.useProgram(program)
      glc.bindBuffer(glc.ARRAY_BUFFER, buffer)
      glc.enableVertexAttribArray(aPos)
      glc.vertexAttribPointer(aPos, 2, glc.FLOAT, false, 0, 0)

      glc.activeTexture(glc.TEXTURE0)
      glc.bindTexture(glc.TEXTURE_2D, texture)
      glc.uniform1i(uniforms.uField, 0)
      glc.uniform2f(uniforms.uSize, canvas.width, canvas.height)
      glc.uniform2f(uniforms.uFieldSize, img.naturalWidth || 1, img.naturalHeight || 1)
      glc.uniform1f(uniforms.uBoil, BOIL)
      glc.uniform1f(uniforms.uEdge, EDGE_GPU)
      glc.uniform1f(uniforms.uErase, 0)
      glc.uniform3f(uniforms.uInk, 0, 0, 0)

      // 글자 레이어(container의 기존 자식)보다 뒤에 와야 한다 — DOM 순서가
      // 곧 쌓임 순서다. appendChild면 글자를 덮어 버린다.
      container.insertBefore(canvas, container.firstChild)

      let lost = false
      const onContextLost = (e: Event) => {
        // 복구를 시도하지 않는다(preventDefault 안 함) — 잃으면 그냥 끝낸다.
        e.preventDefault()
        lost = true
        cancelled = true
        cancelAnimationFrame(rafId)
        finish()
      }
      canvas.addEventListener('webglcontextlost', onContextLost, false)

      renderFrame = (p, seed) => {
        if (lost) return
        glc.uniform1f(uniforms.uProgress, p)
        glc.uniform1f(uniforms.uSeed, seed)
        glc.drawArrays(glc.TRIANGLE_STRIP, 0, 4)
      }
      cleanupRender = () => {
        canvas.removeEventListener('webglcontextlost', onContextLost)
        if (!lost) {
          glc.deleteTexture(texture)
          glc.deleteBuffer(buffer)
          glc.deleteProgram(program)
        }
        container.removeChild(canvas)
      }
      return true
    }

    /** CPU(canvas 2D) 폴백 — WebGL을 못 쓰거나 셰이더가 실패했을 때. */
    function startCpu(img: HTMLImageElement) {
      const container = containerRef.current
      if (!container) {
        finish()
        return
      }

      const canvas = document.createElement('canvas')
      canvas.className = 'absolute'
      // blur가 가장자리를 살짝 안으로 깎아 먹는다 — 컨테이너보다 약간 크게
      // 그려 overflow-hidden으로 잘라내면 그 티가 안 난다.
      canvas.style.inset = '-4px'
      canvas.style.width = 'calc(100% + 8px)'
      canvas.style.height = 'calc(100% + 8px)'
      canvas.style.imageRendering = 'auto'
      canvas.style.filter = `blur(${INK_BLUR_PX}px)`

      const rect = container.getBoundingClientRect()
      const vw = rect.width || window.innerWidth || 1
      const vh = rect.height || window.innerHeight || 1
      const aspect = vw / vh

      let gridW: number
      let gridH: number
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
      if (!octx) {
        finish()
        return
      }
      const { dx, dy, dw, dh } = coverRect(img.naturalWidth, img.naturalHeight, gridW, gridH)
      octx.drawImage(img, dx, dy, dw, dh)
      const data = octx.getImageData(0, 0, gridW, gridH).data
      const orderMap = new Float32Array(gridW * gridH)
      for (let i = 0; i < orderMap.length; i++) orderMap[i] = data[i * 4] / 255

      canvas.width = gridW
      canvas.height = gridH
      const outCtx = canvas.getContext('2d')
      if (!outCtx) {
        finish()
        return
      }
      const outImage = outCtx.createImageData(gridW, gridH)
      const buf = outImage.data

      // 글자 레이어보다 뒤에 와야 한다 — 위 GPU 경로와 같은 이유.
      container.insertBefore(canvas, container.firstChild)

      renderFrame = (p, seed) => {
        const boilAmt = BOIL * p * (1 - p) * 4
        const threshold = mix(-EDGE_CPU, 1 + EDGE_CPU, p)

        let i = 0
        for (let y = 0; y < gridH; y++) {
          for (let x = 0; x < gridW; x++, i++) {
            const order = orderMap[i]
            const n = hash(x, y, seed) - 0.5
            const th = threshold + n * boilAmt
            const inked = smoothstep(order - EDGE_CPU, order + EDGE_CPU, th)
            const o = i * 4
            buf[o] = 0
            buf[o + 1] = 0
            buf[o + 2] = 0
            buf[o + 3] = Math.round(inked * 255)
          }
        }
        outCtx.putImageData(outImage, 0, 0)
      }
      cleanupRender = () => {
        container.removeChild(canvas)
      }
    }

    function tick(now: number) {
      if (cancelled) return
      if (start === null) start = now
      const elapsed = now - start
      const t = Math.min(elapsed / TOTAL_MS, 1)
      const p = inkProgress(t)

      renderFrame?.(p, Math.round(elapsed))

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

      let gpuOk = false
      try {
        gpuOk = trySetupGpu(img)
      } catch (err) {
        // 셰이더 컴파일·링크 실패를 포함해 여기로 온 어떤 예외든 CPU로
        // 조용히 물러선다 — 사용자에게 에러를 보이지 않는다.
        console.warn('[GlitchIntro] WebGL 초기화 실패, CPU로 물러섬:', err)
        gpuOk = false
      }

      if (!gpuOk) {
        try {
          startCpu(img)
        } catch {
          finish()
          return
        }
      }

      if (!renderFrame) {
        // startCpu가 이미 finish()를 불렀을 수도 있다 — finish는 멱등이다.
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
      cleanupRender()
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
      {/* 잉크 캔버스는 GPU/CPU 경로가 이 컨테이너에 직접 붙였다 뗀다 —
          두 경로가 컨텍스트 종류(webgl/2d)가 다른 캔버스가 필요해서다. */}
      <div className="absolute inset-0 flex items-center justify-center">
        <GlitchText glitched={glitched} amplitude={amplitude} seed={seedStep} />
      </div>
    </div>
  )
}
