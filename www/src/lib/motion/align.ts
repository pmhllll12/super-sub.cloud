/**
 * 두 뼈대를 겹치는 셈 — 🔴 **골반 중점 원점 · 몸통 길이 1.** 키 · 카메라 거리를 지우고
 * 자세 차이만 남긴다. 가로 좌표에는 `aspect` 를 곱해 화면 비율을 되돌린다.
 */
import type { Point } from '@/lib/pose'
import { skeletonShapes } from '@/lib/skeleton'
import { KP, mid, seen } from './angles'
import type { Leg, Moments } from './types'

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

/**
 * 정규화 좌표 → SVG 격자(0~size) 의 뼈 · 차는 다리 · 관절. 몸통 1 = size/3.6, 골반은 가운데보다
 * 조금 위. 모양(머리 원 · 척추 · 관절 고리)은 영상 위 뼈대와 같다(`lib/skeleton.ts`).
 * 카드는 정사각 격자를 늘리지 않으므로 가로 · 세로 px 비가 같다.
 */
export function skeletonPath(
  points: (Point | null)[],
  size = 1000,
  kickingLeg: Leg | null = null,
): { bones: string; kick: string; joints: string } {
  const unit = size / 3.6
  const ox = size / 2
  const oy = size * 0.42
  const pts = points.map((p) => (p ? { x: ox + p.x * unit, y: oy + p.y * unit } : null))
  return skeletonShapes(pts, { kickingLeg })
}
