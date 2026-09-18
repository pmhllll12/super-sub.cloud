'use client'

import { useEffect, useState } from 'react'
import MiniPitch from '@/components/MiniPitch'
import {
  FORMATION_SLOTS,
  ROW_POS,
  sizeOfFormation,
  type PosCode,
} from '@/lib/pitchGrid'
import type { PitchPlayer } from '@/lib/teamMatch'
import type { Squad } from '@/server/backend'

/**
 * **부르는 팀의 판** — 초대 줄 아래에 펼쳐진다 (미결 `paik` 37번).
 *
 * 🔴 **왜 있어야 하나.** 슬러그가 없으면 초대받은 사람은 *어느 자리가 비었고
 * 누가 이미 서 있는지 모른 채* 수락 여부를 정하게 된다 — 판을 보고 정하라는
 * 것이 이 기능의 요점이다.
 *
 * 🔴 **`SquadPanel` 이 아니라 `MiniPitch` 를 쓴다.** 미결 37번과 계약 53번이
 * 둘 다 「`SquadPanel` 재사용」이라고 적어 두었지만, `MiniPitch` 머리말이 이미
 * 그 판단을 뒤집어 놓았다 — `SquadPanel` 은 끌어 옮기기·추천 판·등재·서버
 * 저장까지 든 1,600줄짜리라 여기 쓰려면 그 전부를 꺼야 하고, **끌 것이 많다는
 * 것 자체가 재사용하면 안 된다는 뜻**이다. 읽기 전용 판이 `MiniPitch` 다.
 *
 * 🔴 **열 때 읽는다.** 목록을 그릴 때 줄마다 부르면 열지도 않은 판을 초대
 * 수만큼 읽게 된다.
 */
export default function InviteSquad({
  slug,
  teamName,
  posCode,
}: {
  slug: string
  teamName: string
  /**
   * 팀장이 나를 부른 자리. 🔴 **`null` 이면 내 카드를 안 세운다** — 자리를
   * 안 정한 초대가 정상이고(계약), 없는 자리를 지어내면 거짓을 그리는 것이다.
   */
  posCode: string | null
}) {
  const [squad, setSquad] = useState<Squad | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let alive = true
    void (async () => {
      try {
        const res = await fetch(`/api/squads/${encodeURIComponent(slug)}`)
        if (!alive) return
        if (!res.ok) {
          setFailed(true)
          return
        }
        setSquad((await res.json().catch(() => null)) as Squad | null)
      } catch {
        if (alive) setFailed(true)
      }
    })()
    return () => {
      alive = false
    }
  }, [slug])

  /* 🔴 **이 둘도 `.ss-notify-squad` 안이어야 한다**(사용자 지적, 2026-09-17 —
     「하나 더 복사되어서 떨어지는게 보여」). 판은 흐름에서 빠져 줄 왼쪽에
     서는데 이 두 상태만 상자 밖에 있어서, 그때만 흐름 안에 남아 단추 옆에
     끼어 **두 번째 막대처럼 보였다가** 판이 도착하면 사라졌다. DOM 에 줄이
     둘인 적은 없다(`SiteHeader.test.tsx` 가 확인). */
  if (failed)
    return (
      <div className="ss-notify-squad">
        <p className="ss-notify-note">판을 불러오지 못했습니다</p>
      </div>
    )
  if (!squad)
    return (
      <div className="ss-notify-squad">
        <p className="ss-notify-note">판을 불러오는 중…</p>
      </div>
    )

  const players = withMySeat(toPlayers(squad), posCode, squad.formation)

  // 등재는 있어도 **판에 올린 사람이 없으면** 빈 경기장만 그려진다 — 그대로
  // 두면 "못 불러왔다"와 구별이 안 되므로 말로 적는다.
  if (players.length === 0) return <p className="ss-notify-note">아직 판에 올린 사람이 없습니다</p>

  /* 🔴 **「깜빡이는 자리가 나입니다」를 안 적는다**(사용자 판단, 2026-09-17).
     깜빡이는 것이 내 카드이고 카드에 「나」라고 적혀 있어서, 그 줄은 아는
     것을 한 번 더 말하는 자리였다. */
  return (
    <div className="ss-notify-squad">
      <MiniPitch team={teamName} players={players} side="them" />
    </div>
  )
}

/**
 * **내가 설 자리를 판에 세운다** (사용자 요청, 2026-09-17).
 *
 * 🔴 판만 그리면 「저 팀이 이렇게 짜여 있구나」까지다 — 정작 **내가 어디로
 * 불렸는지**가 안 보인다. 팀장이 정한 자리에 내 카드를 세워야 「저기로
 * 부르는구나」가 한눈에 읽힌다.
 *
 * 🔴 **이미 선 사람을 밀어내지 않는다.** 그 줄의 빈 칸을 고르고, 줄이 다
 * 찼으면 세우지 않는다 — 남의 카드를 덮으면 판이 거짓이 된다.
 */
function withMySeat(
  players: PitchPlayer[],
  posCode: string | null,
  formation: string | null,
): PitchPlayer[] {
  if (!posCode) return players
  const row = ROW_POS.indexOf(posCode as PosCode)
  if (row < 0) return players

  /* 🔴 **아무 칸에나 세우지 않는다**(사용자 지적, 2026-09-17 — 「위치가 몇 개로
     정해져 있는데」). 판은 3×4 격자지만 크기마다 **설 수 있는 자리가 정해져
     있다** — 5:5 는 1-2-1 이라 MF 는 왼쪽·오른쪽 둘뿐이고 가운데는 MF 자리가
     아니다. 격자에 있는 칸이라고 포메이션의 자리인 것은 아니다. */
  const taken = new Set(players.filter((p) => p.row === row).map((p) => p.col))
  const slot = FORMATION_SLOTS[sizeOfFormation(formation)].find(
    (s) => s.row === row && !taken.has(s.col),
  )
  // 그 자리가 다 찼으면 안 세운다 — 남의 카드를 덮으면 판이 거짓이 된다.
  if (!slot) return players

  return [...players, { nickname: '나', col: slot.col, row, pos: ROW_POS[row], mine: true }]
}

/**
 * 스쿼드 응답을 판이 읽는 모양으로 옮긴다.
 *
 * 🔴 **칸이 없는 등재는 판에 안 그린다** — `grid_col`·`grid_row` 가 둘 다
 * `null` 인 줄은 "등재는 됐지만 판에는 안 올린" 사람이다(계약 3-7절).
 */
function toPlayers(squad: Squad): PitchPlayer[] {
  const out: PitchPlayer[] = []
  for (const m of squad.members) {
    if (m.grid_col === null || m.grid_row === null) continue
    out.push({
      nickname: m.nickname,
      col: m.grid_col,
      row: m.grid_row,
      pos: posOf(m.position_code, m.grid_row),
    })
  }
  return out
}

/**
 * 자리 약칭 — 판의 이름표에 찍힌다.
 *
 * 🔴 **모르는 값이면 행에서 읽는다**(`ROW_POS`). 판은 네 줄뿐이라 약칭이
 * 그 넷이 아니면 그릴 자리가 없다 — 행이 포지션을 정하는 것이 판의 규칙이다.
 */
function posOf(code: string, row: number): PosCode {
  const known: PosCode[] = ['FW', 'MF', 'DF', 'GK']
  if ((known as string[]).includes(code)) return code as PosCode
  return ROW_POS[row] ?? 'MF'
}
