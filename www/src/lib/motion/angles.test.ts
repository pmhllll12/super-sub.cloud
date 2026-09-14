import { posture, kickMotion } from './kickFixture'
import { hipFlexion, jointAngle, kneeAngle, metricsAt, sideAt, trunkLean } from './angles'

describe('각도', () => {
  it('무릎각은 엉덩이–무릎–발목 사이 각이다', () => {
    const pose = posture({ rightKnee: 120 })
    expect(kneeAngle(pose, 'right', 1)).toBeCloseTo(120, 5)
    expect(kneeAngle(pose, 'left', 1)).toBeCloseTo(160, 5)
  })

  // 🔴 좌표가 가로 · 세로 따로 0~1 이라, 16:9 영상에서 비율을 안 되돌리면 각이 비뚤어진다.
  it('가로 좌표에 화면 비율을 곱해 잰다', () => {
    const a = { x: 0, y: 0, score: 1 }
    const b = { x: 0, y: 0.1, score: 1 }
    const c = { x: 0.1, y: 0.1, score: 1 }
    expect(jointAngle(a, b, c, 1)).toBeCloseTo(90, 5)
    expect(jointAngle(a, b, c, 16 / 9)).toBeCloseTo(90, 5)
    const d = { x: 0.1, y: 0.2, score: 1 }
    expect(jointAngle(a, b, d, 1)).toBeCloseTo(135, 5)
    expect(jointAngle(a, b, d, 16 / 9)).not.toBeCloseTo(135, 0)
  })

  it('점수가 낮은 관절이 끼면 재지 않는다', () => {
    const pose = posture({ rightKnee: 120 })
    pose[16] = { ...pose[16], score: 0.1 }
    expect(kneeAngle(pose, 'right', 1)).toBeNull()
  })

  it('상체 기울기는 차는 방향으로 넘어가면 양수, 뒤로면 음수다', () => {
    const forward = posture({ rightKnee: 170, lean: 0.1 })
    expect(trunkLean(forward, 1, 1)).toBeCloseTo((Math.atan2(0.1, 0.3) * 180) / Math.PI, 5)
    expect(trunkLean(forward, -1, 1)).toBeCloseTo((-Math.atan2(0.1, 0.3) * 180) / Math.PI, 5)
    expect(trunkLean(posture({ rightKnee: 170 }), 1, 1)).toBeCloseTo(0, 5)
  })

  // 가짜 자세는 어깨 중점과 오른쪽 엉덩이가 가로로 0.01 벌어져 있어 정확히 0 은 아니다(≈1.9°).
  it('엉덩이 굴곡은 몸통과 허벅지가 거의 곧으면 0 가깝고, 다리를 앞으로 들면 커진다', () => {
    const straight = hipFlexion(posture({ rightKnee: 170 }), 'right', 1)!
    expect(Math.abs(straight)).toBeLessThan(3)
    const lifted = posture({ rightKnee: 170 })
    lifted[14] = { x: lifted[12].x + 0.1, y: lifted[12].y, score: 0.9 } // 허벅지를 앞으로 수평
    expect(hipFlexion(lifted, 'right', 1)!).toBeGreaterThan(80)
  })

  it('순간마다 정해진 항목만, 반올림해서 낸다', () => {
    const m = kickMotion()
    const moments = { kickingLeg: 'right' as const, direction: 1 as const, before: 14, impact: 15, after: 30, afterClipped: false }
    const player = sideAt(m, moments, 'impact')!
    const user = sideAt(kickMotion({ lean: 0.05 }), moments, 'impact')!
    const rows = metricsAt('impact', player, user)
    expect(rows.map((r) => r.id)).toEqual(['plant_knee_flexion', 'swing_knee_extension', 'trunk_lean'])
    expect(rows[0]).toMatchObject({ label: '디딤발 무릎 굽히기', player: 160, user: 160, unit: '°' })
    expect(rows[1]).toMatchObject({ player: 120, user: 120 })
    expect(rows[2].player).toBe(0)
    expect(rows[2].user).toBe(Math.round((Math.atan2(0.05, 0.3) * 180) / Math.PI))
    expect(metricsAt('after', player, user).map((r) => r.id)).toEqual(['trunk_lean', 'follow_through'])
  })

  it('그 순간 프레임을 못 잡았으면 sideAt 은 null 이다', () => {
    const m = kickMotion()
    m.frames[15] = null
    const moments = { kickingLeg: 'right' as const, direction: 1 as const, before: 14, impact: 15, after: 30, afterClipped: false }
    expect(sideAt(m, moments, 'impact')).toBeNull()
  })
})
