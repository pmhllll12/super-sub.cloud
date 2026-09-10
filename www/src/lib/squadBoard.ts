import type { Squad, SquadMember } from '@/server/backend'

/**
 * 스쿼드 판의 **배치를 서버에 남긴다** — 판 크기 · 카드가 선 칸 · 손으로 정한
 * 포지션 (계약 3-7절, CCC 25 / 미결 `paik` 9번).
 *
 * 🔴 **2026-09-10 에 브라우저 저장소를 걷어냈다.** 그전에는 그 브라우저에만
 * 남아서 **다른 기기에서는 늘 처음 판**으로 열렸다. 이제 세 값이 계약이다:
 *
 *   판 크기   `Squad.formation`            ← `PATCH /teams/{id}/squad`
 *   칸        `SquadMember.grid_col/_row`  ← `PATCH …/squad/members/{id}`
 *   포지션    `SquadMember.position_code`  ← 같은 PATCH
 *
 * 🔴 **서버가 쥐는 것은 「등재된 사람」의 배치뿐이다.** 빈 자리는 서버에 자리가
 * 없다 — `squad_member` 는 사람이 있어야 존재한다. 그래서 빈 자리의 칸·포지션은
 * 여전히 포메이션 기본값이고, 이 파일은 **그것을 서버에 밀어 넣으려 하지
 * 않는다.** 억지로 넣으려면 「사람 없는 등재」라는 없는 개념을 만들어야 한다.
 *
 * ⚠️ **넣기 · 빼기는 아직 이 파일이 다루지 않는다.** 지인 판에서 앉힌 사람은
 * `player_card_id` 가 없어 등재가 안 되고(그 경로는 따로 있다), 그런 자리는
 * 서버에 저장할 대상이 아니다 — `seatOf` 가 `memberId` 로 그 둘을 가른다.
 */

/** 판 크기의 계약 표기 — 화면의 `'3'`과 서버의 `"3:3"` 을 잇는다. */
export function formationToSize(formation: string | null): string | null {
  if (!formation) return null
  const head = formation.split(':')[0]
  return head || null
}

/** 화면 크기(`'5'`) → 계약 표기(`"5:5"`). */
export function sizeToFormation(size: string): string {
  return `${size}:${size}`
}

/**
 * 그 등재가 판에 올라와 있는가 — **둘 다 채워졌을 때만** 그렇다.
 * 🔴 한쪽만 채워지는 일은 없다(서버가 422 로 막는다). 그래도 `null` 검사를
 * 한쪽만 하면 나중에 다른 한쪽이 없을 때 조용히 0번 칸에 선다.
 */
export function seatOf(m: SquadMember): { col: number; row: number } | null {
  return m.grid_col !== null && m.grid_row !== null ? { col: m.grid_col, row: m.grid_row } : null
}

async function patch(path: string, body: unknown): Promise<Squad> {
  const res = await fetch(path, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    let message = '판을 저장하지 못했습니다.'
    try {
      message = (await res.json())?.error?.message ?? message
    } catch {
      // 계약 형태가 아닌 응답 — 위 기본 문구를 쓴다.
    }
    throw new Error(message)
  }
  return (await res.json()) as Squad
}

/**
 * 판 크기를 저장한다. **바뀐 스쿼드 전체**가 돌아온다.
 *
 * ⚠️ **주장이 아니면 403 이다.** 판은 누구나 만져 볼 수 있지만 남는 것은
 * 주장이 만진 것뿐이다 — 계약이 그렇게 정했고, 부르는 쪽이 그 실패를 판이
 * 멈추는 일로 만들지 않는다.
 */
export function saveFormation(teamId: string, size: string): Promise<Squad> {
  return patch(`/api/teams/${encodeURIComponent(teamId)}/squad`, {
    formation: sizeToFormation(size),
  })
}

/**
 * 등재 하나의 **포지션 · 칸**을 저장한다.
 *
 * 🔴 `positionCode` 는 **항상 보낸다** — 등재는 포지션 없이 존재하지 않는다.
 * 칸만 옮길 때도 지금 코드를 그대로 싣는다(계약 3-7절).
 * 🔴 `cell` 이 `null` 이면 **판에서만 뺀다** — 등재는 남는다.
 */
export function saveSeat(
  teamId: string,
  memberId: string,
  positionCode: string,
  cell: { col: number; row: number } | null,
): Promise<Squad> {
  return patch(
    `/api/teams/${encodeURIComponent(teamId)}/squad/members/${encodeURIComponent(memberId)}`,
    {
      position_code: positionCode,
      grid_col: cell ? cell.col : null,
      grid_row: cell ? cell.row : null,
    },
  )
}
