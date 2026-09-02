import type { Box } from './box'
import { smoothStep } from './smoothBox'

const a: Box = { x: 0.4, y: 0.3, w: 0.1, h: 0.4 }

describe('상자 눅이기', () => {
  it('목표 쪽으로 다가가되 한 번에 가지 않는다', () => {
    const b = { ...a, x: a.x + 0.05 }
    const s = smoothStep(a, b, 16)
    expect(s.x).toBeGreaterThan(a.x)
    expect(s.x).toBeLessThan(b.x)
  })

  it('시간이 흐르면 결국 목표에 닿는다', () => {
    const b = { ...a, x: a.x + 0.05 }
    let s = a
    for (let i = 0; i < 60; i += 1) s = smoothStep(s, b, 16)
    expect(s.x).toBeCloseTo(b.x, 3)
  })

  // 🔴 프레임마다 같은 비율로 섞으면 느린 기기에서 더 느리게 따라온다.
  it('프레임률이 달라도 같은 시간에 같은 만큼 온다', () => {
    const b = { ...a, x: a.x + 0.1 }
    let fast = a
    for (let i = 0; i < 12; i += 1) fast = smoothStep(fast, b, 8)
    let slow = a
    for (let i = 0; i < 3; i += 1) slow = smoothStep(slow, b, 32)
    expect(fast.x).toBeCloseTo(slow.x, 2)
  })

  // 🔴 크기 흔들림은 대부분 검출 잡음이다 — 자리보다 훨씬 천천히 따라가야
  // 네모가 숨쉬듯 벌렁거리지 않는다.
  it('크기는 자리보다 훨씬 천천히 따라간다', () => {
    const b = { x: a.x + 0.02, y: a.y, w: a.w * 1.5, h: a.h * 1.5 }
    const s = smoothStep(a, b, 16)
    const posGone = (s.x + s.w / 2 - (a.x + a.w / 2)) / (b.x + b.w / 2 - (a.x + a.w / 2))
    const sizeGone = (s.w - a.w) / (b.w - a.w)
    expect(sizeGone).toBeLessThan(posGone / 3)
  })

  // 🔴 다른 사람으로 옮겨 갈 때 부드럽게 미끄러지면 빈 코트를 가로질러
  // 날아가는 것으로 보인다 — 부드러운 게 아니라 틀린 그림이다.
  it('멀리 건너뛸 때는 눅이지 않고 바로 붙는다', () => {
    // 자기 키의 1.25 배 — 사람이 한 프레임에 갈 수 있는 거리가 아니다.
    const far = { ...a, x: 0.9 }
    expect(smoothStep(a, far, 16)).toEqual(far)
  })

  it('한 프레임이 아주 길어도 튀지 않는다', () => {
    const b = { ...a, x: a.x + 0.05 }
    const s = smoothStep(a, b, 5000)
    expect(s.x).toBeLessThanOrEqual(b.x)
  })
})
