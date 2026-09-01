import { EDGES, MIN_KP, isSamePerson, smoothPose, type Point } from './pose'

const p = (x: number, y: number, score = 1): Point => ({ x, y, score })

describe('뼈대 규칙', () => {
  it('잇는 자리는 모두 관절 17개 안이다', () => {
    for (const [a, b] of EDGES) {
      expect(a).toBeGreaterThanOrEqual(0)
      expect(b).toBeLessThan(17)
    }
  })

  // 🔴 눈 · 귀(1~4)는 잇지 않는다 — 점이 몰려 있어 선이 뭉개지기만 하고
  // 자세를 보는 데 쓰이지도 않는다.
  it('얼굴은 잇지 않는다', () => {
    for (const [a, b] of EDGES) {
      expect([a, b].some((i) => i >= 1 && i <= 4)).toBe(false)
    }
  })
})

describe('같은 사람인지 묻기', () => {
  const a = [p(0.4, 0.3), p(0.4, 0.5), p(0.5, 0.3), p(0.5, 0.5), p(0.45, 0.7)]

  it('조금 움직인 것은 같은 사람이다', () => {
    expect(isSamePerson(a, a.map((q) => p(q.x + 0.01, q.y)))).toBe(true)
  })

  // 🔴 화면의 다른 사람들은 프레임마다 차례가 뒤바뀔 수 있다 — 남의 자세에서
  // 미끄러져 오면 팔다리가 화면을 가로지른다.
  it('멀리 떨어진 것은 남이다', () => {
    expect(isSamePerson(a, a.map((q) => p(q.x + 0.3, q.y)))).toBe(false)
  })

  it('보이는 관절이 너무 적으면 판단하지 않는다', () => {
    const few = a.map((q, i) => p(q.x, q.y, i < 2 ? 1 : 0))
    expect(isSamePerson(few, few)).toBe(false)
  })
})

describe('관절 눅이기', () => {
  it('목표 쪽으로 다가가되 한 번에 가지 않는다', () => {
    const cur = [p(0.4, 0.4)]
    const next = [p(0.6, 0.4)]
    const s = smoothPose(cur, next, 16)
    expect(s[0].x).toBeGreaterThan(0.4)
    expect(s[0].x).toBeLessThan(0.6)
  })

  // 🔴 상자와 같은 이유 — 프레임률이 달라도 같은 시간에 같은 만큼 와야 한다.
  it('프레임률이 달라도 같은 시간에 같은 만큼 온다', () => {
    let fast = [p(0, 0)]
    for (let i = 0; i < 12; i += 1) fast = smoothPose(fast, [p(1, 0)], 8)
    let slow = [p(0, 0)]
    for (let i = 0; i < 3; i += 1) slow = smoothPose(slow, [p(1, 0)], 32)
    expect(fast[0].x).toBeCloseTo(slow[0].x, 2)
  })

  // 🔴 안 보이던 관절이 다시 잡히면 눅이지 않고 그 자리에 놓는다 — 옛 자리에서
  // 미끄러지면 팔이 허공을 가로지른다.
  it('안 보이다 다시 잡힌 관절은 곧바로 그 자리에 놓는다', () => {
    const hidden = [p(0.1, 0.1, MIN_KP - 0.1)]
    const back = [p(0.8, 0.8, 0.9)]
    expect(smoothPose(hidden, back, 16)[0].x).toBe(0.8)
  })

  it('처음이거나 개수가 다르면 그대로 쓴다', () => {
    const next = [p(0.5, 0.5)]
    expect(smoothPose(null, next, 16)).toBe(next)
    expect(smoothPose([p(0, 0), p(1, 1)], next, 16)).toBe(next)
  })
})
