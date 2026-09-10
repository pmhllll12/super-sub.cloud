import type { SportCode } from '@/lib/market'
import type { MatchPrefs } from '@/lib/matchPrefs'
import type { Venue, VenueSlot } from '@/lib/venues'

/**
 * **경기장 거르기** — 화면이 부르는 순수 함수들.
 *
 * 🔴 **거를 수 있는 것은 데이터에 있는 것뿐이다.** 원본(서울시 공공서비스예약
 * 스냅샷)에 **요금도 도로명주소도 없어서**(`venues.ts` 머리 주석) 가격·거리·
 * 지도순은 여기 없다 — 만들면 값을 지어내야 한다.
 *
 * 🔴 **요일·시간은 `label` 이 아니라 `hours` 의 숫자로 판단한다.** 89개
 * 시간대 중 31개는 이름이 그냥 「이용」이라, 이름으로 나누면 **절반이 조용히
 * 빠진다.** 요일만은 숫자로 알 수 없어 이름을 보되, 안 적힌 것은 「아무 때나」로
 * 친다(아래 `dayKindOf`).
 *
 * 🔴 **조건 여럿은 같은 시간대 하나가 다 만족해야 한다.** 시설 단위로 따로
 * 검사하면 「토·일」은 주간 시간대에서, 「야간」은 평일 시간대에서 걸려
 * **주말 야간이 없는 곳이 주말 야간 검색에 나온다.** 실제로 그런 시설이 있다.
 */

/** 평일인가 주말·공휴일인가. 원본 이름에 안 적혀 있으면 `null`. */
export type DayKind = 'weekday' | 'weekend'

/** 조기(이른 아침) · 낮 · 야간. 한 시간대가 셋 다일 수 있다(06:00~22:00). */
export type TimeBand = 'early' | 'day' | 'night'

export type VenueQuery = {
  sport: SportCode | null
  /** 빈 배열이면 **전체**다 — 「아무 지역도 안 고름」과 「전체」는 같은 뜻으로 둔다. */
  regions: string[]
  days: DayKind[]
  bands: TimeBand[]
  /** 접수중인 시간대가 하나라도 있는 곳만. */
  openOnly: boolean
  /** `HH:MM` — 그 시각에 열려 있는 시간대가 있는 곳만. 안 쓰면 `null`. */
  at: string | null
  /** 시설 이름 일부. */
  text: string
  /** 「내 경기 조건에 맞는 곳만」이 켜져 있을 때의 조건. 꺼져 있으면 `null`. */
  prefs: MatchPrefs | null
}

export const EMPTY_QUERY: VenueQuery = {
  sport: null,
  regions: [],
  days: [],
  bands: [],
  openOnly: false,
  at: null,
  text: '',
  prefs: null,
}

/** 조건이 하나라도 켜져 있는가 — 「비우기」를 보일지 정한다. */
export function hasQuery(q: VenueQuery): boolean {
  return (
    q.sport !== null ||
    q.regions.length > 0 ||
    q.days.length > 0 ||
    q.bands.length > 0 ||
    q.openOnly ||
    q.at !== null ||
    q.text.trim() !== '' ||
    q.prefs !== null
  )
}

/** `HH:MM` → 자정부터의 분. 모양이 다르면 `null`. */
export function minutesOf(hhmm: string): number | null {
  const m = /^(\d{1,2}):(\d{2})$/.exec(hhmm.trim())
  if (!m) return null
  const h = Number(m[1])
  const min = Number(m[2])
  if (h > 24 || min > 59) return null
  return h * 60 + min
}

/**
 * `"09:00~17:30"` → 분 구간. 못 읽으면 `null`.
 *
 * 🔴 자정을 넘기는 것(`22:00~02:00`)은 **끝에 24시간을 더한다.** 안 그러면
 * 시작이 끝보다 커서 어떤 검사에도 안 걸려 조용히 사라진다 — 실제로 하나 있다.
 */
export function parseSpan(hours: string): { from: number; to: number } | null {
  const [a, b] = hours.split('~')
  if (!a || !b) return null
  const from = minutesOf(a)
  const to = minutesOf(b)
  if (from === null || to === null) return null
  return { from, to: to <= from ? to + 24 * 60 : to }
}

/**
 * 이름에서 요일을 읽는다. **안 적혀 있으면 `null`** 이고, 그런 시간대는
 * 요일 조건을 **통과시킨다** — 원본이 요일을 안 나누고 파는 시설이라
 * (89개 중 31개) 빼 버리면 목록의 3분의 1이 사라진다.
 */
export function dayKindOf(label: string): DayKind | null {
  // 🔴 **「평일」에도 「일」이 들어 있다.** 주말 낱말을 먼저 찾으면 평일 시간대가
  //    전부 주말로 읽힌다(실제로 그렇게 틀렸다) — 「평일」을 덜어 낸 나머지에서
  //    찾는다.
  const rest = label.replace(/평일/g, '')
  const weekend = /토|일|주말|공휴/.test(rest)
  const weekday = /평일/.test(label)
  // 둘 다 적힌 시간대는 **아무 때나**로 친다 — 하나를 골라 버리면 나머지 요일이
  //    조용히 사라진다.
  if (weekday && weekend) return null
  if (weekend) return 'weekend'
  if (weekday) return 'weekday'
  return null
}

