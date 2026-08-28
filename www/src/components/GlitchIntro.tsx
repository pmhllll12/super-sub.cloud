'use client'

import { useEffect, useRef, useState, type CSSProperties } from 'react'
import {
  BANDS,
  ERASE_MS,
  HOLD_MS,
  SWAP_AT,
  TOTAL_MS,
  bandShifts,
  eraseProgress,
  glitchAmplitudeAt,
  inkProgress,
} from '@/lib/introInk'

/** 앱 이름. `flutter/lib/features/intro/presentation/brand_mark.dart`의 `kBrandText`. */
const BRAND_TEXT = 'SUPERSUB'

/**
 * 인트로 글자 크기. 화면 폭을 따라간다 — 앱은 한 손 크기라 52px 고정이면
 * 됐지만, 웹은 같은 값이 넓은 화면에서 우표만 하게 보인다.
 *
 * `clamp(52px, 5vw, 62px)` — 좁은 화면(375px)에서는 앱과 같은 52px 이고
 * (그때 글자가 이미 화면 폭의 85% 다 — 더 키우면 `SUPERSUB` 여덟 글자가
 * 화면 밖으로 나간다), 넓은 화면에서 **1.2배**까지 커진다. 상한을 168px
 * (세 배) → 72px → 62px 로 두 번 낮춘 값이다.
 *
 * 자간은 `BrandMark.letterSpacingFor`(size × 1.2 / 44)와 같은 공식을 CSS
 * `calc()` 로 옮긴 것이다 — 크기가 반응형이라 자바스크립트 쪽에서 숫자로
 * 계산할 수가 없다. 가지런한 Rubik 쪽에만 0.9px 을 더하는 것도 그대로다.
 */
const BRAND_SIZE = 'clamp(52px, 5vw, 62px)'
const BRAND_TRACKING = `calc(${BRAND_SIZE} * 1.2 / 44)`

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

/**
 * 워드마크가 제자리로 날아가는 곡선. 앞이 빠르고 뒤가 아주 부드럽게 멎는다 —
 * 잉크가 걷히는 것과 같은 성격이라 둘이 한 동작으로 읽힌다.
 *
 * 시간은 `ERASE_MS` 를 그대로 쓴다. 따로 두면 글자가 먼저 앉아 있는데 배경만
 * 남거나 그 반대가 되어, 두 동작이 하나로 안 보인다.
 */
const FLIGHT_EASING = 'cubic-bezier(0.22, 1, 0.36, 1)'

/**
 * 인트로가 끝나며 워드마크가 날아가 앉을 자리 — `BrandMark` 가 붙이는 표식.
 *
 * 반응형으로 크기가 다른 사본이 둘 이상 있을 수 있어(예: `AuthShell` 의
 * 34px/48px) **실제로 보이는 것 하나**를 고른다.
 */
function visibleBrandMark(): HTMLElement | null {
  const marks = Array.from(document.querySelectorAll<HTMLElement>('[data-brand-mark]'))
  return marks.find((el) => el.getBoundingClientRect().width > 0) ?? null
}

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
 * 지도가 "가운데→바깥" 큰 구조(r)를 ±로 흔드는 세기. CPU·GPU 공용 —
 * 눈으로 비교해 골랐다: 0.15 미만이면 경계가 너무 매끈해 로딩 스피너 같은
 * 원으로 보이고, 0.4를 넘으면 지도가 다시 큰 구조를 만들어버려(반복 무늬가
 * 여러 중심을 만들던 이전 문제로 회귀) 가운데부터 번지는 게 안 보인다.
 */
const DETAIL = 0.28

/**
 * `ink_field.png`를 화면 픽셀에 맞춰 반복시킬 때의 배율 — **WebGL 경로용.**
 * 1.0(1:1)이면 무늬가 굵다. 1보다 작을수록 지도가 더 자주 반복돼(거울
 * 반복이라 이음매는 안 생긴다) 알갱이가 고와진다. 0.6 아래로는 디테일이
 * 지글거리는 노이즈로 무너져 잉크 느낌이 사라져 그 직전에서 멈췄다.
 */
