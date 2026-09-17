import { DAYS, type TimeSlot } from './matchPrefs'

/**
 * **조건 슬롯 → 실제 경기 시각** (계약 3-15절이 요구하는 `played_at`).
 *
 * 🔴 **왜 필요한가.** 「맞는 상대」 후보(`GET /teams/{id}/match-candidates`)는
 * **팀 후보이지 경기 공고가 아니라서 시각·구장이 없다.** 그런데 신청
 * (`POST /teams/{id}/match-requests`)은 `played_at`·`place` 를 **필수로**
 * 받는다. 🔴 **지어내지 않는다** — 시각은 **우리가 서버에 올린 경기 조건**에서
 * 만들고, 구장은 경기장 목록(`lib/venues.ts`, 서울시 공공데이터)에서 고른다.
 *
 * 🔴 **조건이 없으면 빈 목록이다.** 아무 시각이나 채워 넣으면 아무도 못 뛰는
 * 경기가 잡힌다.
 */

/** 고를 수 있는 한 줄 — 실제 시각과 사람이 읽을 이름. */
export type Proposal = {
  at: Date
  /** `토 09/19 11:00~13:00` — 고르는 자리에 그대로 적는다. */
  label: string
  slot: TimeSlot
}

/**
 * 그 조건이 **다음에 오는 날**의 그 시각.
 *
 * 🔴 **같은 요일이라도 시각이 이미 지났으면 다음 주다.** 지난 시각으로
 * 신청하면 서버가 받아 줘도 아무도 못 뛴다.
 */
export function nextOccurrence(slot: TimeSlot, now: Date = new Date()): Date {
  const [h, m] = slot.from.split(':').map(Number)
  const at = new Date(now)
  at.setHours(h, m, 0, 0)
  // 화면의 `day` 는 `Date.getDay()` 와 같은 기준(0=일)이라 바로 견준다.
  let ahead = (slot.day - at.getDay() + 7) % 7
  // 오늘인데 시각이 지났으면 다음 주 같은 요일이다.
  if (ahead === 0 && at.getTime() <= now.getTime()) ahead = 7
  at.setDate(at.getDate() + ahead)
  return at
}

/** 두 자리로 맞춘다 — 날짜·시각을 한 줄에 적을 때. */
function p2(n: number): string {
  return String(n).padStart(2, '0')
}

/**
 * 조건 전부를 **이른 것부터** 고를 수 있는 목록으로 펼친다.
 *
 * 🔴 순서는 **실제 날짜 순**이다 — 조건에 적힌 순서가 아니다. 목요일에
 * 「일 09:00」과 「토 11:00」을 갖고 있으면 **토요일이 먼저 온다.**
 */
export function proposalsFrom(slots: TimeSlot[], now: Date = new Date()): Proposal[] {
  return slots
    .map((slot) => {
      const at = nextOccurrence(slot, now)
      return {
        at,
        slot,
        label: `${DAYS[slot.day] ?? '?'} ${p2(at.getMonth() + 1)}/${p2(at.getDate())} ${slot.from}~${slot.to}`,
      }
    })
    .sort((a, b) => a.at.getTime() - b.at.getTime())
}

/**
 * 계약이 받는 모양으로 — **현지 시각의 오프셋을 붙인다.**
 *
 * 🔴 `toISOString()` 을 쓰지 않는다. 그건 UTC 로 바꿔 버려서 「토 11:00」이
 * 「토 02:00」으로 저장된다 — 사람이 고른 것은 **한국 시각의 11시**다.
 */
export function toPlayedAt(at: Date): string {
  const off = -at.getTimezoneOffset()
  const sign = off >= 0 ? '+' : '-'
  const oh = p2(Math.floor(Math.abs(off) / 60))
  const om = p2(Math.abs(off) % 60)
  return (
    `${at.getFullYear()}-${p2(at.getMonth() + 1)}-${p2(at.getDate())}` +
    `T${p2(at.getHours())}:${p2(at.getMinutes())}:00${sign}${oh}:${om}`
  )
}