/** 그 요일(0=일 … 6=토)을 이 시간대가 받는가. 안 적힌 시간대는 아무 요일이나 받는다. */
function acceptsDay(kind: DayKind | null, day: number): boolean {
  if (kind === null) return true
  return kind === 'weekend' ? day === 0 || day === 6 : day >= 1 && day <= 5
}

const DAY_END = 9 * 60
const NIGHT_START = 17 * 60

/** 시각 구간이 걸치는 때 — 🔴 **이름이 아니라 숫자로** 정한다. */
export function bandsOf(hours: string): TimeBand[] {
  const span = parseSpan(hours)
  if (!span) return []
  const out: TimeBand[] = []
  if (span.from < DAY_END) out.push('early')
  if (span.from < NIGHT_START && span.to > DAY_END) out.push('day')
  if (span.to > NIGHT_START) out.push('night')
  return out
}

/** 그 시각에 열려 있는가. 끝 시각은 **안 친다**(17:00 에 끝나는 곳은 17:00 에 못 뛴다). */
export function openAt(hours: string, at: string): boolean {
  const span = parseSpan(hours)
  const t = minutesOf(at)
  if (!span || t === null) return false
  return (span.from <= t && t < span.to) || (span.to > 24 * 60 && t + 24 * 60 < span.to)
}

/** 정해 둔 조건과 겹치는 시간대인가 — 요일이 맞고 시각이 겹쳐야 한다. */
function matchesPrefTimes(slot: VenueSlot, prefs: MatchPrefs): boolean {
  if (prefs.times.length === 0) return true
  const span = parseSpan(slot.hours)
  if (!span) return false
  const kind = dayKindOf(slot.label)
  return prefs.times.some((t) => {
    if (!acceptsDay(kind, t.day)) return false
    const from = minutesOf(t.from)
    const to = minutesOf(t.to)
    if (from === null || to === null) return false
    // 끝이 닿기만 한 것은 안 겹친 것이다 — 함께 뛸 시간이 0분이다.
    return span.from < to && from < span.to
  })
}

/**
 * 🔴 **시간에 걸리는 조건은 전부 여기서 함께 본다.** 시간대 하나가 요일 ·
 * 때 · 시각 · 정해 둔 조건을 **동시에** 만족해야 한다.
 */
export function slotMatches(slot: VenueSlot, q: VenueQuery): boolean {
  if (q.openOnly && !slot.open) return false
  if (q.days.length > 0) {
    const kind = dayKindOf(slot.label)
    if (!q.days.some((d) => (kind === null ? true : kind === d))) return false
  }
  if (q.bands.length > 0) {
    const bands = bandsOf(slot.hours)
    if (!q.bands.some((b) => bands.includes(b))) return false
  }
  if (q.at !== null && !openAt(slot.hours, q.at)) return false
  if (q.prefs && !matchesPrefTimes(slot, q.prefs)) return false
  return true
}

/** 접수중인 시간대 수 — 정렬 기준이자 카드에 적는 값이다. */
export function countOpen(venue: Venue): number {
  return venue.slots.filter((s) => s.open).length
}

export function venueMatches(venue: Venue, q: VenueQuery): boolean {
  if (q.sport && !venue.sports.includes(q.sport)) return false
  if (q.regions.length > 0 && !q.regions.includes(venue.region)) return false
  if (q.prefs && q.prefs.regions.length > 0 && !q.prefs.regions.includes(venue.region)) return false

  const text = q.text.trim()
  if (text && !venue.name.includes(text) && !venue.region.includes(text)) return false

  // 시간에 걸리는 조건이 하나도 없으면 시간대는 안 본다 — 전부 통과다.
  const timed =
    q.openOnly || q.days.length > 0 || q.bands.length > 0 || q.at !== null || q.prefs !== null
  return !timed || venue.slots.some((s) => slotMatches(s, q))
}

/**
 * 거르고 **접수중인 시간대가 많은 순**으로 세운다(사용자 결정, 2026-09-10) —
 * 실제로 잡을 수 있는 곳이 위로 온다.
 *
 * ⚠️ 접수 현황은 내려받은 시점 기준이라 **실시간이 아니다.** 순서가 「지금
 * 비어 있는 순」처럼 읽히지 않도록 화면이 그 사실을 계속 말한다.
 * 🔴 같은 수끼리는 **원본 순서 그대로**다 — `sort` 가 안정 정렬이라 그렇다.
 */
export function filterVenues(venues: Venue[], q: VenueQuery): Venue[] {
  return venues.filter((v) => venueMatches(v, q)).sort((a, b) => countOpen(b) - countOpen(a))
}
