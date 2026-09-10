import { EMPTY_QUERY, bandsOf, dayKindOf, filterVenues, openAt, parseSpan, slotMatches, type VenueQuery } from './venueFilter'
import type { Venue, VenueSlot } from './venues'

/**
 * 🔴 이 시험이 붙드는 것은 **모양이 아니라 판단**이다. 화면은 바뀌어도
 * 「어느 시간대가 조건에 걸리는가」는 바뀌면 안 된다.
 */
const slot = (over: Partial<VenueSlot> = {}): VenueSlot => ({
  label: '평일 · 주간',
  hours: '09:00~17:00',
  open: true,
  reserveUrl: 'https://yeyak.example/1',
  ...over,
})

const venue = (over: Partial<Venue> = {}): Venue => ({
  id: 'v1',
  name: '난지천 풋살장',
  region: '서울 마포구',
  address: '서울 마포구 · 난지천 풋살장',
  sports: ['soccer'],
  tagline: '유료 대관',
  slots: [slot()],
  ...over,
})

const q = (over: Partial<VenueQuery> = {}): VenueQuery => ({ ...EMPTY_QUERY, ...over })

describe('시각 읽기', () => {
  it('분으로 바꾼다', () => {
    expect(parseSpan('09:30~17:00')).toEqual({ from: 570, to: 1020 })
  })

  /* 🔴 자정을 넘기는 것은 끝이 시작보다 작다 — 그대로 두면 어떤 검사에도
     안 걸려 조용히 사라진다. */
  it('자정을 넘기면 끝에 하루를 더한다', () => {
    expect(parseSpan('22:00~02:00')).toEqual({ from: 1320, to: 1560 })
  })

  it('모양이 아니면 null', () => {
    expect(parseSpan('상시')).toBeNull()
  })
})

describe('때 나누기', () => {
  /* 🔴 **이름이 아니라 숫자로 나눈다.** 89개 중 31개가 이름이 그냥 「이용」이라
     이름으로 나누면 절반이 조용히 빠진다 — 이 시험이 그것을 막는다. */
  it('이름이 「이용」이어도 시각으로 걸린다', () => {
    expect(bandsOf('06:00~22:00')).toEqual(['early', 'day', 'night'])
    expect(slotMatches(slot({ label: '이용', hours: '06:00~22:00' }), q({ bands: ['night'] }))).toBe(
      true,
    )
  })

  it('낮만 여는 곳은 야간에 안 걸린다', () => {
    expect(bandsOf('09:00~17:00')).toEqual(['day'])
  })

  it('이른 아침만 여는 곳', () => {
    expect(bandsOf('06:00~09:00')).toEqual(['early'])
  })
})

describe('요일', () => {
  it('이름에서 읽는다', () => {
    expect(dayKindOf('토/일/공휴일 · 야간')).toBe('weekend')
    expect(dayKindOf('평일 · 주간')).toBe('weekday')
  })

  /* 🔴 **「평일」에도 「일」이 들어 있다.** 주말 낱말을 먼저 찾으면 평일
     시간대가 전부 주말로 읽힌다 — 실제로 그렇게 틀렸다. */
  it('「평일」을 주말로 읽지 않는다', () => {
    expect(dayKindOf('평일')).toBe('weekday')
    expect(dayKindOf('평일 · 야간')).toBe('weekday')
  })

  /* 둘 다 적힌 시간대에서 하나를 골라 버리면 나머지 요일이 조용히 사라진다. */
  it('평일과 주말이 함께 적혔으면 아무 때나로 친다', () => {
    expect(dayKindOf('평일 · 주말')).toBeNull()
  })

  /* ⚠️ 원본이 요일을 안 나누고 파는 시설이 3분의 1이다 — 빼 버리면 목록이
     3분의 1로 줄어든다. 「모른다」는 「아니다」가 아니다. */
  it('안 적힌 시간대는 아무 요일에나 걸린다', () => {
    expect(dayKindOf('이용')).toBeNull()
    expect(slotMatches(slot({ label: '이용' }), q({ days: ['weekend'] }))).toBe(true)
  })
})

