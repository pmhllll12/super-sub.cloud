/**
 * 따라가기를 **실제 영상으로** 확인하는 도구.
 *
 * 화면에서 눈으로 보고 고치는 것은 한계가 있다 — 어느 프레임에서 누구에게
 * 넘어갔는지, 그때 닮음 점수가 얼마였는지를 봐야 고칠 수 있다. 이 스크립트는
 * 브라우저에서 도는 것과 **같은 모듈**(`personDetector` 의 해석 · `personTrack`)을
 * 써서 영상 한 편을 통째로 돌리고, 프레임마다 무슨 일이 있었는지 표로 찍고
 * 박스를 그려 넣은 그림을 남긴다.
 *
 * ```
 *   node scripts/track-check.ts <영상> --list            프레임 0 의 사람들에 번호를 매겨 그린다
 *   node scripts/track-check.ts <영상> --pick 2          그 번호로 시작해 끝까지 따라간다
 *   node scripts/track-check.ts <영상> --pick 2 --fps 8  느리면 성기게
 * ```
 */

import { spawnSync } from 'node:child_process'
import { mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import * as tf from '@tensorflow/tfjs-core'
import '@tensorflow/tfjs-backend-cpu'
import { loadGraphModel } from '@tensorflow/tfjs-converter'
import type { Box } from '../src/lib/box'
import { colorHist, histSim } from '../src/lib/appearance'
import { createPersonTracker, snapToDetection, type Det } from '../src/lib/personTrack'
import { smoothStep } from '../src/lib/smoothBox'

const MODEL_URL = 'https://tfhub.dev/google/tfjs-model/movenet/multipose/lightning/1'
const MIN_DET = 0.2

const video = process.env.CLIP ?? ''
const listOnly = process.env.LIST === '1'
const pick = Number(process.env.PICK ?? '0')
const fps = Number(process.env.FPS ?? '10')
const out = join(process.cwd(), '.track-check')

/** ffprobe 로 크기를 읽는다. */
function size(path: string) {
  const r = spawnSync('ffprobe', [
    '-v', 'error', '-select_streams', 'v:0',
    '-show_entries', 'stream=width,height', '-of', 'csv=p=0', path,
  ])
  const [w, h] = r.stdout.toString().trim().split(',').map(Number)
  return { w, h }
}

/** 영상 전체를 **모델 입력 크기의** rgb24 프레임 배열로 뜯는다. */
function frames(path: string, cw: number, ch: number) {
  const r = spawnSync(
    'ffmpeg',
    ['-v', 'error', '-i', path, '-vf', `fps=${fps},scale=${cw}:${ch}`,
     '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
    { maxBuffer: 1 << 30 },
  )
  const buf = r.stdout
  const per = cw * ch * 3
  const list: Buffer[] = []
  for (let i = 0; i + per <= buf.length; i += per) list.push(buf.subarray(i, i + per))
  return list
}

/** rgb24 → 히스토그램이 받는 RGBA. */
function toRgba(rgb: Buffer, w: number, h: number) {
  const data = new Uint8ClampedArray(w * h * 4)
  for (let i = 0, p = 0; i < w * h; i += 1, p += 3) {
    data[i * 4] = rgb[p]
    data[i * 4 + 1] = rgb[p + 1]
    data[i * 4 + 2] = rgb[p + 2]
    data[i * 4 + 3] = 255
  }
  return { data, width: w, height: h }
}

/** 32 의 배수로 올린 입력 크기와, 그 안에서 그림이 차지하는 자리. */
function fitSize(vw: number, vh: number) {
  const long = Math.max(vw, vh)
  const w = Math.ceil(((256 * vw) / long) / 32) * 32
  const h = Math.ceil(((256 * vh) / long) / 32) * 32
  const scale = Math.min(w / vw, h / vh)
  const cw = Math.round(vw * scale)
  const chh = Math.round(vh * scale)
  return { w, h, cw, ch: chh, ox: (w - cw) / 2, oy: (h - chh) / 2 }
}

/** 네모를 그림 위에 그린다(굵기 2). */
function draw(rgb: Buffer, w: number, h: number, box: Box, c: [number, number, number]) {
  const x0 = Math.max(0, Math.round(box.x * w))
  const y0 = Math.max(0, Math.round(box.y * h))
  const x1 = Math.min(w - 1, Math.round((box.x + box.w) * w))
  const y1 = Math.min(h - 1, Math.round((box.y + box.h) * h))
  const put = (x: number, y: number) => {
    if (x < 0 || y < 0 || x >= w || y >= h) return
    const p = (y * w + x) * 3
    rgb[p] = c[0]
    rgb[p + 1] = c[1]
    rgb[p + 2] = c[2]
  }
  for (let t = 0; t < 2; t += 1) {
    for (let x = x0; x <= x1; x += 1) { put(x, y0 + t); put(x, y1 - t) }
    for (let y = y0; y <= y1; y += 1) { put(x0 + t, y); put(x1 - t, y) }
  }
}

/** 숫자를 아주 성기게 찍는다(0~9, 3×5 점). */
const GLYPH: Record<string, string[]> = {
  '0': ['111', '101', '101', '101', '111'], '1': ['010', '110', '010', '010', '111'],
  '2': ['111', '001', '111', '100', '111'], '3': ['111', '001', '111', '001', '111'],
  '4': ['101', '101', '111', '001', '001'], '5': ['111', '100', '111', '001', '111'],
  '6': ['111', '100', '111', '101', '111'], '7': ['111', '001', '001', '001', '001'],
  '8': ['111', '101', '111', '101', '111'], '9': ['111', '101', '111', '001', '111'],
}
function label(rgb: Buffer, w: number, h: number, x: number, y: number, text: string) {
  let ox = x
  for (const ch of text) {
    const g = GLYPH[ch]
    if (!g) { ox += 4; continue }
    for (let j = 0; j < 5; j += 1) for (let i = 0; i < 3; i += 1) {
      if (g[j][i] !== '1') continue
      for (let sy = 0; sy < 2; sy += 1) for (let sx = 0; sx < 2; sx += 1) {
        const px = ox + i * 2 + sx
        const py = y + j * 2 + sy
        if (px < 0 || py < 0 || px >= w || py >= h) continue
        const p = (py * w + px) * 3
        rgb[p] = 255; rgb[p + 1] = 255; rgb[p + 2] = 0
      }
    }
    ox += 8
  }
}

function ppm(path: string, rgb: Buffer, w: number, h: number) {
  writeFileSync(path, Buffer.concat([Buffer.from(`P6\n${w} ${h}\n255\n`), rgb]))
}

// ── 본체 ────────────────────────────────────────────────────────────
// 🔴 시험이 아니라 **도구**다. `CLIP=<영상>` 을 줄 때만 돈다.
//   CLIP=clip.mp4 LIST=1 npx vitest run scripts/track-check.test.ts
//   CLIP=clip.mp4 PICK=2 npx vitest run scripts/track-check.test.ts
it.skipIf(!video)('따라가기를 실제 영상으로 확인한다', async () => {
await tf.setBackend('cpu')
await tf.ready()
const model = await loadGraphModel(MODEL_URL, { fromTFHub: true })

const { w: vw, h: vh } = size(video)
const fit = fitSize(vw, vh)
console.log(`영상 ${vw}×${vh} → 입력 ${fit.w}×${fit.h}, 그림 ${fit.cw}×${fit.ch} (여백 ${fit.ox},${fit.oy})`)

const all = frames(video, fit.cw, fit.ch)
console.log(`프레임 ${all.length}장 (${fps}fps)`)

rmSync(out, { recursive: true, force: true })
mkdirSync(out, { recursive: true })

/** 한 장에서 사람들을 찾는다 — personDetector 와 같은 해석이다. */
function detect(rgb: Buffer): Det[] {
  // 입력 크기로 여백을 채워 넣는다.
  const padded = Buffer.alloc(fit.w * fit.h * 3)
  for (let y = 0; y < fit.ch; y += 1) {
    rgb.copy(padded, ((y + fit.oy) * fit.w + fit.ox) * 3, y * fit.cw * 3, (y + 1) * fit.cw * 3)
  }
  const input = tf.tidy(() =>
    tf.cast(tf.expandDims(tf.tensor3d(new Uint8Array(padded), [fit.h, fit.w, 3], 'int32'), 0), 'int32'),
  )
  const res = model.execute(input) as tf.Tensor
  const raw = res.dataSync() as Float32Array
  res.dispose()
  input.dispose()

  const dets: Det[] = []
  const sx = fit.w / fit.cw
  const sy = fit.h / fit.ch
  const ox = fit.ox / fit.w
  const oy = fit.oy / fit.h
  for (let i = 0; i + 56 <= raw.length; i += 56) {
    const s = raw[i + 55]
    if (s < MIN_DET) continue
    const y1 = (raw[i + 51] - oy) * sy
    const x1 = (raw[i + 52] - ox) * sx
    const y2 = (raw[i + 53] - oy) * sy
    const x2 = (raw[i + 54] - ox) * sx
    const box: Box = { x: x1, y: y1, w: x2 - x1, h: y2 - y1 }
    if (box.w <= 0.005 || box.h <= 0.01) continue
    dets.push({ box, score: s })
  }
  return dets
}

if (listOnly) {
  const rgb = Buffer.from(all[0])
  const dets = detect(all[0])
  dets.forEach((d, i) => {
    draw(rgb, fit.cw, fit.ch, d.box, [0, 255, 0])
    label(rgb, fit.cw, fit.ch, Math.round(d.box.x * fit.cw) + 2, Math.round(d.box.y * fit.ch) + 2, String(i))
    console.log(`  ${i}: x=${d.box.x.toFixed(3)} y=${d.box.y.toFixed(3)} w=${d.box.w.toFixed(3)} h=${d.box.h.toFixed(3)} 점수=${d.score.toFixed(2)}`)
  })
  ppm(join(out, 'list.ppm'), rgb, fit.cw, fit.ch)
  spawnSync('ffmpeg', ['-v', 'error', '-y', '-i', join(out, 'list.ppm'), '-vf', 'scale=1024:-1', join(out, 'list.png')])
  console.log(`→ ${join(out, 'list.png')}`)
  return
}

const first = detect(all[0])
if (!first[pick]) throw new Error(`프레임 0 에 ${pick}번 사람이 없다 (검출 ${first.length}명)`)
const start = first[pick].box
const anchorFrame = toRgba(all[0], fit.cw, fit.ch)
const tracker = createPersonTracker(anchorFrame, snapToDetection(start, first) ?? start)
const anchor = colorHist(anchorFrame, start)

/**
 * 🔴 **화면에 실제로 보이는 것**은 검출 결과가 아니라 그걸 눅인 값이다
 * (`smoothBox`). 도구가 그 경로를 안 재고 있어서 "로직은 멀쩡한데 화면은
 * 이상하다" 를 못 잡았다 — 프레임 사이를 60fps 로 쪼개 그대로 흉내 낸다.
 */
let shown: Box | null = null
const SUB = Math.max(1, Math.round(60 / fps))

console.log('\n프레임  시각   사람  고른곳   닮음  놓침  박스중심  보이는중심  뒤처짐')
let switches = 0
let prev = -1
for (let n = 0; n < all.length; n += 1) {
  const rgb = Buffer.from(all[n])
  const dets = detect(all[n])
  const frame = toRgba(all[n], fit.cw, fit.ch)
  const r = n === 0 ? { box: tracker.box, lost: false, sim: 1 } : tracker.step(dets, frame)

  // 지금 박스가 어느 검출을 가리키나 — 그리고 앵커와 가장 닮은 사람은 누구인가.
  let at = -1
  let bestSim = -1
  let bestIdx = -1
  dets.forEach((d, i) => {
    const s = histSim(anchor, colorHist(frame, d.box))
    if (s > bestSim) { bestSim = s; bestIdx = i }
    if (Math.abs(d.box.x - r.box.x) < 1e-9 && Math.abs(d.box.y - r.box.y) < 1e-9) at = i
  })
  if (at >= 0 && prev >= 0 && at !== prev) switches += 1
  if (at >= 0) prev = at

  // 화면이 그리는 값 — 60fps 로 눅여 가며 따라온다.
  for (let k = 0; k < SUB; k += 1) {
    shown = shown ? smoothStep(shown, r.box, 1000 / 60) : r.box
  }

  dets.forEach((d, i) => draw(rgb, fit.cw, fit.ch, d.box, i === bestIdx ? [80, 80, 255] : [120, 120, 120]))
  draw(rgb, fit.cw, fit.ch, r.box, r.lost ? [120, 40, 40] : [0, 140, 0])
  if (shown) draw(rgb, fit.cw, fit.ch, shown, r.lost ? [255, 60, 60] : [0, 255, 0])
  label(rgb, fit.cw, fit.ch, 3, 3, String(n))
  ppm(join(out, `f${String(n).padStart(4, '0')}.ppm`), rgb, fit.cw, fit.ch)

  const mark = r.lost ? '놓침' : '    '
  console.log(
    `${String(n).padStart(5)} ${(n / fps).toFixed(1).padStart(5)}s ` +
    `${String(dets.length).padStart(4)} ${String(at).padStart(6)} ` +
    `${(r.sim ?? 0).toFixed(2).padStart(6)} ${mark}  ` +
    `${(r.box.x + r.box.w / 2).toFixed(3)}` +
    `${(shown ? (shown.x + shown.w / 2).toFixed(3) : '-').padStart(11)}` +
    `${(shown ? Math.abs(shown.x + shown.w / 2 - (r.box.x + r.box.w / 2)).toFixed(3) : '-').padStart(8)}` +
    (bestIdx !== at && bestIdx >= 0 ? `   ← 가장닮은건 ${bestIdx}(${bestSim.toFixed(2)})` : ''),
  )
}

console.log(`\n대상이 바뀐 횟수: ${switches}`)
spawnSync('ffmpeg', ['-v', 'error', '-y', '-framerate', String(fps), '-i', join(out, 'f%04d.ppm'),
  '-vf', 'scale=768:-1', '-pix_fmt', 'yuv420p', join(out, 'tracked.mp4')])
spawnSync('ffmpeg', ['-v', 'error', '-y', '-i', join(out, 'f%04d.ppm'),
  '-vf', `select='not(mod(n\\,${Math.max(1, Math.floor(all.length / 24))}))',scale=320:-1,tile=6x4`,
  '-frames:v', '1', join(out, 'sheet.png')])
console.log(`→ ${join(out, 'tracked.mp4')}`)
console.log(`→ ${join(out, 'sheet.png')}`)
}, 1_800_000)
