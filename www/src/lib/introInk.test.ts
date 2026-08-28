import {
  DRY_END,
  DRY_MS,
  SETTLE_MS,
  TOTAL_MS,
  WET_END,
  WET_MS,
  glitchAmplitudeAt,
  inkProgress,
} from './introInk'

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
  it('잉크가 번지기 전에는 0 — 민트 종이만 보이는 동안은 흔들리지 않는다', () => {
    expect(glitchAmplitudeAt(0)).toBe(0)
    expect(glitchAmplitudeAt(-0.1)).toBe(0)
  })

  it('다 번지면 0 — 흔들림이 멎고 워드마크로 굳는다', () => {
    expect(glitchAmplitudeAt(1)).toBe(0)
    expect(glitchAmplitudeAt(1.2)).toBe(0)
  })

  it('번지는 내내 흔들린다 — 중간에 정적 구간이 없다', () => {
    for (const p of [0.01, 0.1, 0.3, 0.5, 0.7, 0.9, 0.99]) {
      expect(glitchAmplitudeAt(p)).toBeGreaterThan(0)
    }
  })

  it('글자가 드러나는 순간 가장 세고, 뒤로 갈수록 잦아든다', () => {
    const samples = [0.01, 0.25, 0.5, 0.75, 0.95].map(glitchAmplitudeAt)
    for (let i = 1; i < samples.length; i++) {
      expect(samples[i]).toBeLessThan(samples[i - 1])
    }
    expect(samples[0]).toBeCloseTo(1, 2)
  })

  it('끝에서 뚝 끊기지 않는다 — 마지막 구간에서 이미 거의 잦아들어 있다', () => {
    expect(glitchAmplitudeAt(0.99)).toBeLessThan(0.05)
    // 반대로 번짐 대부분의 구간에서는 세기가 살아 있어야 한다.
    expect(glitchAmplitudeAt(0.5)).toBeGreaterThan(0.5)
  })
})

describe('구간 길이', () => {
  it('민트만 → 번짐 → 머묾 순서로 이어지고 합이 전체 길이다', () => {
    expect(DRY_MS + WET_MS + SETTLE_MS).toBe(TOTAL_MS)
    expect(DRY_END).toBeCloseTo(DRY_MS / TOTAL_MS, 10)
    expect(WET_END).toBeCloseTo((DRY_MS + WET_MS) / TOTAL_MS, 10)
    expect(DRY_END).toBeLessThan(WET_END)
  })

  it('번짐이 전체의 대부분을 차지한다 — 보러 온 것이 번짐이다', () => {
    expect(WET_MS).toBeGreaterThan(DRY_MS + SETTLE_MS)
  })
})
