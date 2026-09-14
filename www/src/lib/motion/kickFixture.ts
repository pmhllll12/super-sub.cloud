/**
 * 시험용 가짜 슈팅 동작 — **오른발**로 차는 사람을 옆에서 본 관절. `aspect: 1` 이라 좌표가
 * 곧 비율이다.
 *
 * 무릎각(엉덩이–무릎–발목)만 바꿔 동작을 만든다: 서 있다가(170) 뒤로 접고(90, 14번)
 * 빠르게 편다(120 → 165 → 175). 중앙 차분 각속도는 15번이 최대다.
 */
import type { Point } from '@/lib/pose'
import type { Motion } from './types'

const P = (x: number, y: number, score = 0.9): Point => ({ x, y, score })

export const RIGHT_KNEE: readonly number[] = [
  170, 170, 170, 170, 170, 170, 170, 170, 170, 170, // 0~9
  150, 130, 110, 95, 90, // 10~14 — 뒤로 접는다
  120, 165, 175, // 15~17 — 편다(15 가 각속도 최대)
  ...Array.from({ length: 28 }, () => 175), // 18~45
]

export function posture({
  rightKnee,
  leftKnee = 160,
  dir = 1,
  lean = 0,
  hipX = 0.5,
}: {
  rightKnee: number
  leftKnee?: number
  dir?: 1 | -1
  lean?: number
  hipX?: number
}): Point[] {
  const pose: Point[] = Array.from({ length: 17 }, () => P(0, 0, 0))
  const hipY = 0.5
  const L = 0.1
  const lx = hipX - 0.01
  const rx = hipX + 0.01
  pose[0] = P(hipX, hipY - 0.4)
  pose[5] = P(lx + lean, hipY - 0.3)
  pose[6] = P(rx + lean, hipY - 0.3)
  pose[11] = P(lx, hipY)
  pose[12] = P(rx, hipY)
  // 허벅지는 곧게 아래로, 정강이는 무릎각만큼 뒤(차는 방향의 반대)로 접힌다.
  const leg = (hx: number, knee: number): [Point, Point] => {
    const bend = ((180 - knee) * Math.PI) / 180
    return [P(hx, hipY + L), P(hx - dir * Math.sin(bend) * L, hipY + L + Math.cos(bend) * L)]
  }
  ;[pose[13], pose[15]] = leg(lx, leftKnee)
  ;[pose[14], pose[16]] = leg(rx, rightKnee)
  return pose
}

/** `impactShift` 만큼 동작을 뒤로 민다(음수면 앞으로 — 잘린 영상 흉내). */
export function kickMotion({
  dir = 1,
  fps = 15,
  frames = 46,
  impactShift = 0,
  lean = 0,
}: { dir?: 1 | -1; fps?: number; frames?: number; impactShift?: number; lean?: number } = {}): Motion {
  const knee = (i: number) =>
    RIGHT_KNEE[Math.min(RIGHT_KNEE.length - 1, Math.max(0, i - impactShift))]
  return {
    fps,
    aspect: 1,
    measuredBy: 'browser',
    frames: Array.from({ length: frames }, (_, i) => posture({ rightKnee: knee(i), dir, lean })),
  }
}
