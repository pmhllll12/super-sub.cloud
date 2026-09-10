/**
 * **경기 조건** — 「어느 동네에서 · 언제 · (팀원이면) 내 자리」.
 *
 * 🔴 **RAG 가 「비슷하다」를 판단할 근거가 이 값이다.** 이게 없으면 비교할
 * 것이 없어서, 지금 명단의 「같은 지역」 알약은 손으로 적어 둔 글자에 지나지
 * 않는다. 조건이 생기면 **실제로 겹치는 것만** 적을 수 있다(`teamMatch.ts`).
 *
 * 🔴 **팀 조건과 내 조건을 따로 둔다.** 같은 사람이 팀장이면서 팀원일 수
 * 있다 — 한 벌로 두면 「우리 팀이 찾는 경기」와 「내가 뛸 수 있는 때」가
 * 섞인다.
 *
 * ⚠️ **서버 저장이 아니다.** 계약에 자리가 없어(미결로 올렸다) 이 브라우저에만
 * 남는다 — 다른 기기에서는 처음부터 다시 묻는다. 🔴 경로가 생기면 **이 파일만**
 * 갈아 끼운다(`published.ts`·`squadBoard.ts` 가 실제로 그렇게 걷혔다).
 */

/** 언제 뛸 수 있는가 — 한 줄. */
export type TimeSlot = {
  /** 0 = 일요일 … 6 = 토요일. `Date.getDay()` 와 같은 값이라 바로 견줄 수 있다. */
  day: number
  /** `HH:MM` — 30분 단위. */
  from: string
  to: string
}

export type MatchPrefs = {
  /** 고른 지역들(`lib/regions.ts` 의 값). 자유 입력이지만 저장은 목록의 것이다. */
  regions: string[]
  times: TimeSlot[]
  /** 내가 뛸 자리 — **팀원 조건에만** 쓴다. 팀 조건에서는 늘 빈 배열이다. */
  positions: string[]
}

/** 어느 쪽 조건인가 — 열쇠도 화면도 이 값으로 갈린다. */
export type PrefsKind = 'team' | 'me'

export const PREFS_KEY = 'ss.matchPrefs.v1'

export const EMPTY_PREFS: MatchPrefs = { regions: [], times: [], positions: [] }

/** 요일 이름 — 화면과 저장이 같은 순서(`Date.getDay()`)를 쓴다. */
export const DAYS = ['일', '월', '화', '수', '목', '금', '토'] as const

/**
 * 고를 수 있는 시각 — **30분 단위, 06:00~24:00**(사용자 요청: 세세하게).
 * 🔴 24:00 을 끝에 둔다 — 밤 경기의 끝을 적을 자리가 없으면 23:30 까지밖에
 * 못 적는다.
 */
export const HOURS: string[] = (() => {
  const out: string[] = []
  for (let m = 6 * 60; m <= 24 * 60; m += 30) {
    out.push(`${String(Math.floor(m / 60)).padStart(2, '0')}:${m % 60 === 0 ? '00' : '30'}`)
  }
  return out
})()

/** 저장된 모양이 아니면 없는 것으로 친다 — 사람이 손댈 수 있는 자리다. */
function clean(v: unknown): MatchPrefs | null {
  if (!v || typeof v !== 'object') return null
  const p = v as Partial<MatchPrefs>
  if (!Array.isArray(p.regions) || !Array.isArray(p.times)) return null
  return {
    regions: p.regions.filter((r) => typeof r === 'string'),
    times: p.times.filter(
      (t) => t && typeof t.day === 'number' && typeof t.from === 'string' && typeof t.to === 'string',
    ),
    positions: Array.isArray(p.positions) ? p.positions.filter((s) => typeof s === 'string') : [],
  }
}

/**
 * 정해 둔 조건. **아직 안 정했으면 `null`** 이다 — 빈 조건과 갈라야 한다.
 * 「처음이라 물어야 하는가」가 그 차이로 정해진다.
 */
export function loadPrefs(kind: PrefsKind): MatchPrefs | null {
  try {
    const raw = globalThis.localStorage?.getItem(PREFS_KEY)
    if (!raw) return null
    const all = JSON.parse(raw) as Record<string, unknown>
    return clean(all?.[kind])
  } catch {
    // 깨진 JSON, 사생활 보호 창에서 던지는 경우까지 여기서 받는다.
    return null
  }
}

export function savePrefs(kind: PrefsKind, prefs: MatchPrefs): void {
  try {
    const raw = globalThis.localStorage?.getItem(PREFS_KEY)
    const all = raw ? (JSON.parse(raw) as Record<string, unknown>) : {}
    globalThis.localStorage?.setItem(PREFS_KEY, JSON.stringify({ ...all, [kind]: prefs }))
  } catch {
    // 못 써도 화면은 계속 돈다 — 그 자리에서 고른 조건으로는 찾을 수 있다.
  }
}

/** `토 09:00~11:00` — 화면에 한 줄로 적을 때. */
export function slotText(t: TimeSlot): string {
  return `${DAYS[t.day] ?? '?'} ${t.from}~${t.to}`
}

/**
 * 두 시간대가 **겹치는가.** 시작이 같아도 끝이 닿기만 한 것은 안 겹친 것이다
 * (`09:00~11:00` 과 `11:00~13:00` 은 함께 뛸 시간이 0분이다).
 */
export function slotsOverlap(a: TimeSlot, b: TimeSlot): boolean {
  return a.day === b.day && a.from < b.to && b.from < a.to
}
