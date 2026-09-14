/**
 * 두 뼈대를 겹치는 셈 — 🔴 **골반 중점 원점 · 몸통 길이 1.** 키 · 카메라 거리를 지우고
 * 자세 차이만 남긴다. 가로 좌표에는 `aspect` 를 곱해 화면 비율을 되돌린다.
 */
import { EDGES, type Point } from '@/lib/pose'
import { KP, mid, seen } from './angles'
import type { Moments } from './types'

export function normalizePose(pose: Point[], aspect: number, flip: boolean): (Point | null)[] | null {
  const s = mid(pose[KP.lShoulder], pose[KP.rShoulder])
  const h = mid(pose[KP.lHip], pose[KP.rHip])
  if (!s || !h) return null
  const torso = Math.hypot((s.x - h.x) * aspect, s.y - h.y)
  if (torso === 0) return null
  const sign = flip ? -1 : 1
  return pose.map((p) =>
    seen(p) ? { x: (sign * (p.x - h.x) * aspect) / torso, y: (p.y - h.y) / torso, score: p.score } : null,
  )
}

/**
 * 🔴 **차는 방향이 다를 때만 뒤집는다.** 차는 발만 다를 때 뒤집으면 방향이 오히려
 * 갈린다. 판별이 틀릴 수 있어 화면에 되돌리는 토글을 둔다.
 */
export function shouldMirror(player: Moments, user: Moments): boolean {
  return player.direction !== user.direction
}

/** 정규화 좌표 → SVG 격자(0~size). 몸통 1 = size/3.6, 골반은 가운데보다 조금 위. */
export function skeletonPath(points: (Point | null)[], size = 1000): { bones: string; joints: string } {
  const unit = size / 3.6
  const ox = size / 2
  const oy = size * 0.42
  const at = (i: number) => {
    const p = points[i]
    return p ? `${(ox + p.x * unit).toFixed(1)} ${(oy + p.y * unit).toFixed(1)}` : null
  }
  let bones = ''
  for (const [a, b] of EDGES) {
    const pa = at(a)
    const pb = at(b)
    if (pa && pb) bones += `M${pa}L${pb}`
  }
  let joints = ''
  for (let i = 0; i < points.length; i += 1) {
    const q = at(i)
    if (q) joints += `M${q}L${q}`
  }
  return { bones, joints }
}