describe('그 시각에 열린 곳', () => {
  it('구간 안이면 걸린다', () => {
    expect(openAt('09:00~17:00', '12:30')).toBe(true)
  })

  /* 끝 시각은 안 친다 — 17:00 에 끝나는 곳에서 17:00 에 뛸 수는 없다. */
  it('끝 시각은 안 친다', () => {
    expect(openAt('09:00~17:00', '17:00')).toBe(false)
  })

  it('자정을 넘긴 구간의 새벽도 걸린다', () => {
    expect(openAt('22:00~02:00', '01:00')).toBe(true)
  })
})

describe('조건 여럿', () => {
  /* 🔴 **같은 시간대 하나가 다 만족해야 한다.** 시설 단위로 따로 검사하면
     「주말」은 주간 시간대에서, 「야간」은 평일 시간대에서 걸려 **주말 야간이
     없는 곳이 주말 야간 검색에 나온다.** */
  it('주말과 야간이 서로 다른 시간대에서 걸리면 안 나온다', () => {
    const v = venue({
      slots: [
        slot({ label: '토/일/공휴일 · 주간', hours: '09:00~17:00' }),
        slot({ label: '평일 · 야간', hours: '18:00~22:00' }),
      ],
    })
    expect(filterVenues([v], q({ days: ['weekend'], bands: ['night'] }))).toEqual([])
  })

  it('한 시간대가 둘 다 만족하면 나온다', () => {
    const v = venue({ slots: [slot({ label: '토/일/공휴일 · 야간', hours: '18:00~22:00' })] })
    expect(filterVenues([v], q({ days: ['weekend'], bands: ['night'] }))).toHaveLength(1)
  })
})

describe('정해 둔 경기 조건', () => {
  const prefs = { regions: ['서울 마포구'], times: [{ day: 6, from: '18:00', to: '20:00' }], positions: [] }

  it('지역이 다르면 뺀다', () => {
    const v = venue({ region: '서울 송파구' })
    expect(filterVenues([v], q({ prefs }))).toEqual([])
  })

  /* 토요일 18~20시에 뛰려는데 평일 야간만 여는 곳은 소용이 없다. */
  it('요일이 안 맞는 시간대만 있으면 뺀다', () => {
    const v = venue({ slots: [slot({ label: '평일 · 야간', hours: '18:00~22:00' })] })
    expect(filterVenues([v], q({ prefs }))).toEqual([])
  })

  it('겹치는 시간대가 있으면 나온다', () => {
    const v = venue({ slots: [slot({ label: '토/일/공휴일 · 야간', hours: '17:00~23:00' })] })
    expect(filterVenues([v], q({ prefs }))).toHaveLength(1)
  })

  /* 끝이 닿기만 한 것은 함께 뛸 시간이 0분이다. */
  it('끝이 닿기만 하면 안 겹친 것이다', () => {
    const v = venue({ slots: [slot({ label: '토/일/공휴일', hours: '20:00~23:00' })] })
    expect(filterVenues([v], q({ prefs }))).toEqual([])
  })
})

describe('순서', () => {
  /* 사용자 결정(2026-09-10): 실제로 잡을 수 있는 곳이 위로 온다. */
  it('접수중인 시간대가 많은 곳이 먼저다', () => {
    const few = venue({ id: 'few', slots: [slot(), slot({ open: false })] })
    const many = venue({ id: 'many', slots: [slot(), slot(), slot()] })
    expect(filterVenues([few, many], q()).map((v) => v.id)).toEqual(['many', 'few'])
  })

  it('같은 수끼리는 원본 순서 그대로다', () => {
    const a = venue({ id: 'a' })
    const b = venue({ id: 'b' })
    expect(filterVenues([a, b], q()).map((v) => v.id)).toEqual(['a', 'b'])
  })
})

describe('시설 이름', () => {
  it('일부만 쳐도 걸린다', () => {
    expect(filterVenues([venue()], q({ text: '난지천' }))).toHaveLength(1)
    expect(filterVenues([venue()], q({ text: '잠실' }))).toEqual([])
  })
})
