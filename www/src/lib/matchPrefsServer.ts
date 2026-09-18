import type {
  MatchSlot,
  MemberMatchPreference,
  Position,
  Region,
  TeamMatchPreference,
} from '@/server/backend'
import { EMPTY_PREFS, type MatchPrefs, type TimeSlot } from './matchPrefs'

/**
 * **화면 모양 ↔ 계약 모양** (계약 3-13절, CCC 40번).
 *
 * 조건이 브라우저(`localStorage`)에만 남던 것을 서버로 올리면서 생긴 자리다.
 * 🔴 **두 모양이 세 군데서 어긋난다** — 그냥 갈아 끼우면 조용히 틀린 값이
 * 저장된다:
 *
 * | | 화면 | 계약 |
 * |---|---|---|
 * | 요일 | `day` **0(일)~6(토)** (`Date.getDay()`) | `weekday` **0(월)~6(일)** |
 * | 시각 | `HH:MM` | `HH:MM:SS` |
 * | 지역 | **이름**(`서울 강남구`) | **id**(UUID) |
 *
 * 🔴 **변환은 이 파일에만 둔다.** 두 군데서 하면 한쪽만 고쳐져 저장할 때와
 * 읽을 때가 갈린다 — 그러면 요일이 하루씩 밀리는데 **화면에는 아무 표시도
 * 안 난다**(겹침 계산만 조용히 틀린다).
 */

/**
 * 화면 요일(0=일) → 계약 요일(0=월).
 *
 * 일(0) → 6 · 월(1) → 0 · 토(6) → 5.
 */
function toServerWeekday(day: number): number {
  return (day + 6) % 7
}

/** 계약 요일(0=월) → 화면 요일(0=일). 위의 역이다. */
function toScreenDay(weekday: number): number {
  return (weekday + 1) % 7
}

export function toServerSlot(t: TimeSlot): MatchSlot {
  return {
    weekday: toServerWeekday(t.day),
    start_time: `${t.from}:00`,
    end_time: `${t.to}:00`,
  }
}

export function toScreenSlot(s: MatchSlot): TimeSlot {
  return {
    day: toScreenDay(s.weekday),
    // `HH:MM:SS` → `HH:MM`. 서버가 초를 안 붙여 보내도 앞 다섯 자는 같다.
    from: s.start_time.slice(0, 5),
    to: s.end_time.slice(0, 5),
  }
}

/**
 * 보낼 모양으로 옮긴다.
 *
 * 🔴 **모르는 지역 이름은 버린다.** 그대로 실어 보내면 422 `UNKNOWN_REGION`
 * 이고, 계약의 `PUT` 은 **통째로 교체**라 그 한 줄 때문에 **조건 전체가
 * 저장되지 않는다.** 이름을 지어내지도 않는다.
 */
export function toServerPrefs(
  prefs: MatchPrefs,
  regions: Region[],
): { region_ids: string[]; slots: MatchSlot[] } {
  const idOf = new Map(regions.map((r) => [r.label, r.id]))
  const region_ids: string[] = []
  for (const label of prefs.regions) {
    const id = idOf.get(label)
    if (id) region_ids.push(id)
  }
  return { region_ids, slots: prefs.times.map(toServerSlot) }
}

/**
 * 받은 모양을 화면 모양으로 되돌린다.
 *
 * 🔴 **모르는 id 는 이름을 지어내지 않고 뺀다** — 목록에 없는 지역을
 * 「알 수 없음」 같은 글자로 채우면 사용자가 그것을 고른 줄로 읽는다.
 * ⚠️ `positions` 는 **팀 조건에 없다**(계약이 개인 조건에만 둔다) — 늘 빈 배열이다.
 */
export function toScreenPrefs(pref: TeamMatchPreference, regions: Region[]): MatchPrefs {
  const labelOf = new Map(regions.map((r) => [r.id, r.label]))
  const names: string[] = []
  for (const id of pref.region_ids) {
    const label = labelOf.get(id)
    if (label) names.push(label)
  }
  return { ...EMPTY_PREFS, regions: names, times: pref.slots.map(toScreenSlot) }
}

/**
 * **내 조건**을 보낼 모양으로 옮긴다 — 팀 조건에 **포지션이 더 붙는다.**
 *
 * 🔴 **화면은 약칭(`MF`)을, 계약은 id(UUID)를 쓴다.** 약칭은 **종목 안에서만**
 * 유일해서(야구 `C`=포수 · 농구 `C`=센터) 그대로 보낼 수가 없다 — 그래서
 * `GET /positions` 가 준 목록으로 옮긴다. 지역이 이름 대신 id 로 가는 것과
 * 같은 이유다.
 *
 * 🔴 **모르는 약칭은 버린다** — 지역과 같은 판단이다. 그대로 실어 보내면 422
 * `UNKNOWN_POSITION` 이고, `PUT` 이 **통째로 교체**라 그 한 줄 때문에 **조건
 * 전체가** 저장되지 않는다. 다만 **조용히 비는 것이 더 나쁘므로**, 부르는 쪽
 * (`myPrefsStore`)이 「고른 것이 있는데 하나도 안 옮겨졌다」를 실패로 본다.
 */
export function toServerMemberPrefs(
  prefs: MatchPrefs,
  regions: Region[],
  positions: Position[],
): { region_ids: string[]; slots: MatchSlot[]; position_ids: string[] } {
  const idOf = new Map(positions.map((p) => [p.code, p.id]))
  const position_ids: string[] = []
  for (const code of prefs.positions) {
    const id = idOf.get(code)
    if (id) position_ids.push(id)
  }
  return { ...toServerPrefs(prefs, regions), position_ids }
}

/**
 * 받은 **내 조건**을 화면 모양으로 되돌린다.
 *
 * 🔴 **모르는 id 는 약칭을 지어내지 않고 뺀다**(지역과 같다) — 목록에 없는
 * 자리를 「알 수 없음」 같은 글자로 채우면 사용자가 그것을 고른 줄로 읽는다.
 */
export function toScreenMemberPrefs(
  pref: MemberMatchPreference,
  regions: Region[],
  positions: Position[],
): MatchPrefs {
  const codeOf = new Map(positions.map((p) => [p.id, p.code]))
  const codes: string[] = []
  for (const id of pref.position_ids) {
    const code = codeOf.get(id)
    if (code) codes.push(code)
  }
  const base = toScreenPrefs(
    { team_id: '', region_ids: pref.region_ids, slots: pref.slots },
    regions,
  )
  return { ...base, positions: codes }
}
