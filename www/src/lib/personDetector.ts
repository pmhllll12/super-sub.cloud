/**
 * 브라우저에서 도는 **사람 검출기** — MoveNet MultiPose Lightning.
 *
 * 🔴 진짜 검출은 에이전트 몫이다(`agent/pose.py` 의 RT-DETR + ViTPose). 그런데
 * 업로드 전송 경로가 아직 없어(계약 5장 ASM-003) 서버로 나가는 것이 하나도
 * 없다. 그렇다고 박스를 가짜로 그릴 수는 없어서 — 화면에서 "따라가는 중" 이라고
 * 말하는 이상 정말로 따라가야 한다 — **브라우저에서 같은 종류의 일을 한다.**
 *
 * ## 🔴 `@tensorflow-models/pose-detection` 을 안 쓰고 모델을 직접 부른다
 *
 * 그 패키지를 먼저 깔았다가 걷어냈다. 안에 BlazePose 가 들어 있고, 그게
 * **레거시 `@mediapipe/pose` 를 정적 import** 한다 — 그 파일은 ESM export 가
 * 하나도 없는 UMD 스크립트라 Turbopack 빌드가 통째로 깨진다
 * (`Export Pose doesn't exist in target module`). 우리는 MoveNet 하나만 쓰는데
 * 쓰지도 않는 모델 때문에 빌드가 막히는 셈이다.
 *
 * MoveNet 의 출력은 해석이 단순해서(아래 표) 직접 부르는 편이 오히려 짧다.
 * 남는 의존성은 `tfjs-core` · `tfjs-converter` · `tfjs-backend-webgl` 셋뿐이다.
 *
 * ## 출력 읽는 법 — `[1, 6, 56]`
 *
 * 사람 한 명이 56 개 숫자다:
 *
 * | 자리 | 무엇 |
 * |---|---|
 * | 0~50 | 관절 17개 × (y, x, 점수) — **입력 그림 기준 0~1** |
 * | 51~54 | 상자 ymin, xmin, ymax, xmax |
 * | 55 | 이 사람의 점수 |
 *
 * ⚠️ **한 번에 최대 6명**이다. 그보다 붐비면 내 사람이 안 잡힐 수 있는데,
 * 그때는 짝짓기(`personTrack`)가 "못 찾음" 으로 넘기고 다음 프레임에 다시
 * 잡히면 이어 붙는다 — 검출이 화면 전체를 보므로 **놓쳐도 돌아온다.**
 *
 * ⚠️ 모델 파일은 처음 한 번 내려받는다(수 MB). 못 내려받으면 화면은 그대로
 * 돌아가되 따라가기만 꺼진다 — 여기서 던지지 않는 이유다. 망을 못 타는
 * 환경이면 모델을 `public/` 에 받아 두고 아래 주소만 바꾸면 된다.
 */

import type { Box } from './box'
import type { Det } from './personTrack'
import { MIN_KP, type Point } from './pose'

const MODEL_URL = 'https://tfhub.dev/google/tfjs-model/movenet/multipose/lightning/1'

/**
 * 2단계용 모델 — 사람 **하나**를 256×256 에 꽉 채워 넣고 관절만 다시 뽑는다.
 *
 * 🔴 관절이 흐릿한 진짜 이유는 모델이 아니라 **픽셀 수**다. 위 MultiPose 는
 * 화면 전체를 256px 로 줄여서 보는데, 그 안에서 멀리 있는 선수는 가로 30px
 * 남짓이다 — 그 크기에서 손목 · 발목을 정확히 찍을 수가 없다.
 *
 * 실제 시스템이 쓰는 방법이 이것이다(top-down): **찾는 것과 재는 것을 나눈다.**
 * 화면 전체에서 사람들을 찾고(MultiPose), 따라가기로 정한 그 사람만 잘라
 * 확대해 다시 잰다(Thunder). 같은 사람에게 **여덟 배쯤 많은 픽셀**이 간다.
 *
 * 출력은 `[1, 1, 17, 3]` — 관절마다 `y, x, 점수` 이고 **잘라 낸 상자 기준**
 * 0~1 이다. 원래 좌표로 되돌리는 셈이 아래에 있다.
 */
