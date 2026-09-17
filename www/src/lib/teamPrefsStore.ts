import type { Region, TeamMatchPreference } from '@/server/backend'
import type { MatchPrefs } from './matchPrefs'
import { toScreenPrefs, toServerPrefs } from './matchPrefsServer'

/**
 * **팀 경기 조건을 서버에 읽고 쓴다** (계약 3-13절, CCC 40번).
 *
 * 🔴 **여기가 「우리 팀이 남에게 보이기 시작하는」 자리다.** 서버가 후보를
 * 고를 때 「경기 조건을 하나라도 등록한 팀만」 남긴다 — 전에는 조건이
 * `localStorage` 에만 있어서(`matchPrefs.ts`), 화면상으로는 설정이 끝난
 * 것처럼 보이는데 **우리 팀이 남의 후보 목록에 아예 안 떴다.**
 *
 * 🔴 **지역 목록을 한 번만 읽는다.** 이름↔id 변환에 필요한데 60곳이 잘 안
 * 바뀌는 참조 데이터라, 화면을 여는 동안 여러 번 부를 이유가 없다.
 */

let regionsCache: Region[] | null = null

async function regions(): Promise<Region[]> {
  if (regionsCache) return regionsCache
  const res = await fetch('/api/regions')
  if (!res.ok) throw new Error('지역 목록을 불러오지 못했습니다.')
  regionsCache = ((await res.json().catch(() => null)) ?? []) as Region[]
  return regionsCache
}

/**
 * 정해 둔 팀 조건. **아직 안 정했으면 `null`** 이다 — 빈 조건(다 지운 것)과
 * 갈라야 「처음이라 물어야 하는가」가 정해진다.
 *
 * 🔴 서버는 조건이 없을 때도 **빈 목록을 담은 200** 을 준다(404 가 아니다) —
 * 그래서 「지역도 시간도 0개」를 곧 「안 정했다」로 읽는다.
 */
export async function loadTeamPrefs(teamId: string): Promise<MatchPrefs | null> {
  const [list, res] = await Promise.all([
    regions(),
    fetch(`/api/teams/${encodeURIComponent(teamId)}/match-preferences`),
  ])
  if (!res.ok) return null
  const pref = (await res.json().catch(() => null)) as TeamMatchPreference | null
  if (!pref) return null
  if (pref.region_ids.length === 0 && pref.slots.length === 0) return null
  return toScreenPrefs(pref, list)
}

/**
 * 팀 조건을 **통째로 교체**한다 — 팀장만(아니면 403).
 *
 * 🔴 **던진다.** 실패를 조용히 삼키면 사용자는 설정이 저장된 줄 알고, 정작
 * 남의 목록에는 안 뜬다 — 부르는 쪽이 그 사실을 화면에 적는다.
 * 🔴 **팀 id 가 없으면 보낼 데가 없다** — 주장인 팀을 아직 못 읽은 경우다.
 */
export async function saveTeamPrefs(teamId: string | null, prefs: MatchPrefs): Promise<void> {
  if (!teamId) throw new Error('우리 팀을 찾지 못했습니다.')
  const body = toServerPrefs(prefs, await regions())
  /* 🔴 **조용히 빈 조건으로 저장되는 것을 막는다.** 지역은 이름으로 고르고
     id 로 보내는데(`matchPrefsServer.ts`), 화면의 검색 목록과 서버 목록의
     이름이 한 글자라도 다르면 **전부 버려진다.** 그대로 보내면 「조건 0개」로
     저장되고, 서버는 조건 없는 팀을 후보에서 빼므로 **우리 팀이 계속 안
     보이는데 화면에는 성공으로 보인다** — 그 조합이 가장 나쁘다. */
  if (prefs.regions.length > 0 && body.region_ids.length === 0) {
    throw new Error('고른 지역을 서버 목록에서 찾지 못했습니다.')
  }
  const res = await fetch(`/api/teams/${encodeURIComponent(teamId)}/match-preferences`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error('조건을 저장하지 못했습니다.')
}

/** 시험에서만 쓴다 — 지역 캐시를 비운다. */
export function __resetRegionsCache(): void {
  regionsCache = null
}