const FIELD_SCALE_GPU = 0.6

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
// 2. **지도를 늘려 덮지 않고, 원래 크기(1:1)로 반복(tile)한다.** 처음엔
//    `ink_field.png`(1080×2340)를 화면에 "cover"로 늘려 맞췄는데, 그러면
//    2560px 폭 화면에서 지도 무늬 자체가 2.4배로 확대돼 GPU가 픽셀마다
//    계산해도 알갱이가 굵게 나왔다 — 앱은 1080px 폰 화면이라 지도가 항상
//    원래 배율로 쓰인다. 화면의 실제 픽셀과 지도의 텍셀을 1:1로 맞추고,
//    화면이 지도보다 크면 그만큼 반복한다. `uFieldSize`(원본 텍셀 크기)는
//    그래서 추가한 유니폼이다(원본 8개 + 샘플러에는 없다).
//
//    **그냥 반복(REPEAT/fract)하면 이음매가 보였다.** `ink_field.png`는
//    이어 붙게(tileable) 구운 지도가 아니라서 타일 경계에서 밝기가 뚝
//    끊기는 선이 났다. 대신 좌표를 삼각파로 접는 거울 반복(mirror tile,
//    셰이더의 `mirrorFold`)을 쓴다 — 정의상 경계의 마지막 텍셀이 스스로와
//    맞붙으므로 이음매가 생길 수 없다. 덕분에 텍스처 래핑도 GL1/GL2 모두
//    그냥 `CLAMP_TO_EDGE`로 둔다(REPEAT류의 NPOT 제약을 아예 피한다) —
//    아래 `trySetupGpu`의 텍스처 파라미터 설정 참고.
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
uniform vec2 uFieldSize;  // uField 원본 텍셀 크기 × uFieldScale — 화면 픽셀과 맞춰 반복하는 주기(웹 전용 추가)
uniform float uProgress;
uniform float uSeed;
uniform float uBoil;
uniform float uEdge;
uniform float uErase;
uniform float uDetail;    // 지도가 경계를 흐트러뜨리는 세기 — 큰 구조(중심→가장자리)는 항상 r이 만든다
uniform vec3 uInk;
uniform sampler2D uField;

float hash(vec2 p, float seed) {
  vec3 q = fract(vec3(p.x, p.y, p.x) * 0.1031 + seed * 0.0037);
  q += dot(q, vec3(q.y, q.z, q.x) + 33.33);
  return fract((q.x + q.y) * q.z);
}

// 좌표 하나(어느 축이든)를 삼각파로 접어 [0,1] 안에 넣는다 — 매 정수
// 경계마다 앞뒤가 거울처럼 맞붙는다. ink_field.png는 이어 붙게(tileable)
// 구운 지도가 아니라서 그냥 반복(REPEAT/fract)하면 타일 경계에서 밝기가
// 뚝 끊기는 선이 보였다 — 거울 반복은 정의상 경계에서 항상 같은 값과
// 만나므로(마지막 텍셀이 스스로와 맞붙는다) 이음매가 생길 수가 없다.
// REPEAT/MIRRORED_REPEAT 같은 하드웨어 래핑도 필요 없다(WebGL1은 NPOT
// 텍스처에 어차피 못 쓴다) — CLAMP_TO_EDGE로 두고 여기서 좌표만 접는다.
float mirrorFold(float x) {
  float t = fract(x * 0.5) * 2.0;
  return 1.0 - abs(t - 1.0);
}

