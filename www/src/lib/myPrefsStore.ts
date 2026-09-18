import type { MemberMatchPreference } from '@/server/backend'
import type { MatchPrefs } from './matchPrefs'
import { toScreenMemberPrefs, toServerMemberPrefs } from './matchPrefsServer'
import { positions, regions } from './refData'

/**
 * **내 경기 조건을 서버에 읽고 쓴다** (계약 3-13절, CCC 40번).
 *
 * 🔴 **여기가 「내가 남의 AI 추천 후보로 뜨기 시작하는」 자리다.** 서버가
 * 후보를 고를 때 첫 하드 필터가 「그 포지션을 등록했는가」인데, 조건이
 * `localStorage`(`matchPrefs.ts`)에만 남던 동안에는 **아무도 등록된 적이
 * 없어서** 팀을 만들어도 추천 판이 영영 0명이었다(2026-09-17에 실제로 그랬다).
 *
 * 🔴 **팀 조건(`teamPrefsStore`)과 저장소가 다르다** — 같은 사람이 팀장이면서
 * 팀원일 수 있어 계약이 둘을 절대 안 섞는다.
 */

const PATH = '/api/me/match-preferences'

/**
 * 정해 둔 내 조건. **아직 안 정했으면 `null`** 이다 — 빈 조건(다 지운 것)과
 * 갈라야 「처음이라 물어야 하는가」가 정해진다.
 *
 * 🔴 서버는 조건이 없을 때도 **빈 목록을 담은 200** 을 준다(404 가 아니다) —
 * 그래서 「지역도 시간도 포지션도 0개」를 곧 「안 정했다」로 읽는다.
 * 🔴 **못 읽으면 `null`** 이다(던지지 않는다) — 읽기 실패로 판이 안 열리면
 * 조건을 고칠 길까지 막힌다. 쓰기는 반대로 던진다(아래).
 */
export async function loadMyPrefs(sportCode: string | null): Promise<MatchPrefs | null> {
  try {
    const [regionList, positionList, res] = await Promise.all([
      regions(),
      positions(sportCode),
      fetch(PATH),
    ])
    if (!res.ok) return null
    const pref = (await res.json().catch(() => null)) as MemberMatchPreference | null
    if (!pref) return null
    if (
      pref.region_ids.length === 0 &&
      pref.slots.length === 0 &&
      pref.position_ids.length === 0
    ) {
      return null
    }
    return toScreenMemberPrefs(pref, regionList, positionList)
  } catch {
    return null
  }
}

/**
 * 내 조건을 **통째로 교체**한다.
 *
 * 🔴 **던진다.** 실패를 조용히 삼키면 사용자는 설정이 저장된 줄 알고, 정작
 * 남의 추천 목록에는 안 뜬다 — 부르는 쪽이 그 사실을 화면에 적는다.
 */
export async function saveMyPrefs(
  sportCode: string | null,
  prefs: MatchPrefs,
): Promise<void> {
  /* 🔴 **종목을 모르면 약칭을 못 푼다.** 약칭(`MF`)은 **종목 안에서만**
     유일해서(야구 `C`=포수 · 농구 `C`=센터) 종목 없이는 어느 자리인지
     가려지지 않는다 — 조용히 포지션 없이 저장하면 후보로 안 뜬다. */
  if (prefs.positions.length > 0 && !sportCode) {
    throw new Error('종목을 알 수 없어 포지션을 저장하지 못했습니다.')
  }
  const [regionList, positionList] = await Promise.all([regions(), positions(sportCode)])
  const body = toServerMemberPrefs(prefs, regionList, positionList)
  /* 🔴 **조용히 빈 조건으로 저장되는 것을 막는다.** 이름·약칭으로 고르고
     id 로 보내는데(`matchPrefsServer.ts`), 화면의 값과 서버 목록이 어긋나면
     **전부 버려진다.** 그대로 보내면 「0개」로 저장되고, 서버는 그런 사람을
     후보에서 빼므로 **계속 안 보이는데 화면에는 성공으로 보인다.** */
  if (prefs.regions.length > 0 && body.region_ids.length === 0) {
    throw new Error('고른 지역을 서버 목록에서 찾지 못했습니다.')
  }
  if (prefs.positions.length > 0 && body.position_ids.length === 0) {
    throw new Error('고른 자리를 서버 목록에서 찾지 못했습니다.')
  }
  const res = await fetch(PATH, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error('조건을 저장하지 못했습니다.')
}