/**
 * 🔴 Thunder(256) 로 시작했다가 **Lightning(192) 으로 내렸다.** 프레임마다
 * 모델을 두 번 돌리는데 Thunder 는 그 자체로 무거워서, 관절이 눈에 띄게
 * 뒤늦게 따라왔다(사용자 지적). 셋 배쯤 빨라지는 대신 정확도를 조금 내준다 —
 * 그래도 화면 전체를 256px 로 줄여 보던 1단계보다는 훨씬 촘촘하다.
 * 되돌리려면 아래 두 줄만 `singlepose/thunder/4` · 256 으로 바꾸면 된다.
 */
const REFINE_URL = 'https://tfhub.dev/google/tfjs-model/movenet/singlepose/lightning/4'
const REFINE_SIZE = 192

/**
 * 잘라 낼 때 상자보다 이만큼 넓게 잡는다.
 *
 * 🔴 딱 맞춰 자르면 안 된다. 상자는 몸을 겨우 감싸는 크기라 팔을 뻗거나 다리를
 * 들면 그 끝이 잘려 나가고, 잘린 관절은 모델이 가장자리에 붙여 놓는다.
 */
const REFINE_PAD = 1.2

/**
 * 다시 잰 관절 중 이만큼은 **그 사람 상자 안**에 들어와야 인정한다.
 *
 * 🔴 2단계 모델은 **한 사람만** 찍는다. 잘라 낸 자리에 옆 사람이 같이 들어오면
 * 그 사람을 집어 버리는데, 그러면 상자는 제대로 있는데 막대기만 옆으로 넘어간다
 * (사용자 지적). 나온 관절이 정말 그 상자의 사람인지 되물어서 아니면 버린다 —
 * 버리면 1단계 관절을 쓴다. 1단계 것은 짝짓기를 통과한 값이라 사람이 틀릴 수 없다.
 */
const REFINE_INSIDE = 0.65

/** 팔다리는 상자 밖으로 나간다 — 안쪽인지 볼 때 이만큼 넓혀서 본다. */
const REFINE_SLACK = 0.25

/** 입력의 긴 변. MoveNet 은 가로 · 세로가 **32의 배수**여야 한다. */
const IN_LONG = 256
const MULT = 32

/** 이 점수 아래는 사람이라고 보지 않는다. */
const MIN_DET = 0.2

type GraphModelLike = { execute(input: unknown): { data(): Promise<Float32Array>; dispose(): void } }
type TF = typeof import('@tensorflow/tfjs-core')

/**
 * 한 번만 만든다. 🔴 모듈 수준에 두는 이유 — 화면을 들락거릴 때마다 다시
 * 만들면 그때마다 모델을 올린다(수백 ms + GPU 메모리).
 */
let ready: Promise<{ tf: TF; model: GraphModelLike }> | null = null

/** 그림을 담는 캔버스. 매번 만들면 GPU 텍스처가 그만큼 새로 잡힌다. */
let canvas: HTMLCanvasElement | null = null

async function load() {
  const [tf, converter] = await Promise.all([
    import('@tensorflow/tfjs-core'),
    import('@tensorflow/tfjs-converter'),
    import('@tensorflow/tfjs-backend-webgl'),
  ])
  await tf.setBackend('webgl')
  await tf.ready()
  const model = (await converter.loadGraphModel(MODEL_URL, {
    fromTFHub: true,
  })) as unknown as GraphModelLike
  return { tf, model }
}

let readyRefine: Promise<{ tf: TF; model: GraphModelLike }> | null = null
let refineCanvas: HTMLCanvasElement | null = null

async function loadRefine() {
  const { tf } = await warmUpDetector()
  const converter = await import('@tensorflow/tfjs-converter')
  const model = (await converter.loadGraphModel(REFINE_URL, {
    fromTFHub: true,
  })) as unknown as GraphModelLike
  return { tf, model }
}

