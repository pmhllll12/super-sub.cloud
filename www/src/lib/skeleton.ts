/**
 * 뼈대의 **모양** — 격자 좌표의 관절 17개(COCO) → 그릴 `d` 셋.
 *
 * 영상 위에 겹치는 뼈대(`lib/poseDraw.ts` — 내 영상 · 선수 영상)와 세 순간 카드
 * (`lib/motion/align.ts`)가 같은 모양을 쓴다. 두 벌로 두면 한쪽만 다듬어진다.
 *
 * 다듬은 것(사용자 요청, 2026-09-15 — 「더 세련되게」):
 * - **머리는 원 하나.** 얼굴 점 다섯(코 · 눈 · 귀)이 흰 점 뭉치로 보였다.
 * - **몸통은 척추 한 줄.** 어깨 가운데 → 골반 가운데. 옆선 둘은 척추를 못 그을 때만.
 * - **관절 고리는 몸의 마디 열둘만**(어깨 · 팔꿈치 · 손목 · 골반 · 무릎 · 발목).
 * - **차는 다리는 따로 모은다**(`kick`) — 굵게 그리는 것은 CSS 가 한다.
 *
 * 🔴 **값은 하나도 바꾸지 않는다.** 모양만 바뀐다 — 각도 · 순간 · 요약은 관절 값
 * 그대로를 쓴다. 발끝처럼 **없는 관절을 지어내지 않는다**(MoveNet · ViTPose 모두
 * 발목까지다).
 */
import { MIN_KP, type Point } from './pose'
import type { Leg } from './motion/types'

/** 격자 좌표의 관절. 안 보이면(`null`) 잇지도 찍지도 않는다. */
export type GridPoint = { x: number; y: number } | null

const NOSE = 0
const L_EAR = 3
const R_EAR = 4
const L_SHOULDER = 5
const R_SHOULDER = 6
const L_HIP = 11
const R_HIP = 12

const ARMS: readonly [number, number][] = [
  [5, 7], [7, 9],
  [6, 8], [8, 10],
]
const LEGS: Record<Leg, readonly [number, number][]> = {
  left: [[11, 13], [13, 15]],
  right: [[12, 14], [14, 16]],
}
/** 관절 고리를 찍는 마디 — 어깨부터 발목까지. 얼굴(0~4)은 머리 원이 대신한다. */
const BODY_JOINTS = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]

/**
 * 머리 반지름 — **몸통 길이**(어깨 가운데 ↔ 골반 가운데)의 몇 배(머리 키 ≈ 몸통 × 0.45).
 *
 * 🔴 귀 사이 · 어깨 폭으로 재지 않는다. 옆으로 선 자세(차는 순간이 대개 그렇다)에서는
 * 두 어깨 · 두 귀가 겹쳐 폭이 0 에 가깝고 **머리가 사라졌다**(카드 렌더로 확인). 몸통
 * 길이는 몸이 어느 쪽을 보든 거의 그대로다.
 */
const HEAD_BY_TORSO = 0.22
/** 몸통을 못 재면 — 어깨 폭의 몇 배(머리 폭 ≈ 어깨 폭 × 0.6). */
const HEAD_BY_SHOULDERS = 0.3

const n = (v: number) => v.toFixed(1)

/** 영상 좌표의 관절(점수 포함) → 격자 좌표. 점수가 모자라면 `null`. */
export function toGrid(pose: Point[], map: (p: Point) => { x: number; y: number }): GridPoint[] {
  return pose.map((p) => (p && p.score >= MIN_KP ? map(p) : null))
}

