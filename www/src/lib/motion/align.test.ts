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
})
