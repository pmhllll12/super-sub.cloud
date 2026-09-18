/**
 * **초대로 고른 칸을 수락까지 살려 둔다** — 이 브라우저에만, 임시로.
 *
 * 🔴 **계약의 초대 본문에는 칸이 없다.** `POST /teams/{id}/invitations` 가
 * 받는 것은 `{invited_user_id, position_code}` 뿐이라(계약 3-7절),
 * 「**오른쪽** MF」라는 선택이 **서버 어디에도 안 남는다.** 같은 포지션
 * 자리가 둘인 판(MF 좌·우)에서 새로고침하면 판을 되살리는 쪽이 아는 것은
 * `MF` 하나뿐이고, 그래서 **늘 첫 빈 MF(왼쪽)** 로 앉았다 — 사용자가 실제
 * 도메인에서 잡은 그 증상이다(2026-09-18: "오른쪽 미드필더에 넣었는데,
 * 새로고침하니까 왼쪽 미드필더로 자리를 옮겼고").
 *
 * 🔴 **이것은 다리이지 살 곳이 아니다.** 수락되는 순간 그 칸은
 * `PATCH …/squad/members/{id}` 로 **서버 등재에 저장**되고, 여기 적힌 것은
 * 지워진다. 제대로 된 자리는 초대에 `grid_col`·`grid_row` 두 칸이 생기는
 * 것이고 정어진에게 미결 항목으로 올려 두었다 — 그것이 오면 이 파일을
 * 통째로 걷는다.
 *
 * ⚠️ **다른 기기·다른 브라우저에서는 없다.** 그때는 전과 같이 포지션의 첫
 * 빈 자리로 앉는다 — 좌·우가 뒤바뀔 뿐 **판이 깨지지는 않는다.**
 * ⚠️ **비밀이 아니다** — 초대 id 와 격자 번호뿐이고, 서버는 이 값을 안 믿는다
 * (칸을 저장하는 `PATCH` 는 주장만 통과한다).
 */

const KEY = 'ss-invite-seats'

/** 판의 **격자 칸**이다 — 화면 픽셀이 아니다(계약 3-7절과 같은 뜻). */
export type InviteCell = { col: number; row: number }

type Stored = Record<string, InviteCell>

/**
 * 🔴 **읽기는 절대 던지지 않는다.** 사생활 보호 창·저장소 차단·서버 렌더에서
 * `localStorage` 는 없거나 접근이 예외를 낸다. 그때는 「기억이 없다」로
 * 떨어져야 하고, 판은 전처럼 포지션으로 앉힌다.
 */
function read(): Stored {
  try {
    const raw = globalThis.localStorage?.getItem(KEY)
    if (!raw) return {}
    const parsed: unknown = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {}
    return parsed as Stored
  } catch {
    return {}
  }
}

function write(next: Stored): void {
  try {
    globalThis.localStorage?.setItem(KEY, JSON.stringify(next))
  } catch {
    /* 못 써도 판은 그대로 돈다 — 좌·우만 못 살린다. */
  }
}

/** 이 초대를 **어느 칸에서** 보냈는지 적어 둔다. */
export function rememberInviteSeat(invitationId: string, cell: InviteCell): void {
  write({ ...read(), [invitationId]: { col: cell.col, row: cell.row } })
}

/**
 * 그 초대의 칸. 적어 둔 적이 없으면 `null` 이다.
 *
 * 🔴 **모양을 확인하고 준다.** 사람이 고칠 수 있는 값이라 `{col:"왼쪽"}`
 * 같은 것이 들어올 수 있고, 그대로 쓰면 `gridColumn: NaN` 으로 카드가
 * 판 밖에 선다.
 */
export function inviteSeat(invitationId: string): InviteCell | null {
  const cell = read()[invitationId]
  if (!cell || !Number.isInteger(cell.col) || !Number.isInteger(cell.row)) return null
  return { col: cell.col, row: cell.row }
}

/** 그 초대의 기억을 지운다 — 칸이 서버로 갔거나, 거절·무르기로 끝났을 때. */
export function forgetInviteSeat(invitationId: string): void {
  const now = read()
  if (!(invitationId in now)) return
  const next = { ...now }
  delete next[invitationId]
  write(next)
}

/**
 * **살아 있는 초대만 남기고 쓸어 낸다.**
 *
 * 🔴 없으면 이 저장소가 영영 자란다 — 초대는 계속 나가는데 지우는 길이
 * 「수락을 내 눈으로 본 경우」뿐이라, 판을 안 열어 둔 사이에 끝난 초대의
 * 칸이 그대로 쌓인다. 판을 열 때마다 그 팀의 초대 목록을 이미 읽으므로
 * (`GET /teams/{id}/invitations`) 거기 없는 id 는 버린다.
 *
 * ⚠️ **남의 팀 초대까지 지우지 않는다** — 목록은 한 팀의 것이라, 이 함수는
 * `keep` 에 든 것과 **다른 팀에서 적힌 것**을 가를 수 없다. 그래서 지우는
 * 것은 `seen`(이번에 본 팀의 초대 id 전부) 안에 있으면서 `keep`(아직
 * 살아 있는 것)에는 없는 것뿐이다.
 */
export function pruneInviteSeats(seen: string[], keep: string[]): void {
  const alive = new Set(keep)
  const known = new Set(seen)
  const now = read()
  const next: Stored = {}
  let changed = false
  for (const [id, cell] of Object.entries(now)) {
    if (known.has(id) && !alive.has(id)) {
      changed = true
      continue
    }
    next[id] = cell
  }
  if (changed) write(next)
}
