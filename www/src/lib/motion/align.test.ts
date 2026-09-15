import { posture } from './kickFixture'
import { normalizePose, shouldMirror, skeletonPath } from './align'
import type { Moments } from './types'

const base: Moments = { kickingLeg: 'right', direction: 1, before: 14, impact: 15, after: 30, afterClipped: false }

describe('겹치기', () => {
  it('골반 중점이 원점, 몸통 길이가 1 이 된다', () => {
    const n = normalizePose(posture({ rightKnee: 170 }), 1, false)!
    const hip = { x: (n[11]!.x + n[12]!.x) / 2, y: (n[11]!.y + n[12]!.y) / 2 }
    const sh = { x: (n[5]!.x + n[6]!.x) / 2, y: (n[5]!.y + n[6]!.y) / 2 }
    expect(hip.x).toBeCloseTo(0, 6)
    expect(hip.y).toBeCloseTo(0, 6)
    expect(Math.hypot(sh.x - hip.x, sh.y - hip.y)).toBeCloseTo(1, 6)
  })

  // 🔴 서 있는 자리가 달라도 같은 자세면 같은 좌표가 되어야 겹쳐 비교된다.
  it('위치가 달라도 같은 자세면 같은 좌표다', () => {
    const a = normalizePose(posture({ rightKnee: 120, hipX: 0.3 }), 1, false)!
    const b = normalizePose(posture({ rightKnee: 120, hipX: 0.7 }), 1, false)!
    a.forEach((p, i) => {
      if (!p) return
      expect(b[i]!.x).toBeCloseTo(p.x, 6)
      expect(b[i]!.y).toBeCloseTo(p.y, 6)
    })
  })

  it('flip 이면 가로만 뒤집는다', () => {
    const a = normalizePose(posture({ rightKnee: 120 }), 1, false)!
    const b = normalizePose(posture({ rightKnee: 120 }), 1, true)!
    expect(b[16]!.x).toBeCloseTo(-a[16]!.x, 6)
    expect(b[16]!.y).toBeCloseTo(a[16]!.y, 6)
  })

  it('어깨나 골반을 못 잡았으면 null 이다', () => {
    const p = posture({ rightKnee: 120 })
    p[5] = { ...p[5], score: 0 }
    expect(normalizePose(p, 1, false)).toBeNull()
  })

  it('차는 방향이 다를 때만 뒤집는다 — 차는 발만 다르면 안 뒤집는다', () => {
    expect(shouldMirror(base, { ...base, direction: -1 })).toBe(true)
    expect(shouldMirror(base, { ...base, kickingLeg: 'left' })).toBe(false)
    expect(shouldMirror(base, base)).toBe(false)
  })

  it('못 잡은 관절은 선을 긋지 않는다', () => {
    const n = normalizePose(posture({ rightKnee: 120 }), 1, false)!
    const full = skeletonPath(n)
    n[16] = null
    const cut = skeletonPath(n)
    expect(full.bones.length).toBeGreaterThan(cut.bones.length)
    expect(cut.bones).not.toContain('NaN')
  })

  // 🔴 카드 SVG 는 viewBox 밖을 자른다. 머리를 원으로 바꾸자(2026-09-15) 원 윗부분이
  // viewBox 위로 나가 **머리가 잘렸다**. 사람 비율(몸통 1 기준 귀 1.6 위 · 발목 1.85 아래)로 선 자세가
  // 머리 끝부터 발목까지 격자 안에 들어와야 한다.
  it('선 자세의 머리 원과 발목이 카드 격자 안에 들어온다', () => {
    const P = (x: number, y: number) => ({ x, y, score: 0.9 })
    const pose = Array.from({ length: 17 }, () => ({ x: 0, y: 0, score: 0 }))
    pose[0] = P(0.1, -1.55)
    pose[3] = P(-0.05, -1.6)
    pose[4] = P(0.05, -1.6)
    pose[5] = P(-0.02, -1)
    pose[6] = P(0.02, -1)
    pose[11] = P(-0.02, 0)
    pose[12] = P(0.02, 0)
    pose[13] = P(-0.02, 0.95)
    pose[14] = P(0.02, 0.95)
    pose[15] = P(-0.02, 1.85)
    pose[16] = P(0.02, 1.85)
    const size = 1000
    const n = normalizePose(pose, 1, false)!
    const { bones, joints } = skeletonPath(n, size)
    const head = bones.match(/M(-?[\d.]+) (-?[\d.]+)a([\d.]+) ([\d.]+)/)!
    const headTop = Number(head[2]) - Number(head[4])
    // 선 굵기(절반 5)만큼 여유를 둔다.
    expect(headTop).toBeGreaterThanOrEqual(5)
    const ys = [...joints.matchAll(/[ML](-?[\d.]+) (-?[\d.]+)/g)].map((m) => Number(m[2]))
    // 관절 고리(절반 12)만큼 여유를 둔다.
    expect(Math.max(...ys)).toBeLessThanOrEqual(size - 12)
  })
})
