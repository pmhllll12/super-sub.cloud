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

  it('직전은 임팩트 앞 0.5초 안에서 무릎이 가장 굽은 프레임이다', () => {
    const r = detectMoments(kickMotion())
    if (!r.ok) throw new Error(r.reason)
    expect(r.moments.before).toBe(14)
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
})
