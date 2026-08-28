import {
  BANDS,
  BURST_COUNT,
  DRY_END,
  DRY_MS,
  HOLD_MS,
  MAX_SHIFT_EM,
  SETTLE_MS,
  TOTAL_MS,
  WET_END,
  WET_MS,
  bandShifts,
  eraseProgress,
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

describe('eraseProgress — 잉크가 역으로 걷힌다', () => {
  it('양 끝은 0과 1이다', () => {
    expect(eraseProgress(0)).toBe(0)
    expect(eraseProgress(1)).toBe(1)
    expect(eraseProgress(-1)).toBe(0)
    expect(eraseProgress(2)).toBe(1)
  })

  it('앞이 빠르다 — 번짐(inkProgress)과 반대로 "확 걷히고" 자락만 남는다', () => {
    // 절반 시점에 이미 3/4가 걷혀 있다.
    expect(eraseProgress(0.5)).toBeCloseTo(0.75, 5)
    expect(eraseProgress(0.5)).toBeGreaterThan(0.5)
  })

  it('단조증가한다 — 걷히다 되돌아오지 않는다', () => {
    const samples = [0, 0.2, 0.4, 0.6, 0.8, 1].map(eraseProgress)
    for (let i = 1; i < samples.length; i++) {
      expect(samples[i]).toBeGreaterThan(samples[i - 1])
    }
  })
})

describe('glitchAmplitudeAt — 흔들리는 때는 세 번뿐이다(앱과 같다)', () => {
  it('버스트 밖에서는 정확히 0 — 사이의 정적이 있어야 터지는 순간이 산다', () => {
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

  it(`인트로 한 판에 정확히 ${BURST_COUNT}번 흔들린다`, () => {
    const steps = Math.floor(TOTAL_MS / HOLD_MS)
    const runs: number[] = []
    let n = 0
    for (let i = 0; i < steps; i++) {
      const a = glitchAmplitudeAt(inkProgress((i * HOLD_MS) / TOTAL_MS))
      if (a > 0) {
        n++
      } else if (n) {
        runs.push(n)
        n = 0
      }
    }
    if (n) runs.push(n)
    expect(runs).toHaveLength(BURST_COUNT)
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

describe('bandShifts', () => {
  it('같은 seed 면 같은 결과다 — 프레임마다 다시 뽑히지 않는다', () => {
    expect(bandShifts(42, 1)).toEqual(bandShifts(42, 1))
    expect(bandShifts(42, 1)).not.toEqual(bandShifts(43, 1))
  })

  it('띠 수만큼 준다', () => {
    expect(bandShifts(1, 1)).toHaveLength(BANDS)
  })

  // 버스트 밖에서 조각내면 조각 경계가 가로줄로 보인다 — GlitchIntro 가
  // "전부 0이면 통짜로" 그리도록, 여기서 정확히 0을 줘야 한다.
  it('진폭이 0이면 전부 0 — 버스트 밖에서는 글자를 자르지 않는다', () => {
    expect(bandShifts(7, 0)).toEqual(new Array(BANDS).fill(0))
  })

  it('진폭에 비례한다 — 최대 어긋남이 MAX_SHIFT_EM 을 넘지 않는다', () => {
    for (let seed = 0; seed < 50; seed++) {
      for (const shift of bandShifts(seed, 1)) {
        expect(Math.abs(shift)).toBeLessThanOrEqual(MAX_SHIFT_EM)
      }
      const half = bandShifts(seed, 0.5)
      const full = bandShifts(seed, 1)
      half.forEach((v, i) => expect(v).toBeCloseTo(full[i] / 2, 10))
    }
  })
})
