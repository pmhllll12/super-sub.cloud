import { DRY_END, WET_END, inkProgress, glitchAmplitudeAt } from './introInk'

describe('inkProgress', () => {
  it('dryEnd 전(0 포함)에는 0', () => {
    expect(inkProgress(0)).toBe(0)
    expect(inkProgress(DRY_END / 2)).toBe(0)
    expect(inkProgress(DRY_END)).toBe(0)
  })

  it('wetEnd 이후(1 포함)에는 1', () => {
    expect(inkProgress(WET_END)).toBe(1)
    expect(inkProgress((WET_END + 1) / 2)).toBe(1)
    expect(inkProgress(1)).toBe(1)
  })

  it('선형이 아니다 — 번짐 구간 중간 지점이 0.5가 아니라 0.65다', () => {
    const mid = DRY_END + (WET_END - DRY_END) / 2
    expect(inkProgress(mid)).not.toBeCloseTo(0.5, 5)
    expect(inkProgress(mid)).toBeCloseTo(0.65, 5)
  })
})

describe('glitchAmplitudeAt', () => {
  it('버스트 밖에서는 정확히 0', () => {
    expect(glitchAmplitudeAt(0)).toBe(0)
    expect(glitchAmplitudeAt(0.5)).toBe(0)
    expect(glitchAmplitudeAt(0.72)).toBe(0) // 1버스트 끝(0.71)과 2버스트 시작(0.76) 사이
    expect(glitchAmplitudeAt(0.84)).toBe(0) // 2버스트 끝(0.83)과 3버스트 시작(0.88) 사이
    expect(glitchAmplitudeAt(0.95)).toBe(0) // 3버스트(0.93) 이후
    expect(glitchAmplitudeAt(1)).toBe(0)
  })

  it('버스트 시작 지점에서는 그 버스트의 세기 그대로다', () => {
    expect(glitchAmplitudeAt(0.62)).toBeCloseTo(1.0, 5)
    expect(glitchAmplitudeAt(0.76)).toBeCloseTo(0.72, 5)
    expect(glitchAmplitudeAt(0.88)).toBeCloseTo(0.4, 5)
  })

  it('버스트 안에서 뒤로 갈수록 진폭이 작아진다', () => {
    const early = glitchAmplitudeAt(0.63)
    const mid = glitchAmplitudeAt(0.665)
    const late = glitchAmplitudeAt(0.7)
    expect(early).toBeGreaterThan(mid)
    expect(mid).toBeGreaterThan(late)
  })

  it('버스트 끝(end)은 포함하지 않는다 — 다음 정적 구간이 즉시 0이다', () => {
    expect(glitchAmplitudeAt(0.71)).toBe(0)
    expect(glitchAmplitudeAt(0.83)).toBe(0)
    expect(glitchAmplitudeAt(0.93)).toBe(0)
  })
})
