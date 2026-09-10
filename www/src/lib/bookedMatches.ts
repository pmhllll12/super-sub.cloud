import type { MatchTeam } from '@/lib/teamMatch'

/**
 * **팀 매칭으로 잡힌 경기** — 상대 팀장이 수락한 것들.
 *
 * ⚠️ **서버 저장이 아니다.** 팀 매칭은 넷 다 계약에 없다(추천 · 신청 · 알림 ·
 * 수락 — `lib/teamMatch.ts` 첫머리). 그래서 잡힌 경기도 둘 데가 없어 **이
 * 브라우저에만** 남는다. 다른 기기에서는 안 보이고, 상대에게도 안 간다.
 *
 * 🔴 **`GET /teams/{id}/matches`(내 경기)와 섞지 않는다.** 그쪽은 서버가 준
 * 진짜 경기이고 이것은 데모다 — 한 배열로 뭉치면 어느 것이 진짜인지 화면도
 * 다음 사람도 알 수 없다. 화면이 **따로 받아 얹고**, 데모라고 적는다.
 *
 * 🔴 경로가 생기면 **이 파일만 지운다.** 부르는 쪽은 아래 두 함수만 안다 —
 * `published.ts`·`squadBoard.ts` 가 계약을 얻으면서 실제로 그렇게 걷혔다.
 */

export const BOOKED_KEY = 'ss.booked.v1'

/** 잡힌 경기 한 건 — 목록에 그릴 만큼만 담는다. */
export type BookedMatch = {
  /** 상대 팀의 id. 같은 팀과 두 번 잡지 않는 기준이다. */
  id: string
  /** 상대 팀 이름. */
  opponent: string
  /** 언제(ISO). */
  playedAt: string
  place: string
}

function read(): BookedMatch[] {
  try {
    const raw = globalThis.localStorage?.getItem(BOOKED_KEY)
    if (!raw) return []
    const v: unknown = JSON.parse(raw)
    // 사람이 손댈 수 있는 자리다 — 모양이 아니면 없는 것으로 친다.
    if (!Array.isArray(v)) return []
    return (v as BookedMatch[]).filter(
      (m) => m && typeof m.id === 'string' && typeof m.playedAt === 'string',
    )
  } catch {
    // 깨진 JSON, 사생활 보호 창에서 던지는 경우까지 여기서 받는다.
    return []
  }
}

function write(list: BookedMatch[]): void {
  try {
    globalThis.localStorage?.setItem(BOOKED_KEY, JSON.stringify(list))
  } catch {
    // 못 써도 화면은 계속 돈다 — 저장이 이 화면의 본업이 아니다.
  }
}

/** 이른 것이 앞이다 — 「내 경기」가 그 순서로 읽힌다(계약 3-4절과 같은 규칙). */
export function listBooked(): BookedMatch[] {
  return read().sort((a, b) => a.playedAt.localeCompare(b.playedAt))
}

/**
 * 잡혔다고 적는다. **같은 팀이면 덮어쓴다** — 두 번 신청해도 두 줄이 되지 않는다.
 */
export function book(team: MatchTeam): void {
  const next: BookedMatch = {
    id: team.id,
    opponent: team.name,
    playedAt: team.playedAt,
    place: team.place,
  }
  write([next, ...read().filter((m) => m.id !== team.id)])
}

/** 취소한다 — 경기 취소가 부른다. */
export function unbook(id: string): void {
  write(read().filter((m) => m.id !== id))
}
