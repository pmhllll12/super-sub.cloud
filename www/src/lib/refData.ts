import type { Position, Region } from '@/server/backend'

/**
 * **참조 데이터를 한 번만 읽는다** — 지역 60곳 · 종목별 포지션.
 *
 * 둘 다 이름↔id 변환에만 쓰이고 거의 안 바뀌는 값이라, 판을 여는 동안 여러
 * 번 부를 이유가 없다. 🔴 **캐시를 한 곳에 둔다** — 팀 조건(`teamPrefsStore`)
 * 과 내 조건(`myPrefsStore`)이 각자 들고 있으면 같은 목록을 두 번 받는다.
 *
 * 🔴 **못 받으면 빈 배열이 아니라 던진다**(지역). 빈 목록으로 진행하면 고른
 * 지역이 전부 버려진 채 「조건 0개」로 저장되는데, 화면에는 성공으로 보이고
 * 정작 후보 목록에는 안 뜬다 — 그 조합이 가장 나쁘다.
 */

let regionsCache: Region[] | null = null
/** 종목마다 다른 목록이라 종목별로 담는다(`null` = 전 종목). */
const positionsCache = new Map<string, Position[]>()

export async function regions(): Promise<Region[]> {
  if (regionsCache) return regionsCache
  const res = await fetch('/api/regions')
  if (!res.ok) throw new Error('지역 목록을 불러오지 못했습니다.')
  regionsCache = ((await res.json().catch(() => null)) ?? []) as Region[]
  return regionsCache
}

/**
 * 그 종목의 포지션 목록.
 *
 * 🔴 **빈 `sportCode` 를 실어 보내지 않는다** — `?sport_code=` 는 "전체"가
 * 아니라 없는 종목이라 422 `UNKNOWN_SPORT` 다(`lib/positions.ts` 와 같은 규칙).
 */
export async function positions(sportCode: string | null): Promise<Position[]> {
  const key = sportCode ?? ''
  const hit = positionsCache.get(key)
  if (hit) return hit
  const qs = sportCode ? `?${new URLSearchParams({ sport_code: sportCode })}` : ''
  const res = await fetch(`/api/positions${qs}`)
  if (!res.ok) throw new Error('포지션 목록을 불러오지 못했습니다.')
  const list = ((await res.json().catch(() => null)) ?? []) as Position[]
  positionsCache.set(key, list)
  return list
}

/** 시험에서만 쓴다 — 받아 둔 목록을 비운다. */
export function __resetRefDataCache(): void {
  regionsCache = null
  positionsCache.clear()
}