/** 모델을 미리 올려 둔다 — 처음 한 장에서 몇백 ms 를 벌기 위해서다. */
export function warmUpDetector() {
  ready ??= load()
  return ready
}

/**
 * 2단계 모델도 미리 올려 둔다.
 *
 * 🔴 이걸 안 하면 **시작을 누른 뒤에** 내려받기 시작해서 첫 몇 초 동안 관절이
 * 1단계 값(흐릿한 것)으로 나온다. 영상을 고르는 순간부터 받아 두면 시작할
 * 때는 이미 준비돼 있다. 1단계가 먼저 올라간 뒤에 시작한다 — 둘을 동시에
 * 받으면 정작 먼저 필요한 쪽이 늦어진다.
 */
export function warmUpRefine() {
  readyRefine ??= loadRefine()
  return readyRefine
}

/**
 * 관절을 **다시, 더 정확하게** 잰다. 못 하면 `null` — 부를 쪽이 원래 값을 쓴다.
 *
 * 🔴 이 함수는 **따라가는 그 사람에게만** 쓴다. 화면의 모두에게 돌리면 사람
 * 수만큼 모델을 더 돌리게 되는데, 분석하는 사람은 하나다.
 */
export async function refinePose(video: HTMLVideoElement, box: Box): Promise<Point[] | null> {
  const vw = video.videoWidth
  const vh = video.videoHeight
  if (!vw || !vh || box.w <= 0 || box.h <= 0) return null

  readyRefine ??= loadRefine()
  let tf: TF
  let model: GraphModelLike
  try {
    ;({ tf, model } = await readyRefine)
  } catch {
    return null
  }

  // 🔴 **정사각형으로** 자른다. 모델이 정사각 입력을 받으므로, 직사각형을
  // 억지로 늘려 넣으면 사람이 옆으로 퍼져 관절이 어긋난다.
  const side = Math.max(box.w * vw, box.h * vh) * REFINE_PAD
  const sx = (box.x + box.w / 2) * vw - side / 2
  const sy = (box.y + box.h / 2) * vh - side / 2

  refineCanvas ??= document.createElement('canvas')
  refineCanvas.width = REFINE_SIZE
  refineCanvas.height = REFINE_SIZE
  const ctx = refineCanvas.getContext('2d')
  if (!ctx) return null

  // 화면 밖으로 나간 부분은 그릴 것이 없다 — 검게 두고 안쪽만 옮겨 담는다.
  const x0 = Math.max(0, sx)
  const y0 = Math.max(0, sy)
  const x1 = Math.min(vw, sx + side)
  const y1 = Math.min(vh, sy + side)
  if (x1 <= x0 || y1 <= y0) return null
  ctx.fillStyle = '#000'
  ctx.fillRect(0, 0, REFINE_SIZE, REFINE_SIZE)
  ctx.drawImage(
    video,
    x0, y0, x1 - x0, y1 - y0,
    ((x0 - sx) / side) * REFINE_SIZE, ((y0 - sy) / side) * REFINE_SIZE,
    ((x1 - x0) / side) * REFINE_SIZE, ((y1 - y0) / side) * REFINE_SIZE,
  )

  const input = tf.tidy(() =>
    tf.cast(tf.expandDims(tf.browser.fromPixels(refineCanvas!), 0), 'int32'),
  )
  let raw: Float32Array
  const out = model.execute(input)
  try {
    raw = await out.data()
  } finally {
    out.dispose()
    input.dispose()
  }

  // 잘라 낸 상자 기준 0~1 → 다시 **영상 그림 안** 0~1 로.
  const points: Point[] = []
  for (let j = 0; j < 17; j += 1) {
    const p = j * 3
    points.push({
      y: (sy + raw[p] * side) / vh,
      x: (sx + raw[p + 1] * side) / vw,
      score: raw[p + 2],
    })
  }

  // 🔴 **정말 그 사람인가.** 옆 사람을 집어 온 것이면 버린다(위 주석).
  const mx = box.w * REFINE_SLACK
  const my = box.h * REFINE_SLACK
  let seen = 0
  let inside = 0
  for (const p of points) {
    if (p.score < MIN_KP) continue
    seen += 1
    if (
      p.x >= box.x - mx &&
      p.x <= box.x + box.w + mx &&
      p.y >= box.y - my &&
      p.y <= box.y + box.h + my
    ) {
      inside += 1
    }
  }
  if (seen < 5 || inside / seen < REFINE_INSIDE) return null

  return points
}

