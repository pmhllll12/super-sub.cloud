/**
 * 관절 각도 — 🔴 **가로 좌표에 `aspect` 를 곱해** 화면 비율을 되돌린 뒤 잰다.
 * 항목 이름은 루브릭 그대로(`types.ts` 의 `METRIC_LABEL`).
 */
import { MIN_KP, type Point } from '@/lib/pose'
import { METRIC_LABEL, type Leg, type MetricId, type MetricRow, type MomentKey, type Moments, type Motion } from './types'

/** COCO 17점 중 여기서 쓰는 자리. */
export const KP = {
  lShoulder: 5,
  rShoulder: 6,
  lHip: 11,
  rHip: 12,
  lKnee: 13,
  rKnee: 14,
  lAnkle: 15,
  rAnkle: 16,
} as const

export const seen = (p: Point | null | undefined): p is Point => !!p && p.score >= MIN_KP

export function legOf(leg: Leg) {
  return leg === 'left'
    ? { hip: KP.lHip, knee: KP.lKnee, ankle: KP.lAnkle }
    : { hip: KP.rHip, knee: KP.rKnee, ankle: KP.rAnkle }
}

export const otherLeg = (leg: Leg): Leg => (leg === 'left' ? 'right' : 'left')

export function mid(a: Point | null | undefined, b: Point | null | undefined): Point | null {
  if (!seen(a) || !seen(b)) return null
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, score: Math.min(a.score, b.score) }
}

/** b 에서 잰 a–b–c 각(도, 0~180). */
export function jointAngle(
  a: Point | null | undefined,
  b: Point | null | undefined,
  c: Point | null | undefined,
  aspect: number,
): number | null {
  if (!seen(a) || !seen(b) || !seen(c)) return null
  const ux = (a.x - b.x) * aspect
  const uy = a.y - b.y
  const vx = (c.x - b.x) * aspect
  const vy = c.y - b.y
  const nu = Math.hypot(ux, uy)
  const nv = Math.hypot(vx, vy)
  if (nu === 0 || nv === 0) return null
  const cos = Math.max(-1, Math.min(1, (ux * vx + uy * vy) / (nu * nv)))
  return (Math.acos(cos) * 180) / Math.PI
}

export function kneeAngle(pose: Point[], leg: Leg, aspect: number): number | null {
  const j = legOf(leg)
  return jointAngle(pose[j.hip], pose[j.knee], pose[j.ankle], aspect)
}

/** 골반 중점 → 어깨 중점 선이 수직에서 **차는 방향으로** 넘어간 각. 뒤로면 음수. */
export function trunkLean(pose: Point[], direction: 1 | -1, aspect: number): number | null {
  const s = mid(pose[KP.lShoulder], pose[KP.rShoulder])
  const h = mid(pose[KP.lHip], pose[KP.rHip])
  if (!s || !h) return null
  const dx = (s.x - h.x) * aspect * direction
  const up = h.y - s.y
  if (up === 0 && dx === 0) return null
  return (Math.atan2(dx, up) * 180) / Math.PI
}

/** 차는 다리 엉덩이 굴곡 — 몸통 선과 허벅지 선이 곧게 이어지면 0, 다리를 앞으로 들수록 커진다. */
export function hipFlexion(pose: Point[], leg: Leg, aspect: number): number | null {
  const s = mid(pose[KP.lShoulder], pose[KP.rShoulder])
  const j = legOf(leg)
  const a = jointAngle(s, pose[j.hip], pose[j.knee], aspect)
  return a === null ? null : 180 - a
}

/** 한 사람의 한 순간 — 각도를 재는 데 필요한 전부. */
export type Side = { pose: Point[]; kickingLeg: Leg; direction: 1 | -1; aspect: number }

export function sideAt(motion: Motion, moments: Moments, key: MomentKey): Side | null {
  const pose = motion.frames[moments[key]]
  if (!pose) return null
  return { pose, kickingLeg: moments.kickingLeg, direction: moments.direction, aspect: motion.aspect }
}

export const METRICS_AT: Record<MomentKey, readonly MetricId[]> = {
  before: ['plant_knee_flexion', 'swing_knee_extension', 'trunk_lean'],
  impact: ['plant_knee_flexion', 'swing_knee_extension', 'trunk_lean'],
  after: ['trunk_lean', 'follow_through'],
}

function valueOf(id: MetricId, s: Side): number | null {
  switch (id) {
    case 'plant_knee_flexion':
      return kneeAngle(s.pose, otherLeg(s.kickingLeg), s.aspect)
    case 'swing_knee_extension':
      return kneeAngle(s.pose, s.kickingLeg, s.aspect)
    case 'trunk_lean':
      return trunkLean(s.pose, s.direction, s.aspect)
    case 'follow_through':
      return hipFlexion(s.pose, s.kickingLeg, s.aspect)
  }
}

/** 두 사람 다 잰 항목만 행으로 낸다 — 한쪽이 비면 비교가 아니다. */
export function metricsAt(key: MomentKey, player: Side, user: Side): MetricRow[] {
  const rows: MetricRow[] = []
  for (const id of METRICS_AT[key]) {
    const a = valueOf(id, player)
    const b = valueOf(id, user)
    if (a === null || b === null) continue
    rows.push({ id, label: METRIC_LABEL[id], player: Math.round(a), user: Math.round(b), unit: '°' })
  }
  return rows
}
