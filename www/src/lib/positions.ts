import type { Position } from '@/server/backend'

/**
 * **포지션 목록** — `GET /positions` (계약 3-3절, CCC 28).
 *
 * 🔴 전에는 챗봇 프롬프트 · 스쿼드 등재 · 모집 등록이 각자
 * `{ GK: '골키퍼', … }` 를 들고 있었다. 마이그레이션이 바뀌면 **조용히 낡는**
 * 자리라, 목록의 정본을 서버 하나로 옮겼다. 새 목록을 여기 다시 적지 않는다.
 *
 * 🔴 **`code` 는 종목 안에서만 유일하다** — 야구 `C`(포수)와 농구 `C`(센터)가
 * 다른 것이라, 코드만으로 이름을 찾으면 남의 종목 이름이 나온다.
 */

/**
 * 그 종목의 포지션을 받아 온다. **못 받으면 빈 배열이다** — 목록을 못 받은
 * 것과 "그 종목에 포지션이 없다"가 화면에서 같아 보이지만, 이 목록은 화면을
 * 꾸미는 값이라 판이 멈추는 쪽이 더 나쁘다(부르는 쪽이 붙박이로 버틴다).
 *
 * 🔴 **빈 `sportCode` 를 실어 보내지 않는다** — `?sport_code=` 는 "전체"가
 * 아니라 없는 종목이라 422 `UNKNOWN_SPORT` 다.
 */
export async function fetchPositions(sportCode?: string): Promise<Position[]> {
  try {
    const qs = sportCode ? `?${new URLSearchParams({ sport_code: sportCode })}` : ''
    const res = await fetch(`/api/positions${qs}`)
    if (!res.ok) return []
    const body: unknown = await res.json()
    return Array.isArray(body) ? (body as Position[]) : []
  } catch {
    return []
  }
}