/**
 * 영상을 입력 크기에 **비율을 지켜** 담고, 남은 여백을 알려 준다.
 *
 * 🔴 여백을 안 돌려주면 좌표가 어긋난다. 모델이 주는 값은 **담은 그림 전체**
 * 기준이라, 위아래에 검은 띠가 있으면 그 띠까지 포함한 좌표다 — 세로 영상일
 * 수록 크게 틀어진다.
 */
function fit(video: HTMLVideoElement) {
  const vw = video.videoWidth
  const vh = video.videoHeight
  const long = Math.max(vw, vh)
  const w = Math.ceil(((IN_LONG * vw) / long) / MULT) * MULT
  const h = Math.ceil(((IN_LONG * vh) / long) / MULT) * MULT

  canvas ??= document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d', { willReadFrequently: false })
  if (!ctx) return null

  const scale = Math.min(w / vw, h / vh)
  const dw = vw * scale
  const dh = vh * scale
  const ox = (w - dw) / 2
  const oy = (h - dh) / 2
  ctx.fillStyle = '#000'
  ctx.fillRect(0, 0, w, h)
  ctx.drawImage(video, ox, oy, dw, dh)

  // 담은 그림 기준 0~1 좌표를 **영상 그림 기준**으로 되돌리는 값들.
  return { canvas, ox: ox / w, oy: oy / h, sx: w / dw, sy: h / dh }
}

/** 한 프레임에서 사람들을 찾는다. 좌표는 **영상 그림 안** 0~1 정규화다. */
export async function detectPeople(video: HTMLVideoElement): Promise<Det[]> {
  const { tf, model } = await warmUpDetector()
  if (!video.videoWidth || !video.videoHeight) return []

  const f = fit(video)
  if (!f) return []

  const input = tf.tidy(() =>
    tf.cast(tf.expandDims(tf.browser.fromPixels(f.canvas), 0), 'int32'),
  )
  let raw: Float32Array
  const out = model.execute(input)
  try {
    raw = await out.data()
  } finally {
    out.dispose()
    input.dispose()
  }

  const dets: Det[] = []
  // 사람 한 명이 56 개 숫자. 상자는 51~54, 점수는 55(위 표).
  for (let i = 0; i + 56 <= raw.length; i += 56) {
    const s = raw[i + 55]
    if (s < MIN_DET) continue
    const y1 = (raw[i + 51] - f.oy) * f.sy
    const x1 = (raw[i + 52] - f.ox) * f.sx
    const y2 = (raw[i + 53] - f.oy) * f.sy
    const x2 = (raw[i + 54] - f.ox) * f.sx
    const box: Box = { x: x1, y: y1, w: x2 - x1, h: y2 - y1 }
    if (box.w <= 0.005 || box.h <= 0.01) continue

    /**
     * 🔴 관절도 같이 담는다 — 지금까지 버리고 있었다. 자리는 `y, x, 점수`
     * 순서이고(상자와 반대다) 상자와 **같은 여백 보정**을 거쳐야 한다.
     */
    const keypoints: Point[] = []
    for (let j = 0; j < 17; j += 1) {
      const p = i + j * 3
      keypoints.push({
        y: (raw[p] - f.oy) * f.sy,
        x: (raw[p + 1] - f.ox) * f.sx,
        score: raw[p + 2],
      })
    }
    dets.push({ box, score: s, keypoints })
  }
  return dets
}