void main() {
  vec2 frag = vec2(gl_FragCoord.x, uSize.y - gl_FragCoord.y);
  vec2 clampedFrag = clamp(frag, vec2(0.5), uSize - 0.5);
  // cover로 늘려 맞추지 않는다 — 화면 픽셀과 지도 텍셀을 uFieldScale 배로
  // 맞추고 모자라는 만큼 거울 반복(mirror tile)한다(위 mirrorFold 참고).
  vec2 period = clampedFrag / uFieldSize;
  vec2 uv = vec2(mirrorFold(period.x), mirrorFold(period.y));

  // 큰 구조(어디부터 번지는가)는 화면 중심에서의 거리 r이 만든다. x/y를
  // 각각 uSize로 나누면 화면비가 정사각이 아닐 때 원이 타원으로 찌그러진다
  // — 대신 픽셀 단위(실제 정사각 픽셀) 거리를 구하고, 대각선 절반이라는
  // 스칼라 하나로 나눠 등방성을 지킨다. 대각선 기준이라 네 모서리까지
  // r=1 미만으로 채워진다.
  vec2 centerOffset = frag - uSize * 0.5;
  float halfDiag = length(uSize) * 0.5;
  float r = length(centerOffset) / max(halfDiag, 1.0);

  // 지도는 그 r을 ±로 흔드는 디테일일 뿐 — 큰 구조는 만들지 않는다(경계를
  // 잉크처럼 불규칙하게 만드는 역할). [0,1]로 다시 묶어 두는 이유는 아래
  // "젖는 중" 문턱 스윕이 이 범위를 기준으로 짜여 있어서다 — 넘치면 dry
  // 구간(progress=0)에도 중심 근처가 먼저 물드는 티가 난다.
  float detail = SAMPLE(uField, uv).r - 0.5;
  float order = clamp(r + detail * uDetail, 0.0, 1.0);
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
  'uDetail',
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
  // 깨진 뒤(RubikGlitch)의 스타일은 `BrandMark` 와 **한 글자도 달라선 안 된다**
  // — 인트로가 끝나면 이 글자가 그대로 그 자리로 날아가 앉기 때문이다.
  //
  // 굵기가 그 함정이었다. RubikGlitch 는 굵기가 하나뿐인 장식 글꼴이라
  // `font-weight: 900` 을 주면 브라우저가 **가짜 굵게(synthetic bold)** 를
  // 입힌다 — 자간·폭은 그대로라 측정으로는 안 잡히고 **획 두께만** 굵어져서,
  // 날아가 앉은 글자가 원래 워드마크보다 두껍게 보였다. 900 은 가변 글꼴인
  // Rubik(깨지기 전)에만 뜻이 있다.
  const style: CSSProperties = {
    fontFamily: glitched ? 'var(--font-rubik-glitch)' : 'var(--font-rubik)',
    fontWeight: glitched ? undefined : 900,
    fontVariationSettings: glitched ? undefined : "'wght' 900",
    fontSize: BRAND_SIZE,
    letterSpacing: glitched ? BRAND_TRACKING : `calc(${BRAND_TRACKING} + 0.9px)`,
    color: 'var(--ss-accent)',
    lineHeight: 1,
    whiteSpace: 'nowrap',
  }

  const shifts = bandShifts(seed, amplitude)

  // 어긋난 띠가 하나도 없으면 **자르지 않고 통짜로** 그린다.
  //
  // 자르기만 해도 조각 경계가 가는 가로줄로 보인다(글자 높이를 7로 나눈
  // 자리가 정수 픽셀에 안 떨어져 생기는 틈). 예전엔 진폭이 0보다 크면 늘
  // 어딘가 어긋나 있어서 드러나지 않았는데, 흔들림을 드문드문하게 바꾸면서
  // **"진폭은 있는데 이번 칸은 조용한" 순간이 대부분**이 됐다 — 그 순간마다
  // 멀쩡한 글자에 줄이 그어져 보였다.
  if (shifts.every((shift) => shift === 0)) {
    return <span style={style}>{BRAND_TEXT}</span>
  }

  return (
    <span style={{ position: 'relative', display: 'inline-block', lineHeight: 1 }}>
      {/* 크기만 잡는 숨은 사본 — 아래 절대배치 띠들의 기준 상자가 된다. */}
      <span style={{ ...style, visibility: 'hidden' }}>{BRAND_TEXT}</span>
      {shifts.map((shift, i) => (
        <span
          key={i}
          style={{
            ...style,
            position: 'absolute',
            inset: 0,
            // 아래쪽을 0.5px 넘겨 이웃 조각과 겹친다 — 딱 맞추면 경계가
            // 정수 픽셀에 안 떨어져 그 사이로 배경이 비쳐 줄로 보인다.
            clipPath: `inset(${(i / BANDS) * 100}% 0 calc(${100 - ((i + 1) / BANDS) * 100}% - 0.5px) 0)`,
            transform: `translateX(${shift}em)`,
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
  const inkRef = useRef<HTMLDivElement>(null)
  const markRef = useRef<HTMLSpanElement>(null)
  const [glitched, setGlitched] = useState(false)
  const [amplitude, setAmplitude] = useState(0)
  const [seedStep, setSeedStep] = useState(0)

  useEffect(() => {
    let cancelled = false
    let rafId = 0
    let done = false
    let exiting = false
    let start: number | null = null
    /** 비행 때 감춘 목적지 워드마크를 되살린다(멱등). */
    let restoreDest: () => void = () => {}

    let reducedMotion = false
    try {
      reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    } catch {
      reducedMotion = false
    }

    const finish = () => {
      if (done) return
      done = true
      // 되살린 뒤에 언마운트해야 한 프레임도 워드마크가 비지 않는다.
      restoreDest()
      onDone()
    }

    // 어느 경로(GPU/CPU)든 이 두 훅만 채우면 tick()은 신경 쓸 필요가 없다.
    let renderFrame: ((p: number, seed: number, erase: boolean) => void) | null = null
    let cleanupRender: () => void = () => {}

    /** WebGL2 → WebGL1 순으로 컨텍스트를 얻어 셰이더 경로를 세운다. 실패하면 false. */
    function trySetupGpu(img: HTMLImageElement): boolean {
      const container = inkRef.current
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
      // REPEAT/MIRRORED_REPEAT 둘 다 필요 없다 — 반복은 셰이더의 mirrorFold가
      // 좌표를 접어서 흉내 낸다(위 FRAGMENT_BODY 참고). uv가 항상 [0,1]
      // 안이라 CLAMP_TO_EDGE로도 충분하고, WebGL1의 NPOT(1080×2340처럼
      // 2의 거듭제곱이 아닌 텍스처) REPEAT 제약도 자연히 피한다 — GL1/GL2
      // 둘 다 같은 값을 쓴다.
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
      // FIELD_SCALE_GPU < 1이면 화면 픽셀 기준 지도 주기가 짧아져(더 자주
      // 거울 반복) 무늬가 더 작게(곱게) 보인다 — 위 FIELD_SCALE_GPU 참고.
      glc.uniform2f(
        uniforms.uFieldSize,
        (img.naturalWidth || 1) * FIELD_SCALE_GPU,
        (img.naturalHeight || 1) * FIELD_SCALE_GPU,
      )
      glc.uniform1f(uniforms.uBoil, BOIL)
      glc.uniform1f(uniforms.uEdge, EDGE_GPU)
      glc.uniform1f(uniforms.uErase, 0)
      glc.uniform1f(uniforms.uDetail, DETAIL)
      glc.uniform3f(uniforms.uInk, 0, 0, 0)

      // 잉크 레이어 안에 넣는다 — 이 레이어 자체가 글자 레이어보다 뒤라
      // 순서를 따로 맞출 필요가 없다.
      container.appendChild(canvas)

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

      renderFrame = (p, seed, erase) => {
        if (lost) return
        glc.uniform1f(uniforms.uProgress, p)
        glc.uniform1f(uniforms.uSeed, seed)
        // uErase=1이면 알파가 뒤집힌다(a = 1 - inked) — 같은 알갱이로 잉크가
        // 역으로 걷힌다. 셰이더에 이미 있던 유니폼이라 새로 만든 게 아니다.
        glc.uniform1f(uniforms.uErase, erase ? 1 : 0)
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
      const container = inkRef.current
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
      // 큰 구조(가운데→바깥)는 그리드 픽셀에서의 중심거리 r이 만들고, 지도는
      // 그 r을 ±DETAIL만큼 흔드는 디테일로만 쓴다 — WebGL 경로와 같은
      // 역할 분리(위 FRAGMENT_BODY 참고). r은 프레임마다 안 바뀌니 여기서
      // 한 번만 계산해 orderMap에 합쳐 둔다(렌더 루프에 비용을 더하지 않음).
      const halfDiag = Math.sqrt(gridW * gridW + gridH * gridH) / 2
      const orderMap = new Float32Array(gridW * gridH)
      let oi = 0
      for (let y = 0; y < gridH; y++) {
        for (let x = 0; x < gridW; x++, oi++) {
          const dxc = x - gridW / 2
          const dyc = y - gridH / 2
          const r = Math.min(1, Math.sqrt(dxc * dxc + dyc * dyc) / halfDiag)
          const detail = data[oi * 4] / 255 - 0.5
          orderMap[oi] = clamp(r + detail * DETAIL, 0, 1)
        }
      }

      canvas.width = gridW
      canvas.height = gridH
      const outCtx = canvas.getContext('2d')
      if (!outCtx) {
        finish()
        return
      }
      const outImage = outCtx.createImageData(gridW, gridH)
      const buf = outImage.data

      // 잉크 레이어 안에 넣는다 — 위 GPU 경로와 같다.
      container.appendChild(canvas)

      renderFrame = (p, seed, erase) => {
        const boilAmt = BOIL * p * (1 - p) * 4
        const threshold = mix(-EDGE_CPU, 1 + EDGE_CPU, p)

        let i = 0
        for (let y = 0; y < gridH; y++) {
          for (let x = 0; x < gridW; x++, i++) {
            const order = orderMap[i]
            const n = hash(x, y, seed) - 0.5
            const th = threshold + n * boilAmt
            const inked = smoothstep(order - EDGE_CPU, order + EDGE_CPU, th)
            // GPU 경로의 uErase와 같은 뒤집기.
            const a = erase ? 1 - inked : inked
            const o = i * 4
            buf[o] = 0
            buf[o + 1] = 0
            buf[o + 2] = 0
            buf[o + 3] = Math.round(a * 255)
          }
        }
        outCtx.putImageData(outImage, 0, 0)
      }
      cleanupRender = () => {
        container.removeChild(canvas)
      }
    }

    /**
     * 인트로에서 화면으로 넘어가는 마지막 구간을 시작한다 — 딱 한 번만.
     *
     * 두 동작이 같은 시간 동안 함께 일어난다:
     * 1. 잉크가 **역으로 걷힌다**(`tick` 의 erase 구간). 번질 때와 같은
     *    알갱이라 점 단위로 사라지며 밑의 화면이 드러난다
     * 2. 워드마크가 `BrandMark` 자리로 **날아가 앉는다**(FLIP)
     *
     * 잉크가 걷히기 시작하는 순간 화면은 아직 완전히 검다(진행도 1에서는
     * 모든 픽셀이 불투명하다). 그래서 그 밑의 민트 종이를 이때 치워도
     * 보이는 게 달라지지 않는다 — 치워야 걷힌 자리로 민트가 아니라 실제
     * 화면이 보인다.
     */
    function startExit() {
      inkRef.current?.style.setProperty('background', 'transparent')

      const mark = markRef.current
      if (reducedMotion || !mark) return

      const dest = visibleBrandMark()
      if (!dest) return

      const from = mark.getBoundingClientRect()
      const to = dest.getBoundingClientRect()
      if (!from.width || !to.width) return

      // 두 워드마크는 글꼴·자간 공식이 같아서(BrandMark.letterSpacingFor)
      // 크기만 다르다 — 회전·비틀림 없이 균등 확대·축소 하나로 정확히 겹친다.
      const scale = to.width / from.width
      const dx = to.left + to.width / 2 - (from.left + from.width / 2)
      const dy = to.top + to.height / 2 - (from.top + from.height / 2)

      // 날아가는 동안 목적지의 워드마크는 감춘다 — 같은 글자가 둘로 보인다.
      // 도착하면 되살린다(둘이 픽셀 단위로 겹쳐 있어 바뀌는 게 안 보인다).
      dest.style.visibility = 'hidden'
      restoreDest = () => {
        dest.style.visibility = ''
        restoreDest = () => {}
      }

      mark.animate(
        [
          { transform: 'translate(0px, 0px) scale(1)' },
          { transform: `translate(${dx}px, ${dy}px) scale(${scale})` },
        ],
        { duration: ERASE_MS, easing: FLIGHT_EASING, fill: 'forwards' },
      )
    }

    function tick(now: number) {
      if (cancelled) return
      if (start === null) start = now
      const elapsed = now - start

      // 1) 번지는 구간 — 잉크가 퍼지고 글자가 흔들린다.
      if (elapsed < TOTAL_MS) {
        const p = inkProgress(elapsed / TOTAL_MS)
        renderFrame?.(p, Math.round(elapsed), false)
        setGlitched(p >= SWAP_AT)
        setAmplitude(reducedMotion ? 0 : glitchAmplitudeAt(p))
        setSeedStep(Math.floor(elapsed / HOLD_MS))
        rafId = requestAnimationFrame(tick)
        return
      }

      // 2) 걷히는 구간 — 잉크가 역으로 사라지고 글자는 제자리로 날아간다.
      if (!exiting) {
        exiting = true
        setGlitched(true)
        setAmplitude(0)
        startExit()
      }

      const e = Math.min((elapsed - TOTAL_MS) / ERASE_MS, 1)
      renderFrame?.(eraseProgress(e), Math.round(elapsed), true)

      if (e >= 1) {
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
      // 비행 도중에 언마운트되면(경로 이동 등) 목적지 워드마크가 감춰진 채
      // 남는다 — 여기서도 되살린다.
      restoreDest()
    }
    // onDone은 IntroGate에서 useCallback으로 안정적으로 넘어온다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div ref={containerRef} className="fixed inset-0 z-50 overflow-hidden">
      {/* 잉크 레이어 — 민트 종이와 그 위의 잉크 캔버스. GPU/CPU 경로가 이
          div에 캔버스를 직접 붙였다 뗀다(두 경로가 컨텍스트 종류가 다른
          캔버스를 쓴다). **글자와 레이어를 나눈 이유**는 끝에서 잉크만
          걷어내고 글자는 남겨 제자리로 날려보내야 하기 때문이다. */}
      <div ref={inkRef} className="absolute inset-0" style={{ background: 'var(--ss-accent)' }} />
      <div className="absolute inset-0 flex items-center justify-center">
        {/* 비행하는 주체 — 이 래퍼의 상자가 곧 글자의 상자다(FLIP 기준).
            `lineHeight: 1` 이 필요하다. 없으면 이 inline-block 의 상자가
            글꼴 기본 줄높이(1.18배)로 커져서, 목적지 `BrandMark`(줄높이 1)와
            **상자 중심은 맞아도 글자 중심이 어긋난다.** */}
        <span ref={markRef} className="inline-block" style={{ lineHeight: 1 }}>
          <GlitchText glitched={glitched} amplitude={amplitude} seed={seedStep} />
        </span>
      </div>
    </div>
  )
}