export function skeletonShapes(
  pts: GridPoint[],
  {
    kickingLeg = null,
    sx = 1,
    sy = 1,
  }: {
    /** 차는 다리. 모르면(`null`) 두 다리 다 `bones` 에 둔다. */
    kickingLeg?: Leg | null
    /**
     * 격자 한 칸이 화면에서 가로 · 세로 몇 px 인가. 🔴 겹치는 판은 격자를 상자에
     * **늘려** 맞추므로(`preserveAspectRatio="none"`) 둘이 다르다 — 머리 원이 화면에서
     * 원으로 보이게 반지름을 가로 · 세로 따로 되돌린다.
     */
    sx?: number
    sy?: number
  } = {},
): { bones: string; kick: string; joints: string } {
  const at = (i: number) => pts[i] ?? null
  const seg = (a: { x: number; y: number }, b: { x: number; y: number }) =>
    `M${n(a.x)} ${n(a.y)}L${n(b.x)} ${n(b.y)}`
  const edge = (a: number, b: number) => {
    const pa = at(a)
    const pb = at(b)
    return pa && pb ? seg(pa, pb) : ''
  }
  const mid = (a: number, b: number) => {
    const pa = at(a)
    const pb = at(b)
    return pa && pb ? { x: (pa.x + pb.x) / 2, y: (pa.y + pb.y) / 2 } : null
  }
  /** 두 점의 **화면** 거리(px). */
  const dist = (a: { x: number; y: number }, b: { x: number; y: number }) =>
    Math.hypot((a.x - b.x) * sx, (a.y - b.y) * sy)

  let bones = ''
  let kick = ''

  for (const [a, b] of ARMS) bones += edge(a, b)
  bones += edge(L_SHOULDER, R_SHOULDER)
  bones += edge(L_HIP, R_HIP)

  const neckBase = mid(L_SHOULDER, R_SHOULDER)
  const pelvis = mid(L_HIP, R_HIP)
  if (neckBase && pelvis) {
    bones += seg(neckBase, pelvis)
  } else {
    bones += edge(L_SHOULDER, L_HIP)
    bones += edge(R_SHOULDER, R_HIP)
  }

  for (const leg of ['left', 'right'] as const) {
    const d = LEGS[leg].map(([a, b]) => edge(a, b)).join('')
    if (leg === kickingLeg) kick += d
    else bones += d
  }

  /* 머리 중심 — 두 귀 가운데. 옆모습이라 귀가 하나면 **코와 그 귀의 가운데**(코는 얼굴
     앞이고 귀는 머리 뒤쪽이라 둘의 가운데가 머리 중심에 가깝다). 그것도 없으면 보이는 점 하나. */
  const ear = at(L_EAR) ?? at(R_EAR)
  const nose = at(NOSE)
  const center =
    mid(L_EAR, R_EAR) ??
    (ear && nose ? { x: (ear.x + nose.x) / 2, y: (ear.y + nose.y) / 2 } : (nose ?? ear))
  const r =
    neckBase && pelvis
      ? dist(neckBase, pelvis) * HEAD_BY_TORSO
      : at(L_SHOULDER) && at(R_SHOULDER)
        ? dist(at(L_SHOULDER)!, at(R_SHOULDER)!) * HEAD_BY_SHOULDERS
        : 0
  if (center && r >= 1) {
    const rx = r / sx
    const ry = r / sy
    bones += `M${n(center.x - rx)} ${n(center.y)}a${n(rx)} ${n(ry)} 0 1 0 ${n(2 * rx)} 0a${n(rx)} ${n(ry)} 0 1 0 ${n(-2 * rx)} 0`
    // 목 — 어깨 가운데에서 머리 원 가장자리까지. 원 안까지 그으면 머리를 가로지른다.
    if (neckBase) {
      const d = dist(neckBase, center)
      if (d > r) {
        const k = (d - r) / d
        bones += seg(neckBase, {
          x: neckBase.x + (center.x - neckBase.x) * k,
          y: neckBase.y + (center.y - neckBase.y) * k,
        })
      }
    }
  }

  let joints = ''
  for (const i of BODY_JOINTS) {
    const p = at(i)
    if (p) joints += `M${n(p.x)} ${n(p.y)}L${n(p.x)} ${n(p.y)}`
  }

  return { bones, kick, joints }
}
