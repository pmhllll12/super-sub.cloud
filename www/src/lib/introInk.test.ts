import {
  DRY_END,
  DRY_MS,
  SETTLE_MS,
  TOTAL_MS,
  WET_END,
  WET_MS,
  BANDS,
  HOLD_MS,
  MIN_SHIFT_EM,
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

  it('끝에 가서야 잦아든다 — 그전까지는 세기가 살아 있다', () => {
    // 1 - p³ 이던 시절엔 여기서 이미 0.27 까지 떨어져 마지막 1.2초가
    // 통째로 죽었다. 번지는 동안 계속 흔들려야 한다.
    expect(glitchAmplitudeAt(0.9)).toBeGreaterThan(0.4)
    expect(glitchAmplitudeAt(0.5)).toBeGreaterThan(0.9)
    // 그러면서도 끝에서는 뚝 끊기지 않고 잦아들어 있어야 한다.
    expect(glitchAmplitudeAt(0.99)).toBeLessThan(0.1)
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

describe('bandShifts — 흔들림이 규칙적으로 보이면 안 된다', () => {
  /** 인트로 한 판을 그대로 돌려 45ms 칸마다의 띠 어긋남을 모은다. */
  function wholeIntro() {
    const steps = Math.floor(TOTAL_MS / HOLD_MS)
    return Array.from({ length: steps }, (_, i) =>
      bandShifts(i, glitchAmplitudeAt(inkProgress((i * HOLD_MS) / TOTAL_MS))),
    )
  }

  it('같은 seed 면 같은 결과다 — 프레임마다 다시 뽑히지 않는다', () => {
    expect(bandShifts(42, 1)).toEqual(bandShifts(42, 1))
    // seed 가 다르면 결과도 갈린다 — 이웃한 두 seed 가 나란히 "정지"일 수도
    // 있으니(대부분의 순간이 정지다) 낱개가 아니라 무리로 본다.
    const distinct = new Set(
      Array.from({ length: 50 }, (_, i) => JSON.stringify(bandShifts(i, 1))),
    )
    expect(distinct.size).toBeGreaterThan(10)
  })

  it('진폭이 0이면 전부 0 — 번지기 전과 다 번진 뒤는 완전히 정지다', () => {
    expect(bandShifts(7, 0)).toEqual(new Array(BANDS).fill(0))
  })

  it('대부분의 순간은 정지해 있다 — 쉬지 않고 떨면 글리치가 아니라 진동이다', () => {
    const frames = wholeIntro()
    const still = frames.filter((f) => f.every((s) => s === 0)).length
    expect(still / frames.length).toBeGreaterThan(0.5)
  })

  it('터질 때도 일부 띠만 움직인다 — 전부 움직이면 화면이 떠는 것으로 보인다', () => {
    const moving = wholeIntro()
      .map((f) => f.filter((s) => s !== 0).length)
      .filter((n) => n > 0)
    const average = moving.reduce((a, b) => a + b, 0) / moving.length
    expect(average).toBeGreaterThan(1)
    expect(average).toBeLessThan(BANDS - 1)
  })

  it('터짐과 정적의 길이가 제각각이다 — 한 박자로 반복되면 기계처럼 보인다', () => {
    const active = wholeIntro().map((f) => f.some((s) => s !== 0))
    const runs: number[] = []
    let n = 1
    for (let i = 1; i < active.length; i++) {
      if (active[i] === active[i - 1]) {
        n++
      } else {
        runs.push(n)
        n = 1
      }
    }
    runs.push(n)
    expect(new Set(runs).size).toBeGreaterThan(2)
  })

  // 눈에 안 보일 만큼 작게 어긋나면 글자만 조각나고 어긋남은 안 보인다 —
  // 조각 경계가 가로줄로 드러난다(GlitchIntro 가 "전부 0이면 통짜로" 그린다).
  it('눈에 안 보일 만큼 작게 어긋나지 않는다 — 그런 건 0으로 친다', () => {
    const tiny = wholeIntro()
      .flat()
      .filter((s) => s !== 0 && Math.abs(s) < MIN_SHIFT_EM)
    expect(tiny).toEqual([])
  })

  it('크기가 한쪽으로 쏠린다 — 대부분 작고 가끔 크다', () => {
    const sizes = wholeIntro()
      .flat()
      .filter((s) => s !== 0)
      .map(Math.abs)
      .sort((a, b) => a - b)
    const peak = sizes[sizes.length - 1]
    const median = sizes[Math.floor(sizes.length / 2)]
    // 균등분포라면 중앙값이 정점의 절반쯤이고 절반이 그 위에 있다.
    // `r³` 은 아래쪽으로 쏠린다 — 다만 MIN_SHIFT_EM 아래를 잘라내므로
    // (그 값들은 아예 0이 된다) 남은 분포의 쏠림은 그만큼 완만해진다.
    expect(median).toBeLessThan(peak * 0.45)
    expect(sizes.filter((s) => s < peak / 2).length / sizes.length).toBeGreaterThan(0.55)
  })

  it('번지는 내내 흔들린다 — 앞뒤 어느 한쪽으로 몰려 있지 않다', () => {
    const frames = wholeIntro()
    // 잉크가 번지는 구간(민트만 보이는 앞과 머무는 뒤를 뺀 가운데)을 반으로 갈라 본다.
    const wet = frames.filter((_, i) => {
      const p = inkProgress((i * HOLD_MS) / TOTAL_MS)
      return p > 0 && p < 1
    })
    const half = Math.floor(wet.length / 2)
    const count = (a: number[][]) => a.filter((f) => f.some((s) => s !== 0)).length
    expect(count(wet.slice(0, half))).toBeGreaterThan(0)
    expect(count(wet.slice(half))).toBeGreaterThan(0)
  })
})
