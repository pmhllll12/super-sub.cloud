import { kneeAngle } from './angles'
import { kickMotion } from './kickFixture'
import { detectMoments, velocity } from './moments'

describe('세 순간', () => {
  it('각속도는 중앙 차분(도/초)이고 양끝은 비운다 — np.gradient 의 가운데와 같다', () => {
    expect(velocity([10, 20, 40, null, 50], 10)).toEqual([null, 150, null, 50, null])
  })

  it('각속도가 더 큰 다리를 차는 다리로, 그 최대 프레임을 임팩트로 잡는다', () => {
    const r = detectMoments(kickMotion())
    expect(r.ok).toBe(true)
    if (!r.ok) return
    expect(r.moments.kickingLeg).toBe('right')
    expect(r.moments.impact).toBe(15)
  })

  it('직전은 임팩트 0.3초 전이다', () => {
    const r = detectMoments(kickMotion())
    if (!r.ok) throw new Error(r.reason)
    // fps 15, impact 15 → 15 - round(0.3*15) = 15 - round(4.5) = 15 - 5 = 10.
    expect(r.moments.before).toBe(10)
  })

  it('그 프레임에 관절이 없으면 가장 가까운 잡힌 프레임을 쓴다(동률이면 이른 쪽)', () => {
    const m = kickMotion()
    m.frames[10]![16] = { ...m.frames[10]![16], score: 0 } // 목표 프레임(10)의 오른 발목만 못 잡음
    const r = detectMoments(m)
    if (!r.ok) throw new Error(r.reason)
    // 9(거리1)·11(거리1) 동률 — 이른 쪽인 9.
    expect(r.moments.before).toBe(9)
  })

  it('+1초는 임팩트 + fps 프레임이다', () => {
    const r = detectMoments(kickMotion())
    if (!r.ok) throw new Error(r.reason)
    expect(r.moments.after).toBe(30)
    expect(r.moments.afterClipped).toBe(false)
  })

  it('영상이 먼저 끝나면 마지막 유효 프레임으로 대신하고 표시한다', () => {
    const r = detectMoments(kickMotion({ frames: 20 }))
    if (!r.ok) throw new Error(r.reason)
    expect(r.moments.after).toBe(19)
    expect(r.moments.afterClipped).toBe(true)
  })

  // 🔴 에이전트 `segment_phases` 와 같은 판단 — 잘린 영상에서 순간을 지어내지 않는다.
  it('임팩트가 유효 구간 경계에서 2프레임 안이면 실패다', () => {
    const r = detectMoments(kickMotion({ impactShift: -14 }))
    expect(r.ok).toBe(false)
  })

  it('차는 발목이 직전→임팩트로 움직인 쪽이 차는 방향이다', () => {
    const right = detectMoments(kickMotion({ dir: 1 }))
    const left = detectMoments(kickMotion({ dir: -1 }))
    if (!right.ok || !left.ok) throw new Error('순간을 못 찾음')
    expect(right.moments.direction).toBe(1)
    expect(left.moments.direction).toBe(-1)
  })

  it('관절을 하나도 못 잡았으면 실패다', () => {
    const m = kickMotion()
    m.frames = m.frames.map(() => null)
    expect(detectMoments(m).ok).toBe(false)
  })

  // 🔴 velocity[i]는 i-1·i+1만 보므로, 그 다리 무릎을 못 잰 프레임도 각속도 최대치가 될 수 있다.
  it('진짜 임팩트 프레임에서 그 다리 무릎을 못 쟀으면 그 프레임은 후보에서 뺀다', () => {
    const m = kickMotion()
    m.frames[15]![14] = { ...m.frames[15]![14], score: 0 } // 15번 프레임의 오른 무릎만 못 잡음
    const r = detectMoments(m)
    if (!r.ok) throw new Error(r.reason)
    expect(r.moments.impact).not.toBe(15)
    const impactKnee = kneeAngle(m.frames[r.moments.impact]!, 'right', m.aspect)
    expect(impactKnee).not.toBeNull()
  })
})
