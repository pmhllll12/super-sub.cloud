'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import type { PublicPlayerCard, Squad } from '@/server/backend'
import PlayerCardView from '@/components/PlayerCardView'
import BlankPlayerCard from '@/components/BlankPlayerCard'
import SquadSuggest from '@/components/SquadSuggest'
import SquadFriends from '@/components/SquadFriends'
import TeamSeek from '@/components/TeamSeek'
import MatchBot from '@/components/MatchBot'
import TeamMatch from '@/components/TeamMatch'
import MatchWaiting from '@/components/MatchWaiting'
import { teamById, type MatchTeam } from '@/lib/teamMatch'
import {
  addSeat,
  formationToSize,
  saveFormation,
  saveSeat,
  seatOf,
} from '@/lib/squadBoard'
import {
  COLS,
  ROWS,
  ROW_POS,
  FORMATION_SLOTS,
  cellExists,
  rowPos,
  type PosCode,
  type SquadSize,
} from '@/lib/pitchGrid'
import { fetchPositions } from '@/lib/positions'
import { loadFeaturedOf } from '@/lib/featuredClip'
import { apiDelete, apiPost } from '@/lib/api/client'

/**
 * 홈 첫 화면의 스쿼드 판 — 판 하나 위에 선수 카드를 **포지션 자리대로**
 * 앉힌다(참고: 축구 게임의 스쿼드 화면). 한 줄로 늘어놓지 않는 이유가
 * 그것이다 — 누가 어느 자리인지가 배치로 읽혀야 한다.
 *
 * 풋살 5인, 1-2-1 포메이션 — 골키퍼 하나 · 수비 하나 · 중원 둘 · 공격 하나.
 * 나머지 넷은 빈 카드 — 같은 틀 · 같은 머리글(SUPERSUB · PLAYER CARD)에
 * 가운데 + 만 있다. 눌러 보기 전에 무슨 자리인지 알 수 있어야 해서다.
 *
 * 🔴 **읽기는 서버에서 온다**(2026-09-04). `GET /teams/{id}/squad` 가
 * 09-03 에 생겨서, 홈이 그것을 받아 `squad` 로 넘겨준다 — 새로고침해도
 * 등재된 사람이 그대로 앉아 있다.
 *
 * 🔴 **내 카드도 등재의 하나다**(2026-09-10). 맨 위(FW)는 **판이 내 카드를
 * 그리는 처음 자리**일 뿐이고, 내 카드 슬러그로 내 등재를 찾아 이어 둔다 —
 * 그래서 내 포지션 · 칸도 남들과 똑같이 서버에 남는다. **등재가 아니면
 * 남길 데가 없어** 새로고침하면 처음 자리로 돌아간다(고장이 아니다).
 * 🔴 `mates` 에는 내 이름을 **안** 넣는다 — 넣으면 판이 그 자리를 「남이 앉은
 * 카드」로 그려서 내 카드 대신 이름표가 선다.
 *
 * ⚠️ **넣기 · 빼기는 아직 이 컴포넌트 안에서만 일어난다.**
 * 🔴 **막혀 있어서가 아니다 — 아직 안 붙였을 뿐이다**(2026-09-10 정정).
 * 예전 주석은 *"팀 구성원의 카드 id 를 얻을 경로가 계약에 없다"* 고 적어
 * 두었는데, **2026-09-04 에 열렸다**(미결 `paik` 2번 해소):
 * `GET /teams/{team_id}` 의 `members[]` 가 `player_card_id` 와
 * `card_public_slug` 를 함께 준다. 지금 없는 것은 **www 쪽 접점**이다 —
 * `Backend.getTeam()` 과 그 BFF 라우트를 만들고, `setMates` 를 부르는 자리
 * 둘을 `addSquadMember` · `removeSquadMember` 로 바꾸면 된다.
 * 🔴 그때 **`player_card_id` 가 `null` 인 사람은 단추를 비활성**으로 둔다
 * (카드가 없는 구성원 — 서버도 막지만 눌러 보고 알게 하지 않는다).
 * 자리→등재 id 는 이미 아래 `members` 가 들고 있으니 그 짝을 채우면 된다.
 *
 * 🔴 **판 배치가 2026-09-10 에 서버로 갔다**(CCC 25, 미결 `paik` 9번). 판 크기 ·
 * 카드가 선 칸 · 손으로 정한 포지션 셋이 계약에 자리를 얻어서, 09-08 에
 * 임시로 넣었던 `localStorage` 를 걷어냈다 — 그때 적어 둔 "서버가 진짜가 되는
 * 순간 상태가 두 곳에 생긴다"가 바로 지금이다. 어디에 어떻게 남기는지는
 * `lib/squadBoard.ts` 한 곳에 있다.
 *
 * 🔴 **첫 판을 서버 값에서 만든다** — 저장소를 읽던 때와 달리 하이드레이션이
 * 안 깨진다. `squad` 는 서버 컴포넌트가 준 prop 이라 서버와 브라우저의 첫
 * 그림이 같다(저장소는 서버에 없어서 달랐다).
 */

/* 🔴 **격자 규칙은 `lib/pitchGrid.ts` 가 정본이다** — 대기 팝업의 읽기 전용
   판(`MiniPitch`)이 같은 것을 쓰는데, 그쪽이 이 파일을 import 하면 순환이 된다.
   두 벌로 베끼면 한쪽만 고쳐져 판마다 포지션이 갈린다. */
export type { PosCode }

/**
 * 판 위의 자리.
 *
 * 🔴 `col`·`row` 는 **격자 칸**이다. 전에는 `area`(grid-template-areas 이름)로
 * 못박혀 있었는데, 그러면 자리가 포메이션에 갇혀 옮길 수가 없다.
 * `pos` 가 있으면 **사람이 직접 정한 것**이고, 없으면 행이 정한다.
 */
type Slot = { area: string; col: number; row: number; pos?: PosCode | null; mine?: boolean }

/** 이 자리의 지금 포지션 — 사람이 정한 것이 있으면 그것, 없으면 행이 정한다. */
function posOf(slot: Slot): PosCode {
  return slot.pos ?? rowPos(slot.row)
}

/**
 * 서버가 준 포지션을 자리에 얹는다.
 *
 * 🔴 **행이 정하는 것과 같으면 「자동」(`null`)으로 둔다.** 계약에는 「자동」이
 * 없어서 `position_code` 가 늘 실려 오는데, 그것을 그대로 `pos` 에 박으면
 * **한 번 저장된 카드는 옮겨도 이름표가 안 바뀐다** — 「행이 포지션을 정한다」가
 * 조용히 죽는다(2026-09-10 에 실제로 그랬다).
 *
 * ⚠️ 손으로 정한 값이 마침 행과 같았던 경우는 「자동」이 된다. 그 자리에서는
 * 보이는 것도 뜻도 같고, **다른 줄로 옮길 때만** 갈린다 — 둘을 가릴 방법이
 * 계약에 없으므로 「옮기면 따라 바뀐다」 쪽을 지켰다.
 */
function applyPos(seat: Slot, code: string): void {
  seat.pos = code === rowPos(seat.row) ? null : (code as PosCode)
}

/** 판의 크기 — 3:3 · 5:5 · 7:7. 화면 글자와 같은 값이라 그대로 쓴다. */
/* 🔴 정본은 `lib/pitchGrid.ts` 다 — 좌표와 크기를 두 벌로 두면 판마다
   자리가 갈린다. 여기서는 쓰던 이름을 이어 주기만 한다. */
export type { SquadSize }

/**
 * 크기마다의 포메이션.
 *
 * 🔴 **자리 이름을 역할+번호로 둔다**(`fw1` · `mf2` · `df1` …). 크기를 바꿔도
 * 같은 이름이 같은 자리를 가리켜야, 7인에서 넣은 사람이 5인으로 줄였다가
 * 되돌아왔을 때 **제자리에 그대로 앉아 있다**(사용자 요청: 줄어들면 감췄다가
 * 되돌리면 돌아온다). `ml`·`mr` 처럼 위치로 이름 지으면 3인의 MF 하나가
 * 어느 쪽인지부터 정해야 하고, 크기가 바뀔 때마다 이름이 갈린다.
 *
 * 🔴 여기 적힌 포지션은 **판의 생김새**다(행이 포지션 라인 — 계약 3-7절이
 * 4행으로 못박았다). *고를 수 있는 목록*은 이제 `GET /positions` 가 정본이고
 * (CCC 28) `posCodes` 가 그것을 받는다 — 둘은 다른 축이라 섞지 않는다.
 */
export const FORMATIONS: Record<SquadSize, { label: string; slots: Slot[] }> = {
  '3': { label: '3 : 3', slots: FORMATION_SLOTS['3'] },
  '5': { label: '5 : 5', slots: FORMATION_SLOTS['5'] },
  '7': { label: '7 : 7', slots: FORMATION_SLOTS['7'] },
}

/** 처음 여는 크기 — 풋살 5인(사용자 요청). */
const DEFAULT_SIZE: SquadSize = '5'

// 추천 판이 닫히며 물러나는 시간 — globals.css 의 ss-suggest-out 과 같아야
// 한다. 짧으면 애니메이션 도중에 잘리고, 길면 사라진 자리가 남는다.
const SUGGEST_EXIT_MS = 200

/**
 * 서버가 준 스쿼드를 **판의 자리 이름표**로 바꾼다.
 *
 * 🔴 내 자리(FW)는 건너뛴다 — 거기는 `card` 가 그리므로, 서버 목록에 내가
 * 들어 있어도 같은 사람이 두 번 나오지 않는다.
 * 🔴 같은 포지션이 둘인 자리(MF)는 **먼저 온 사람부터** 채운다. 서버는 어느
 * 쪽 MF 인지까지는 모른다 — 좌 · 우는 화면만의 배치다.
 */
function seatsFromSquad(
  squad: Squad | null,
  size: SquadSize,
  /** 내 카드 — **어느 등재가 나인지** 가리는 열쇠다(아래 0단계). */
  mySlug?: string,
): {
  slots: Slot[]
  mates: Record<string, string | null>
  /** 그 자리 사람의 **카드 공개 슬러그** — 진짜 카드를 그리려면 필요하다. */
  slugs: Record<string, string | null>
  members: Record<string, string>
  /** 그 자리의 사람이 **오기로 했는가**(`accepted_at` 이 찼는가). */
  ready: Record<string, boolean>
} {
  // 자리는 **복사해서** 만진다 — FORMATIONS 는 모듈 상수라 고치면 다음 마운트가
  // 남의 배치를 물려받는다.
  const slots = FORMATIONS[size].slots.map((sl) => ({ ...sl }))
  const mates: Record<string, string | null> = {}
  const slugs: Record<string, string | null> = {}
  const members: Record<string, string> = {}
  const ready: Record<string, boolean> = {}
  if (!squad) return { slots, mates, slugs, members, ready }

  /* 0) **내 자리도 등재와 잇는다**(사용자 요청, 2026-09-10).
        전에는 「내 자리는 `card` 가 그린다」는 이유로 등재와 안 이어 놓았는데,
        그러면 **내 카드만 포지션과 칸이 안 남았다** — 옮길 수는 있는데 새로
        고치면 제자리로 돌아갔다. 나도 팀의 한 명이라 남들과 같아야 한다.
        🔴 `mates` 에는 **안** 넣는다. 거기 이름이 들어가면 판이 그 자리를
        「남이 앉은 카드」로 그려서 내 카드 대신 이름표가 나온다. */
  const me = mySlug ? squad.members.find((m) => m.card_public_slug === mySlug) : undefined
  /* 🔴 **내 자리는 고정이 아니다**(2026-09-16, 사용자 설계). 전에는 포메이션의
     FW 한 칸에 `mine: true` 를 박아 두어 **처음 들어온 사람도 판에 이미 서
     있었다.** 이제는 등재했을 때만, 그것도 **내가 앉힌 칸**에 선다 —
     안 앉히면 판에 없다(「나는 안 뛴다」가 그렇게 표현된다). */
  if (me) {
    const cell = seatOf(me)
    const mySeat = cell
      ? slots.find((sl) => sl.col === cell.col && sl.row === cell.row)
      : undefined
    if (mySeat) {
      mySeat.mine = true
      members[mySeat.area] = me.id
      // 포지션도 저장된 값을 쓴다(행과 같으면 「자동」 — `applyPos` 주석).
      applyPos(mySeat, me.position_code)
    }
  }

  /**
   * 그 자리가 **이미 차 있는가.**
   *
   * 🔴 **내 자리(`mine`)도 찬 것으로 센다.** 거기는 `card` 가 그리므로
   * `mates` 에는 안 들어가는데, 그것만 보고 판단하면 **내 카드 위로 남의
   * 카드를 옮겨 놓는다** — 실제로 그래서 내 카드가 안 보였다(2026-09-10).
   */
  const taken = (sl: Slot) => Boolean(sl.mine || mates[sl.area])

  /* 1) **칸이 저장된 등재 — 그 칸이 곧 자리다.**
        포지션도 저장된 값을 쓴다: 손으로 정했을 수 있어 행에서 역산하면 안 된다. */
  for (const m of squad.members) {
    if (m === me) continue
    const cell = seatOf(m)
    if (!cell) continue
    /* 🔴 그 칸이 이미 찼으면 **건너뛴다.** 내 자리와 겹치는 것이 이 갈래로
       들어온다 — 서버 목록에 내가 들어 있어도 같은 사람이 두 번 나오지
       않게 하는 것이 원래 규칙이고, 그 규칙을 여기서도 지킨다. */
    if (slots.some((sl) => taken(sl) && sl.col === cell.col && sl.row === cell.row)) continue
    /* 🔴 **그 칸에 있는 자리를 먼저 쓴다.** 아무 빈 자리나 끌어다 옮기면
       자리들이 통째로 뒤엉켜, 원래 그 칸에 있던 자리가 밀려나며 카드가
       겹쳐 사라진다. 그 칸에 자리가 없을 때만(골키퍼 줄 양옆처럼 아예 없는
       칸, 또는 판이 작아진 경우) 남는 자리를 옮겨 온다. */
    const seat =
      slots.find((sl) => !taken(sl) && sl.col === cell.col && sl.row === cell.row) ??
      slots.find((sl) => !taken(sl))
    if (!seat) continue
    seat.col = cell.col
    seat.row = cell.row
    applyPos(seat, m.position_code)
    mates[seat.area] = m.nickname
    slugs[seat.area] = m.card_public_slug ?? null
    members[seat.area] = m.id
    /* 🔴 `accepted_at` 이 **안 오면**(옛 응답) 수락된 것으로 본다 — 그 시절엔
       팀원만 앉을 수 있어서 앉은 것이 곧 온 것이었다. 새 응답에서 비어
       있으면 그때는 정말 대기중이다. */
    ready[seat.area] = m.accepted_at !== null
  }

  /* 2) **칸이 아직 없는 등재**(`grid_col`·`grid_row` 가 null)는 포메이션의
        기본 자리에 포지션으로 맞춰 앉힌다.
        ⚠️ 계약대로면 "판에 안 올린 등재"라 안 그리는 것이 맞지만, 그러면
        서버의 **기존 행이 전부 null 이라** 판이 통째로 비어 보인다 — 등재된
        사람이 화면에서 사라지는 쪽이 더 나쁘다. 앉혀서 보여 주되 **여기서
        저장하지는 않는다**(판을 여는 것만으로 서버가 바뀌면 안 된다). 그
        사람을 한 번 옮기면 그때 칸이 서버에 생긴다. */
  for (const m of squad.members) {
    if (m === me || seatOf(m)) continue
    const seat = slots.find((sl) => !taken(sl) && posOf(sl) === m.position_code)
    if (!seat) continue
    mates[seat.area] = m.nickname
    slugs[seat.area] = m.card_public_slug ?? null
    members[seat.area] = m.id
    ready[seat.area] = m.accepted_at !== null
  }
  return { slots, mates, slugs, members, ready }
}

export default function SquadPanel({
  card,
  squad = null,
  sportCode = null,
  teamName = null,
  myCardId = null,
  scouting = false,
  onCloseScouting,
  onOpenScouting,
  myTeamId = null,
  onRequested,
  acceptedTeamId = null,
  acceptedMatchId = null,
  onAcceptedShown,
  seeking = false,
  onCloseSeeking,
  bot = false,
  onBotChange,
}: {
  card?: PublicPlayerCard | null
  /**
   * 그 팀의 종목 — **포지션 목록을 받아 오는 열쇠**다(CCC 28).
   *
   * 🔴 코드만으로는 못 찾는다 — 야구 `C`(포수)와 농구 `C`(센터)가 다르다.
   * 없으면(팀이 없는 사람) 판이 아는 축구 넷으로 돈다.
   */
  sportCode?: string | null
  /**
   * 홈에 그리는 그 팀의 이름 — **머리글이 된다**(사용자 요청, 2026-09-16).
   *
   * 🔴 이름을 적는 까닭은 「내 팀이 생겼다」를 알리는 것보다 **어느 팀 판을
   * 보고 있는지**다. 소속이 여럿일 수 있고 홈은 그중 하나만 그리는데
   * (`lib/homeTeam.ts`), 머리글이 늘 「MY SQUAD」면 고른 팀을 바꿔도 화면
   * 어디에도 안 적힌다.
   *
   * 소속이 없으면 `null` — 그때는 「MY SQUAD」로 둔다(적을 이름이 없다).
   */
  teamName?: string | null
  /**
   * 내 카드 id — **나를 판에 앉힐 때** 계약이 요구하는 값이다
   * (`POST /squad/members` 의 `player_card_id`).
   *
   * ⚠️ `card` 로는 못 얻는다 — 그쪽은 `PublicPlayerCard` 라 id 가 빠져 있다
   * (공개 카드에 내부 id 를 안 싣는 원칙). 그래서 따로 받는다.
   */
  myCardId?: string | null
  /**
   * 서버가 준 스쿼드. **없을 수 있다** — 팀이 없거나(개인 계정) 팀은 있어도
   * 스쿼드를 아직 안 만든 경우다. 계약이 그 둘을 갈라 두었으므로(404
   * `SQUAD_NOT_FOUND`) 여기서도 null 하나로 뭉뚱그리지 않고, 판은 빈 자리로
   * 그린다.
   */
  squad?: Squad | null
  /**
   * 알약 '용병 찾기' 를 눌렀는가 — 켜지면 판 오른쪽에 **AI 추천 판과 지인
   * 찾기 판이 나란히** 열린다.
   *
   * 🔴 예전에는 '지인 찾기' 알약이 지인 판만 열었다. 두 일이 결국 **같은
   * 빈 자리를 채우는 한 가지 일**이라 단추를 하나로 합쳤다(사용자 요청,
   * 2026-09-08) — 그래서 판도 짝으로 여닫는다.
   */
  scouting?: boolean
  onCloseScouting?: () => void
  /**
   * 빈 자리(`+`)를 눌렀을 때 **용병 찾기를 켜 달라**고 부모에게 알린다
   * (사용자 요청, 2026-09-16). 알약으로 연 것과 **같은 한 벌**을 연다 —
   * 추천 판 옆에 지인 찾기 판도 선다.
   *
   * 🔴 `scouting` 은 부모가 든다(`HomeStage`). 이 판이 제 상태로 흉내내지
   * 않는 이유는, 켜진 동안 판 바깥의 큰 글자(`OWN THE PITCH`)가 비켜서야
   * 하고 그 판단이 부모에 있기 때문이다 — 두 곳에서 들면 한쪽만 켜진 채로
   * 어긋난다.
   *
   * ⚠️ 이때 자리는 **누른 자리**다. 아래 `scouting` 효과가
   * `setPicking((now) => now ?? firstEmpty)` 로 **이미 고른 자리를 덮지
   * 않게** 되어 있어서, 누르기 쪽에서 `setPicking(slot)` 을 먼저 하면 그
   * 자리가 그대로 남는다(둘은 같은 이벤트에서 한 번에 반영된다).
   */
  onOpenScouting?: () => void
  /** 내 팀 id — 경기 신청이 이 팀 밑으로 나간다(계약 3-15절). */
  myTeamId?: string | null
  /** 신청을 **걸었다**(「잡혔다」가 아니다) — 부모가 기억해 둔다. */
  /* 🔴 **`id` 만 있으면 된다.** 쓰는 쪽(`HomeStage`)이 `team.id` 를
     기억해 두는 것이 전부다 — 넓게 잡으면 후보(`CandidateTeam`)를 못 넘긴다. */
  onRequested?: (requestId: string, team: { id: string }) => void
  /**
   * **상대가 수락한 팀** — 값이 들어오는 순간 대기 팝업이 뜬다.
   *
   * 🔴 이 신호는 **알림에서 온다**(`useNotifyInbox`). 신청을 건 쪽이든 받아서
   * 수락한 쪽이든, 확정되는 순간은 이 화면 바깥이라 부모가 알려 줘야 한다.
   */
  acceptedTeamId?: string | null
  /**
   * 그렇게 잡힌 **경기 id** — 「무르기」가 이걸로 취소한다(계약은
   * `DELETE /matches/{match_id}`). 🔴 **없으면 무르기 단추를 안 낸다** —
   * 눌러도 아무 일이 없는 단추를 두지 않는다.
   */
  acceptedMatchId?: string | null
  /** 팝업을 닫았다고 부모에게 알린다 — 안 지우면 닫자마자 다시 뜬다. */
  onAcceptedShown?: () => void
  /**
   * 알약 '팀원' 을 눌렀는가 — 켜지면 **스쿼드 판이 물러나고 그 자리에**
   * 사람을 찾는 팀들의 명단이 선다(사용자 요청, 2026-09-08).
   *
   * 🔴 나란히 세우지 않는다. 스쿼드 판은 *내 팀을 짜는* 자리이고 그 판은
   * *남의 팀에 들어가는* 자리라, 둘이 같이 보이면 무엇을 하고 있는지가
   * 흐려진다 — 판 오른쪽이 "한 번에 하나" 인 것과 같은 판단이다.
   */
  seeking?: boolean
  onCloseSeeking?: () => void
  /**
   * AI 챗봇이 열려 있는가 — 켜지면 **지인 찾기와 같은 자리**에서 나온다.
   *
   * 🔴 챗봇 자체는 `HomeStage` 것이지만 그릴 자리는 여기다. 판 오른쪽
   * (`left: 100%`)은 `.ss-squad-wrap` 안에서만 잡히는 좌표라, 바깥에서
   * 그리면 그 자리를 다시 재서 옮겨야 한다 — 자리를 정하는 곳이 둘이 된다.
   */
  bot?: boolean
  onBotChange?: (next: boolean) => void
}) {
  /**
   * 🔴 **판 오른쪽은 이제 칸이 둘이다**(2026-09-08).
   *
   *   첫째 칸 — AI 추천 판 · 챗봇 (`.ss-suggest`)
   *   둘째 칸 — 지인 찾기 판 (`.ss-friends`)
   *
   * 전에는 셋이 **한 좌표**에 서서 "한 번에 하나만" 이 규칙이었다(여는 쪽이
   * 다른 것을 닫았다). 용병 찾기 하나가 추천과 지인을 **같이** 열어야 해서
   * 칸을 갈랐다 — 첫째 칸은 여전히 한 번에 하나다(챗봇이 켜지면 추천이 닫힌다).
   * 좌표는 globals.css 의 `--ss-side-panel-w` 가 정한다.
   */
  /* 🔴 서버가 준 것을 **첫 값으로만** 읽는다. 그 뒤로는 이 화면이 들고 있다 —
     넣기 · 빼기가 아직 서버로 안 가므로(위 주석), 매번 서버 값으로 되돌리면
     방금 넣은 사람이 사라진다. */
  /**
   * 서버가 준 스쿼드로 만든 **첫 판** — 크기 · 자리 · 앉은 사람 · 그 사람의
   * 등재 id 넷이 여기서 나온다(CCC 25).
   *
   * 🔴 **모르는 `formation` 은 기본 판으로 연다.** 계약이 값 집합을 강제하지
   * 않아(길이만 본다) 화면이 아직 모르는 크기가 올 수 있다 — 그때 판이
   * 안 그려지면 안 된다.
   */
  const seeded = useMemo(() => {
    const from = formationToSize(squad?.formation ?? null)
    const startSize: SquadSize =
      from && from in FORMATIONS ? (from as SquadSize) : DEFAULT_SIZE
    return { size: startSize, ...seatsFromSquad(squad, startSize, card?.public_slug) }
  }, [squad, card?.public_slug])

  /**
   * 판의 크기(3:3 · 5:5 · 7:7) — 머리글의 단추가 바꾼다(사용자 요청,
   * 2026-09-08). 정본은 서버의 `Squad.formation` 이다(CCC 25).
   */
  const [size, setSize] = useState<SquadSize>(seeded.size)
  /**
   * 🔴 자리는 **상태**다 — 옮길 수 있어야 해서다(사용자 요청, 2026-09-08).
   * 포메이션(FORMATIONS)은 이제 「고정된 자리」가 아니라 **처음 놓이는 자리**다.
   */
  const [slots, setSlots] = useState<Slot[]>(() => seeded.slots)

  /**
   * 자리 이름 → 그 사람의 **등재 id**(`squad_member.id`).
   *
   * 🔴 **이것이 있는 자리만 서버에 저장된다.** 지인 판에서 앉힌 사람은
   * `player_card_id` 가 없어 등재가 안 되고(그 경로는 아직 없다), 등재가
   * 아니면 서버에 배치를 남길 대상이 없다 — 없는 등재에 PATCH 를 쏘면 404 다.
   */
  /* 🔴 **첫 값에서 고정된다** — 갱신 함수를 두지 않는다. 이 판이 사람을
     새로 등재하지는 않으므로(그 경로는 아직 없다) 바뀔 일이 없고, 자리
     (`mates`)와 따로 갱신되면 어느 자리가 누구의 등재인지가 어긋난다. */
  /* 🔴 **갱신 함수가 필요하다**(2026-09-16). 전에는 첫 값에 고정이었다 —
     등재는 서버가 만들고 화면은 읽기만 했기 때문이다. 이제 「나」로 앉히면
     화면이 **등재를 만든다**(`addSeat`). 돌아온 등재 id 를 여기 안 넣으면
     그 뒤로 옮기기(`saveSeat`)도 빼기(`removeSeat`)도 서버로 안 나간다. */
  const [members, setMembers] = useState<Record<string, string>>(() => seeded.members)

  /**
   * 판 배치를 서버에 남긴다 — **판이 멈추지 않게 삼킨다.**
   *
   * 🔴 **주장이 아니면 403 이다**(계약 3-7절). 판은 누구나 만져 볼 수 있고
   * 남는 것만 주장의 것이라, 실패를 화면의 고장으로 만들지 않는다. 되돌리지도
   * 않는다 — 방금 옮긴 카드가 손 밑에서 제자리로 튀는 편이 더 나쁘다.
   */
  function persist(run: () => Promise<unknown>) {
    void run().catch(() => {})
  }

  /**
   * 크기를 바꾸면 그 포메이션의 처음 자리로 놓는다.
   *
   * 🔴 **사람이 직접 정한 포지션(`pos`)은 들고 간다** — 같은 자리 이름이면
   * 그대로 옮겨 준다. 크기를 잘못 눌렀다가 되돌렸을 때 손으로 고친 것이
   * 사라지면 안 된다(앉은 사람을 안 지우는 것과 같은 이유).
   *
   * 🔴 **내 자리(`mine`)도 들고 간다**(사용자 지적, 2026-09-16: "한 번 넣고
   * 난 후에는 x 누르지 않는 이상 계속 유지"). 포메이션 상수에는 이제 `mine`
   * 이 없으므로(내 자리는 고정이 아니다) 여기서 안 옮기면 **크기를 누르는
   * 것만으로 내가 판에서 빠진다.**
   */
  function changeSize(next: SquadSize) {
    setSize(next)
    setSlots((now) => {
      const kept = new Map(now.map((sl) => [sl.area, { pos: sl.pos ?? null, mine: sl.mine }]))
      return FORMATIONS[next].slots.map((sl) => ({
        ...sl,
        pos: kept.get(sl.area)?.pos ?? null,
        mine: kept.get(sl.area)?.mine,
      }))
    })
    setMoving(null)
    if (squad) persist(() => saveFormation(squad.team_id, next))
  }

  /* 🔴 앉은 사람은 **크기가 줄어도 안 지운다**(사용자 요청). 자리 이름이
     역할+번호라(FORMATIONS 주석) 없어진 자리는 그리지 않을 뿐이고, 다시
     키우면 그대로 앉아 있다 — 실수로 눌렀을 때 잃는 것이 없다. */
  const [mates, setMates] = useState<Record<string, string | null>>(() => seeded.mates)
  /**
   * 그 자리 사람의 **카드 슬러그**. 🔴 **이름만으로는 카드를 못 그린다** —
   * 판에 앉은 사람도 제 카드가 떠야 한다(사용자 지적, 2026-09-17: 「그 사람을
   * 추가하면 그 사람 카드가 같이 실제로 떠야 하잖아」). 지인 판에서 앉힌
   * 사람은 슬러그를 모를 수 있고, 그때는 지금처럼 이름표만 그린다.
   */
  const [mateSlugs, setMateSlugs] = useState<Record<string, string | null>>(() => seeded.slugs)

  /**
   * 🔴 **그릴 때 저장소를 읽지 않는다.** 서버엔 없는 값이라 첫 그림이 서버와
   * 달라져 하이드레이션이 깨진다(공개 목록 · 카드 꾸미기에서 이미 데인 자리).
   * 그려진 다음에 한 번 읽어 얹는다.
   */
  /* 🔴 **ref 가 아니라 state 다.** ref 로 두면 되살리기와 저장이 **같은
     렌더**에서 돌아, 저장이 아직 기본값인 판을 먼저 써 버리고 StrictMode 의
     두 번째 실행이 그 덮어쓴 값을 읽는다 — 실제로 그래서 다른 화면에 갔다
     오면 늘 5:5 로 돌아갔다(실측). state 면 되살린 값이 **화면에 반영된
     다음 렌더**에서야 저장이 열린다. */
  /**
   * 내가 고른 대표 영상 — 추천 판이 목록에 나를 그릴 때 이 장면을 튼다.
   * 🔴 그릴 때 읽지 않는다(하이드레이션).
   */
  const [myClip, setMyClip] = useState<string | null>(null)
  /**
   * 🔴 **내 대표 영상도 계약으로 읽는다**(CCC 27). 전에는 `localStorage` 라
   * 다른 기기에서는 안 나왔다. 내 카드 슬러그로 부르므로 남의 판을 볼 때도
   * **같은 함수**가 그 사람 것을 준다 — 추천 판이 자리 표시 클립을 돌리던
   * 자리가 이걸로 메워진다.
   *
   * 🔴 **그릴 때 부르지 않는다**(하이드레이션) — 그려진 다음에 한 번 얹는다.
   * ⚠️ 주소는 만료되는 값이라 들고만 있고 캐시로 삼지 않는다.
   */
  const slug = card?.public_slug
  useEffect(() => {
    if (!slug) return
    let alive = true
    void loadFeaturedOf(slug).then((f) => {
      if (alive) setMyClip(f?.url ?? null)
    })
    return () => {
      alive = false
    }
  }, [slug])

  /**
   * 이름표를 눌러 고를 수 있는 **포지션 코드들** — `GET /positions` 가 정본이다
   * (CCC 28). 전에는 이 파일의 `ROW_POS` 넷이 곧 고를 수 있는 전부라,
   * 마이그레이션이 포지션을 늘려도 판은 몰랐다.
   *
   * 🔴 **`ROW_POS` 를 대신하지는 않는다.** 그쪽은 「행이 포지션 라인」이라는
   * **판의 생김새**이고 계약 3-7절이 4행으로 못박은 값이다(0 FW · 1 MF ·
   * 2 DF · 3 GK). 여기서 받는 것은 *고를 수 있는 목록*이라 서로 다른 축이다.
   *
   * 🔴 **못 받으면 판이 아는 넷으로 돈다** — 목록을 못 받았다고 이름표가
   * 안 눌리면, 서버가 잠깐 흔들릴 때 판의 기능이 사라진다.
   */
  const [posCodes, setPosCodes] = useState<PosCode[]>(ROW_POS)
  useEffect(() => {
    if (!sportCode) return
    let alive = true
    void fetchPositions(sportCode).then((list) => {
      if (alive && list.length) setPosCodes(list.map((p) => p.code as PosCode))
    })
    return () => {
      alive = false
    }
  }, [sportCode])
  /**
   * 지인 찾기에서 골라 둔 사람. 정해져 있으면 **빈 자리 버튼의 뜻이 바뀐다**
   * — 원래는 "AI 추천 열기"지만 이때는 "여기 넣기"다. 자리를 여기서 안 고르고
   * 진짜 판을 누르게 한 이유는 SquadFriends 주석에 있다.
   */
  /**
   * **팀 매칭** — 판이 다 찼을 때만 열리는 판(사용자 요청, 2026-09-10).
   *
   * 🔴 **추천 · 챗봇과 같은 첫째 칸**이라 「한 번에 하나」다 — 여는 쪽이
   * 다른 것을 닫는다(같은 좌표라 z 로는 뒤에 가려질 뿐이다).
   */
  const [matching, setMatching] = useState(false)
  /** 상대가 수락한 경기. 있으면 대기 팝업이 화면을 덮는다. */
  const [matched, setMatched] = useState<MatchTeam | null>(null)

  /**
   * 🔴 **확정되는 순간은 이 화면 바깥이다**(사용자 요청, 2026-09-16) — 신청을
   * 건 것만으로는 안 뜨고, 알림에서 수락이 확인돼야 뜬다.
   *
   * 이름 · 판을 그리려면 팀 한 벌이 필요한데 계약 응답에는 id 뿐이라
   * (`teamById` 주석) 붙박이 목록에서 찾는다. **못 찾으면 안 띄운다** —
   * 빈 판을 띄우느니 안 띄우는 편이 낫다.
   */
  useEffect(() => {
    if (!acceptedTeamId) return
    const them = teamById(acceptedTeamId)
    if (!them) return
    const team: MatchTeam = { ...them, why: [] }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMatched(team)
    /* 🔴 **브라우저에 따로 적지 않는다**(2026-09-16). 전에는 `book(team)` 으로
       localStorage 에 남겼다 — 계약에 확정 경기 자리가 없던 시절의 임시였다.
       이제 수락하면 서버에 진짜 `match` 가 생기고(계약 3-15절) 「내 경기」가
       `GET /teams/{id}/matches` 로 그것을 읽는다. 둘 다 두면 **같은 경기가
       두 번** 보인다. */
    // 팝업이 화면을 덮으므로 뒤의 명단은 접는다 — 닫았을 때 판만 남는다.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMatching(false)
  }, [acceptedTeamId])


  const [placing, setPlacing] = useState<string | null>(null)
  /** 고른 지인의 카드 슬러그 — 앉히는 순간 그 자리로 옮겨 간다(미결 `paik` 39번). */
  const [placingSlug, setPlacingSlug] = useState<string | null>(null)
  /** 고른 지인의 `user_id` — **초대를 보내려면 이것이 있어야 한다**(계약 49). */
  const [placingUserId, setPlacingUserId] = useState<string | null>(null)
  /**
   * 그 자리에 보낸 **초대 id**.
   *
   * 🔴 **앉힌 사람이 사라지지 않는 이유가 이것이다**(사용자 설계, 2026-09-17).
   * 판에 앉히면 초대가 서버에 남고, 새로고침하면 `GET /teams/{id}/invitations`
   * 로 되살아난다. **사라지는 것은 상대가 거절하거나 주장이 ⊗ 를 눌러 무를
   * 때뿐**이다.
   */
  const [invites, setInvites] = useState<Record<string, string>>({})
  // 지인 찾기 판이 DOM 에 있는가 — 닫힐 때 물러나는 동안 남아 있어야 한다.
  const [friendVisible, setFriendVisible] = useState(false)
  /**
   * 지금 끌고 있는 자리와 손가락이 움직인 거리.
   *
   * 🔴 **끄는 것만 옮기는 손짓이다**(누르기가 아니다). 카드를 누르는 뜻은
   * 그대로 둔다 — 빈 카드는 추천 열기, 앉은 카드는 빼기. 누르기를 옮기기로
   * 바꾸면 그 둘이 갈 데가 없어지고, 카드가 이미 `<button>` 이라 그 안에
   * 또 버튼을 둘 수도 없다.
   */
  const [moving, setMoving] = useState<{ area: string; dx: number; dy: number } | null>(null)
  /** 끄는 동안 눌린 것으로 치지 않는다 — 놓는 순간 click 이 뒤따라 온다. */
  const draggedRef = useRef(false)
  const dragFromRef = useRef<{ x: number; y: number } | null>(null)
  const boardRef = useRef<HTMLDivElement>(null)

  /** 손가락이 이만큼 움직여야 "끈 것"으로 본다. 손떨림을 누르기로 살린다. */
  const DRAG_MIN = 6

  /**
   * 화면 좌표에서 가장 가까운 격자 칸을 찾는다.
   *
   * 🔴 `elementFromPoint` 를 쓰지 않는다 — 끌고 있는 카드가 손가락 밑에 있어서
   * 늘 자기 자신이 잡힌다. 칸의 중심과의 거리로 고른다.
   */
  function cellAt(x: number, y: number): { col: number; row: number } | null {
    const board = boardRef.current
    if (!board) return null
    const cells = [...board.querySelectorAll('.ss-squad-cell')] as HTMLElement[]
    if (!cells.length) return null
    let best: { col: number; row: number } | null = null
    let bestD = Infinity
    for (const el of cells) {
      const c = el.getBoundingClientRect()
      const d = (c.left + c.width / 2 - x) ** 2 + (c.top + c.height / 2 - y) ** 2
      if (d < bestD) {
        bestD = d
        best = { col: Number(el.dataset.col), row: Number(el.dataset.row) }
      }
    }
    return best
  }

  /**
   * 자리를 옮긴다. 그 칸에 다른 자리가 있으면 **서로 바꾼다** — 밀어내면
   * 밀린 쪽이 어디로 갈지 정할 규칙이 또 필요하고, 바꾸는 편이 짐작대로다.
   */
  function moveTo(area: string, col: number, row: number) {
    const me = slots.find((sl) => sl.area === area)
    if (!me || (me.col === col && me.row === row)) return
    /* 🔴 **없는 칸으로는 못 간다** — 골키퍼 줄의 양옆이 그것이다. 한 곳에서
       막아야 끌기 · 방향키 · 앞으로 생길 길이 다 같이 걸린다. */
    if (!cellExists(col, row)) return
    const other = slots.find((sl) => sl.col === col && sl.row === row)
    const next = slots.map((sl) => {
      if (sl.area === area) return { ...sl, col, row }
      if (other && sl.area === other.area) return { ...sl, col: me.col, row: me.row }
      return sl
    })
    setSlots(next)
    /* 🔴 **자리를 맞바꾸면 둘 다 저장한다.** 옮긴 쪽만 보내면 밀려난 사람의
       칸이 서버에서 옛 자리에 남아, 다음에 열 때 두 카드가 한 칸에 겹친다. */
    saveCells(next, other ? [area, other.area] : [area])
  }

  /**
   * 자리들의 **칸과 포지션**을 서버에 남긴다 — 등재된 사람이 앉은 자리만.
   *
   * 🔴 **다음 값을 받아서** 쓴다. 지금 상태를 다시 읽으면 **한 걸음 뒤처진
   * 칸**을 보낸다 — 홈의 휠 처리기와 대표 영상 지우기에서 두 번 데인 자리다.
   * 🔴 **상태 갱신 함수 안에서 부르지 않는다.** 그쪽은 순수해야 하고,
   * StrictMode 는 그 함수를 한 번 더 돌린다 — 같은 PATCH 가 두 번 나간다.
   */
  function saveCells(next: Slot[], areas: string[]) {
    if (!squad) return
    for (const area of areas) {
      const memberId = members[area]
      // 등재가 아닌 자리(지인 판에서 앉힌 사람 · 내 자리)는 서버에 남길 것이 없다.
      if (!memberId) continue
      const sl = next.find((x) => x.area === area)
      if (!sl) continue
      persist(() => saveSeat(squad.team_id, memberId, posOf(sl), { col: sl.col, row: sl.row }))
    }
  }

  /** 내가 지금 판에 서 있는 자리. 없으면 **안 뛰는 것**이다. */
  const mySeat = slots.find((sl) => sl.mine) ?? null

  /**
   * **나를 이 자리에 앉힌다.**
   *
   * 🔴 **정정 (2026-09-17, 사용자 판단).** 하루 전에는 「처음 판은 비어 있고,
   * 빈 자리를 눌러 뜨는 **「나」 표식**을 눌러야 내 카드가 선다」였다. 그
   * 표식을 **없앴다** — 팀을 만든 사람은 **뛴다고 보고 FW 에 먼저 앉힌다**
   * (아래 자동 착석). 옮기든 빼든 그건 그다음 일이고, **일단 앉혀 놓고**
   * 시작하는 것이 판을 처음 여는 사람에게 자연스럽다.
   *
   * 이 함수는 그대로 남는다 — 자동 착석이 이것을 부른다.
   */
  function seatMe(area: string) {
    if (mySeat || !myCardId) return
    const next = slots.map((sl) => (sl.area === area ? { ...sl, mine: true } : sl))
    setSlots(next)
    setPicking(null)
    /* 🔴 **지인 찾기 판도 같이 닫는다**(사용자 지적, 2026-09-16). 추천 판은
       `picking` 이 null 이 되며 닫히는데 지인 판은 `scouting` 이 쥐고 있어
       혼자 남았다 — 자리를 정하고 나면 둘 다 볼 일이 없다. 한 단추가 연
       한 벌이므로 닫는 것도 한 번이다. */
    onCloseScouting?.()
    const sl = next.find((x) => x.area === area)
    if (squad && sl) {
      /* 🔴 **돌아온 등재 id 를 잇는다.** 안 이으면 방금 앉은 내 카드를 옮기거나
         빼도 서버로 아무것도 안 나간다 — 새로고침해야 이어졌다. */
      persist(async () => {
        const next2 = await addSeat(squad.team_id, {
          playerCardId: myCardId,
          positionCode: posOf(sl),
          cell: { col: sl.col, row: sl.row },
        })
        const mine = next2.members.find((m) => m.player_card_id === myCardId)
        if (mine) setMembers((prev) => ({ ...prev, [area]: mine.id }))
      })
    }
  }

  /**
   * 판에 앉은 사람들의 **진짜 카드** (2026-09-17, 사용자 지적).
   *
   * 🔴 전에는 이름만 적은 빈 카드를 그렸다 — 「그 사람을 추가하면 그 사람
   * 카드가 같이 실제로 떠야」 한다. 슬러그를 아는 사람만 받아 온다(지인 판에서
   * 앉힌 사람은 슬러그가 없을 수 있고, 그때는 이름표만 그린다).
   *
   * 🔴 **슬러그로 캐시한다** — 같은 사람을 자리만 옮겨도 다시 받지 않는다.
   * 🔴 **실패는 조용히 넘긴다.** 카드가 없거나 못 읽으면 이름표로 남는 것이
   * 맞다 — 판이 통째로 안 뜨는 것보다 낫다.
   */
  const [mateCards, setMateCards] = useState<Record<string, PublicPlayerCard>>({})
  useEffect(() => {
    const want = Object.values(mateSlugs).filter(
      (slug): slug is string => !!slug && !(slug in mateCards),
    )
    if (want.length === 0) return
    let alive = true
    void Promise.all(
      want.map(async (slug) => {
        try {
          const res = await fetch(`/api/cards/${encodeURIComponent(slug)}`)
          if (!res.ok) return null
          const body = (await res.json()) as unknown
          /* 🔴 **카드 모양인지 보고 받는다.** 아니면 그리지 않는다 — 엉뚱한
             것이 카드 자리에 들어가면 `PlayerCardView` 가 없는 값을 읽다가
             **판이 통째로 안 그려진다**(시험 대역이 그걸 실제로 드러냈다).
             못 알아보면 이름표로 남는 것이 맞다. */
          if (
            !body ||
            typeof body !== 'object' ||
            typeof (body as PublicPlayerCard).public_slug !== 'string' ||
            !(body as PublicPlayerCard).user
          ) {
            return null
          }
          return [slug, body as PublicPlayerCard] as const
        } catch {
          return null
        }
      }),
    ).then((got) => {
      if (!alive) return
      const add = got.filter((x): x is readonly [string, PublicPlayerCard] => x !== null)
      if (add.length > 0) setMateCards((prev) => ({ ...prev, ...Object.fromEntries(add) }))
    })
    return () => {
      alive = false
    }
  }, [mateSlugs, mateCards])

  /**
   * **그 자리로 초대를 보낸다** (계약 49·53, 2026-09-17).
   *
   * 🔴 **동의 없이 꽂지 않는다**(2026-09-10 박민호 결정) — 그 사람이 수락해야
   * 팀원이 된다. 그때까지 카드 위에 「수락 대기중」이 붙는다.
   *
   * 🔴 **부르는 자리를 함께 보낸다**(`position_code`) — 그래야 새로고침해도
   * **어느 칸**에 앉혔는지가 살아난다.
   *
   * ⚠️ 팀이 아직 없으면 보낼 데가 없다 — 화면에만 앉는다(그 자리는 새로고침
   * 하면 사라진다). 팀을 만들면 그때부터 남는다.
   */
  async function invite(slot: Slot, userId: string) {
    if (!myTeamId) return
    try {
      const made = await apiPost<{ id: string }>(
        `/api/teams/${encodeURIComponent(myTeamId)}/invitations`,
        { invited_user_id: userId, position_code: posOf(slot) },
      )
      setInvites((prev) => ({ ...prev, [slot.area]: made.id }))
    } catch {
      /* 🔴 **화면에서 지우지 않는다.** 이미 앉은 것을 걷으면 사람이 방금 한
         일이 사라진 것처럼 보인다 — 초대가 안 나갔을 뿐이라 ⊗ 로 빼면 된다.
         (같은 사람에게 이미 보낸 초대가 있으면 `409` 다.) */
    }
  }

  /**
   * **보낸 초대를 무른다** — ⊗ 를 누를 때(계약 49).
   *
   * 🔴 사라지는 길은 **이것과 상대의 거절 둘뿐**이다(사용자 설계). 그래서
   * 화면에서 지우기 전에 서버로 먼저 보낸다 — 실패하면 그대로 둔다.
   */
  async function cancelInvite(area: string) {
    const id = invites[area]
    if (!myTeamId || !id) return
    try {
      await apiDelete(
        `/api/teams/${encodeURIComponent(myTeamId)}/invitations/${encodeURIComponent(id)}`,
      )
    } catch {
      /* 이미 답이 났으면 409 다 — 그때는 아래 복원이 곧 맞춰 준다. */
    }
    setInvites((prev) => {
      const next = { ...prev }
      delete next[area]
      return next
    })
  }

  /**
   * **판을 되살린다** — 보낸 초대 중 **아직 대기 중인 것**을 자리에 앉힌다.
   *
   * 🔴 이것이 「앉혀 두면 남는다」를 실제로 만드는 자리다(사용자 설계,
   * 2026-09-17). 거절·무르기로 끝난 초대는 `status` 가 `pending` 이 아니라
   * 여기서 빠지고, 그래서 **그 자리가 비워진다.**
   */
  useEffect(() => {
    if (!myTeamId) return
    let alive = true
    void (async () => {
      try {
        const res = await fetch(
          `/api/teams/${encodeURIComponent(myTeamId)}/invitations`,
        )
        if (!res.ok || !alive) return
        const rows = ((await res.json().catch(() => null)) ?? []) as {
          id: string
          status: string
          position_code: string | null
          invited_user_nickname: string | null
          invited_user_card_slug: string | null
        }[]
        const pending = rows.filter((r) => r.status === 'pending')
        if (pending.length === 0 || !alive) return
        setSlots((now) => {
          const nextMates: Record<string, string | null> = {}
          const nextSlugs: Record<string, string | null> = {}
          const nextInvites: Record<string, string> = {}
          for (const r of pending) {
            if (!r.invited_user_nickname) continue
            /* 자리를 안 정한 초대는 빈 칸 아무 데나 앉힌다 — 「우리 팀에
               오세요」도 정상 초대라 판에서 빠뜨리지 않는다. */
            const seat =
              now.find((sl) => posOf(sl) === r.position_code && !nextMates[sl.area]) ??
              now.find((sl) => !sl.mine && !nextMates[sl.area])
            if (!seat) continue
            nextMates[seat.area] = r.invited_user_nickname
            nextSlugs[seat.area] = r.invited_user_card_slug
            nextInvites[seat.area] = r.id
          }
          setMates((prev) => ({ ...prev, ...nextMates }))
          setMateSlugs((prev) => ({ ...prev, ...nextSlugs }))
          setInvites((prev) => ({ ...prev, ...nextInvites }))
          return now
        })
      } catch {
        /* 못 읽어도 판은 그대로 돈다 — 되살리기만 못 한다. */
      }
    })()
    return () => {
      alive = false
    }
  }, [myTeamId])

  /** 이름표를 눌러 포지션을 직접 정한다 — 한 번에 한 칸씩 돈다(자동 포함). */
  function cyclePos(area: string) {
    const next = slots.map((sl) => {
      if (sl.area !== area) return sl
      const order: (PosCode | null)[] = [...posCodes, null]
      const at = order.indexOf(sl.pos ?? null)
      return { ...sl, pos: order[(at + 1) % order.length] }
    })
    setSlots(next)
    /* 자동(`null`)으로 돌아와도 저장한다 — 그때 서버로 가는 값은 **행이 정한
       포지션**(`posOf`)이다. 계약은 `position_code` 를 늘 요구하고, 등재가
       포지션 없이 존재하지 않기 때문이다. */
    saveCells(next, [area])
  }

  // 지금 추천을 열어 둔 자리. null 이면 닫혀 있다.
  const [picking, setPicking] = useState<Slot | null>(null)
  // 닫히는 중인 자리 — 물러나는 동안 DOM 에 남겨 둬야 애니메이션이 보인다.
  const [closing, setClosing] = useState<Slot | null>(null)
  const timer = useRef(0)

  /**
   * 🔴 **팀을 만든 사람은 FW 에 먼저 앉는다** (2026-09-17, 사용자 판단).
   *
   * 「나」 표식(빈 자리를 눌러 내 카드를 세우던 핀)을 없애고 대신 이것을 둔다 —
   * **팀장은 뛴다고 보고 일단 앉혀 놓고 시작한다.** 옮기는 것도 빼는 것도
   * 그다음 일이다.
   *
   * 🔴 **FW 가 차 있으면 빈 자리에 앉는다** — 남을 밀어내지는 않는다. 팀이
   * 아직 없으면(등재 없음) 화면에만 앉고 `seatMe` 가 서버 저장을 건너뛴다.
   *
   * 🔴 **세션 안에서 한 번만**(`autoSeated`). 지금은 내 카드에 ⊗ 가 없어
   * 스스로 빠질 일이 없지만, 판이 비는 다른 길(크기 바꾸기 · 늦게 온 응답)에서
   * 이 효과가 다시 돌면 **서버로 같은 등재가 두 번** 나간다.
   *
   * ⚠️ 새로고침하면 서버에 남은 등재를 읽어 그 자리에 선다 — 자동 착석이
   * `addSeat` 로 저장하기 때문이다. 판이 진짜로 비어 있을 때만 다시 앉는다.
   */
  const autoSeated = useRef(false)
  useEffect(() => {
    if (autoSeated.current) return
    if (!myCardId || mySeat) return
    /* 🔴 **FW 가 먼저, 차 있으면 빈 자리 아무 데나.** 「무조건 뛴다」가 전제라
       남이 이미 앉아 있어도 나는 판에 선다 — 다만 남을 밀어내지는 않는다.
       빈 자리가 하나도 없으면 아무것도 안 한다(그때는 판이 이미 다 찼다). */
    const fw = slots.find((sl) => sl.area === 'fw1')
    const seat =
      fw && !mates[fw.area] ? fw : slots.find((sl) => !mates[sl.area] && !sl.mine)
    if (!seat) return
    autoSeated.current = true
    /* 규칙은 effect 안의 setState 를 싫어하지만, 여기서 바꾸는 것은 **처음
       한 번의 초기 상태**다 — `autoSeated` 가 막아서 연쇄가 안 생긴다. 판을
       그린 뒤에 앉히는 것이 아니라 **앉은 판을 처음부터** 그리는 것이 뜻이다. */
    // eslint-disable-next-line react-hooks/set-state-in-effect
    seatMe(seat.area)
    // `seatMe` 는 렌더마다 새로 만들어지는 함수라 넣으면 매번 다시 돈다 —
    // 위 `autoSeated` 가 한 번만 돌게 막는다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [squad, myCardId, mySeat, slots, mates])

  const friendTimer = useRef(0)
  useEffect(() => () => {
    clearTimeout(timer.current)
    clearTimeout(friendTimer.current)
  }, [])

  // 지인 찾기가 켜지면 바로 띄우고, 꺼지면 물러나는 시간만큼 남겨 둔다.
  // 고르던 사람도 같이 지운다 — 판이 없는데 자리만 깜빡이면 안 된다.
  useEffect(() => {
    if (scouting) {
      clearTimeout(friendTimer.current)
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setFriendVisible(true)
      return
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPlacing(null)
    setPlacingUserId(null)
    // 고른 사람의 슬러그도 같이 놓는다 — 판이 닫혔는데 남아 있으면 다음에
    // 앉히는 사람에게 **앞 사람 카드**가 붙는다.
    setPlacingSlug(null)
    friendTimer.current = window.setTimeout(() => setFriendVisible(false), SUGGEST_EXIT_MS)
    return () => clearTimeout(friendTimer.current)
  }, [scouting])

  /**
   * **판이 다 찼는가** — 「팀 매칭」이 켜지는 조건이다(사용자 요청).
   *
   * 🔴 **내 자리도 한 자리로 센다.** 거기는 `card` 가 그려서 `mates` 에 안
   * 들어가지만, 판 위에 선 사람인 것은 같다 — 안 세면 5:5 를 다 채워도
   * 넷으로 세어 단추가 영영 안 켜진다.
   * 🔴 **크기와 무관하다**(사용자 결정) — 3:3 으로 할지 7:7 로 할지는 팀장이
   * 정하는 것이라, 고른 크기가 다 차면 켜진다.
   *
   * 🔴 **「팀원」일 때는 아니다**(사용자 지적, 2026-09-10). 그쪽은 *남의 팀에
   * 들어가는* 자리라 우리 팀이 상대를 찾을 일이 없다 — 판도 물러나 있어서
   * 「다 찼다」가 화면에 보이지도 않는다.
   */
  /* 🔴 **다 찼고 + 모두 수락했을 때**만 켜진다(사용자 지정, 2026-09-16).
     전에는 자리만 차면 켜졌는데, 그러면 아직 아무도 오기로 안 한 판으로
     상대 팀에 경기를 신청하게 된다 — 「수락 대기중」이 남아 있는 판은
     아직 팀이 아니다.
     ⚠️ **내 자리는 수락을 안 본다** — 내가 나를 부른 것이라 기다릴 것이 없다. */
  const full =
    !seeking &&
    slots.every((slot) => slot.mine || (Boolean(mates[slot.area]) && seeded.ready[slot.area]))

  /**
   * 용병 찾기로 열 때 **어느 자리의 추천**을 낼 것인가 — 빈 자리 중 첫
   * 번째다(FW → MF → MF → DF → GK). 이 순서는 판 위에서 위에서 아래로
   * 읽히는 순서라, "지금 가장 급한 자리"로 그대로 읽힌다.
   * 다 찼으면 마지막 자리를 낸다 — 판이 안 열리는 것보다 낫다(빼고 나서
   * 다시 누를 필요가 없다).
   */
  const firstEmpty =
    slots.find((slot) => !slot.mine && !mates[slot.area]) ?? slots[slots.length - 1]

  /* 알약이 켜지면 추천 판도 같이 연다. 🔴 **자리를 여기서 다시 고르지
     않는다** — 빈 자리를 직접 눌러 연 뒤(picking 이 이미 있다) 알약 상태가
     바뀌었다고 그 자리를 첫 빈 자리로 되돌리면, 방금 고른 자리가 사라진다. */
  useEffect(() => {
    clearTimeout(timer.current)
    if (scouting) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setClosing(null)
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setPicking((now) => now ?? firstEmpty)
      return
    }
    // 꺼지면 추천 판도 같이 접는다 — 한 단추가 연 한 벌이다.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPicking((now) => {
      if (now) {
        setClosing(now)
        timer.current = window.setTimeout(() => setClosing(null), SUGGEST_EXIT_MS)
      }
      return null
    })
    // firstEmpty 는 자리가 채워질 때마다 새 값이 된다 — 넣을 때마다 판이
    // 다시 열리면 안 되므로 켜고 끄는 순간만 본다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scouting])

  /**
   * 🔴 **챗봇이 켜지면 추천 판을 닫는다** — 둘은 **첫째 칸**을 나눠 쓴다.
   *
   * ⚠️ 빈 자리를 눌러 연 추천은 `scouting` 이 아니라 이 판이 제 상태
   * (`picking`)로 들고 있다. 그래서 알약으로 연 경우만 닫히고, **빈 자리로
   * 연 경우에는 AI 판이 그 뒤에 나왔다**(사용자 지적) — 같은 좌표라 z 로는
   * 가려질 뿐이다. 여는 쪽이 닫는다는 규칙을 이 길에도 건다.
   *
   * 빈 자리 누르기 쪽에도 `onBotChange?.(false)` 가 있어 **양쪽이 서로를
   * 닫는다** — 어느 쪽을 먼저 눌러도 첫째 칸에는 하나만 선다.
   */
  useEffect(() => {
    if (!bot) return
    clearTimeout(timer.current)
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPicking((now) => {
      if (now) {
        setClosing(now)
        timer.current = window.setTimeout(() => setClosing(null), SUGGEST_EXIT_MS)
      }
      return null
    })
  }, [bot])

  function close() {
    setClosing(picking)
    setPicking(null)
    clearTimeout(timer.current)
    timer.current = window.setTimeout(() => setClosing(null), SUGGEST_EXIT_MS)
    // 🔴 알약으로 연 한 벌이면 **둘 다** 접는다. 추천만 닫고 지인 판을
    // 남기면, 알약은 아직 켜진 것으로 남아 다시 눌러도 안 열린다.
    onCloseScouting?.()
  }

  // 열려 있는 동안 Esc 로 닫는다 — 바깥을 누르는 것과 같은 자리에 둔다.
  useEffect(() => {
    if (!picking) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') close()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  })

  /**
   * 이미 판에 들어가 있는 사람 → 그 자리 이름. 지인 목록이 이걸로 "여기
   * 있음" 표식을 붙이고 다시 못 고르게 막는다 — 없으면 같은 사람을 두 자리에
   * 넣을 수 있다.
   */
  const placed = Object.fromEntries(
    slots.flatMap((slot) => {
      const name = mates[slot.area]
      return name ? [[name, posOf(slot)] as const] : []
    }),
  )

  /* 🔴 전에는 두 판이 **같은 자리**라 지인 찾기가 열려 있는 동안 추천을
     아예 안 그렸다. 이제 칸이 둘이라(위 주석) 같이 뜬다 — 그 막음을 걷어냈다.
     첫째 칸을 챗봇과 나눠 쓰는 것은 그대로다(챗봇을 켜면 추천이 닫힌다). */
  const shown = picking ?? closing

  return (
    /* 🔴 추천 판은 스쿼드 판의 **형제**다. 스쿼드 판이 overflow: hidden
       이라(모서리 밖으로 나가는 것을 자르려고) 자식으로 두면 판 밖으로
       나간 부분이 통째로 잘린다 — 실제로 그렇게 안 보였다. 자리 잡기는
       이 바깥 상자가 맡고, 두 판은 그 안에서 좌표를 잡는다. */
    <div className="ss-squad-wrap">
      {/* 유리 굴절(warp) — backdrop-filter 는 흐림·채도만 다루고 뒤 배경을
          휘게 하지는 못한다. 그건 SVG 필터의 몫이다: 부드러운 잡음
          (feTurbulence)을 만들고 그만큼 픽셀을 밀어(feDisplacementMap)
          두께 있는 유리를 통과한 것처럼 만든다. 세기(scale)는 실측으로
          골랐다 — 7 이면 화면의 9.7%가 달라지고(최대차 19), 15 면 18.4%
          (최대차 31)로 뒤 연기가 또렷하게 일렁인다. seed 를 고정해 두어
          새로고침해도 같은 무늬가 나온다. width/height 0 이라 자리를
          차지하지 않는다 — 정의만 두는 자리다. */}
      <svg width="0" height="0" aria-hidden="true" focusable="false" className="absolute">
        <filter
          id="ss-squad-warp"
          x="-10%"
          y="-10%"
          width="120%"
          height="120%"
          colorInterpolationFilters="sRGB"
        >
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.006 0.01"
            numOctaves="2"
            seed="4"
            result="warp"
          />
          <feDisplacementMap
            in="SourceGraphic"
            in2="warp"
            scale="15"
            xChannelSelector="R"
            yChannelSelector="G"
          />
        </filter>
      </svg>

      {/* 🔴 **팀원 판은 스쿼드 판을 대신 선다**(사용자 요청, 2026-09-08).
          같은 자리를 쓰므로 `.ss-squad-wrap` 안에서 좌표를 다시 잴 것이 없고,
          오른쪽에 붙는 판들(추천 · 지인 · 챗봇)의 기준점도 그대로다. */}
      {seeking && (
        <TeamSeek closing={false} onClose={() => onCloseSeeking?.()} sportCode={sportCode} />
      )}

      <section
        className="ss-squad"
        aria-label="내 스쿼드"
        /* 🔴 **`hidden` 이 아니라 표시만 남긴다.** 통째로 빼면 자리가 접혀서
           팀원 판이 설 크기를 잃는다 — 스쿼드 판의 크기는 카드 폭 · 칸 간격
           에서 계산되는 값이라(globals.css) 그 숫자를 여기 베껴 오면 카드
           크기를 바꾸는 순간 둘이 어긋난다. CSS 가 `visibility` 로 감추므로
           **자리는 그대로 남고 접근성 트리에서는 빠진다.** */
        data-seeking={seeking ? 'true' : undefined}
        // 🔴 backdrop-filter 는 **인라인으로** 준다. globals.css 에 두면
        // 같은 규칙의 color-mix() 때문에 Lightning CSS 가 @supports 로
        // 쪼개는 과정에서 통째로 떨어뜨린다(추천 판에서 실제로 그렇게
        // 날아갔다 — 계산값 none). 흐림 없이 굴절만 건다.
        style={{
          backdropFilter: 'url(#ss-squad-warp)',
          WebkitBackdropFilter: 'url(#ss-squad-warp)',
        }}
      >
      {/* 반짝임의 **시계**가 여기 하나 있다 — 자리마다 걸면 위상이 어긋난다
          (globals.css 의 --ss-beckon-t 주석 참고). */}
      {/* 🔴 배치는 CSS 가 `data-size` 로 고른다 — grid-template-areas 를 인라인
          으로 주면 자리 이름이 두 곳(여기와 globals.css)에 살게 된다. */}
      <div
        ref={boardRef}
        className="ss-squad-board"
        data-size={size}
        data-moving={moving ? 'true' : undefined}
        data-placing={placing ? 'true' : undefined}
      >
        {/* 머리글이 경기장 선 **안쪽**에 앉아야 한다 — 판 위쪽에 따로
            두면 선 밖으로 나간다. 선을 그리는 상자 안에 넣고 위 여백을
            그만큼 준다(globals.css). */}
        <header className="ss-squad-head">
          {/* 🔴 **팀이 있으면 그 이름이 머리글이다**(위 `teamName` 주석).
              없을 때만 「MY SQUAD」다 — 팀을 만들면 이 글자가 바뀌는 것이
              곧 「생겼다」는 신호이기도 하다.

              ⚠️ 이름이 길 수 있다(계약에 상한이 없다). 한 줄로 자르고
              말줄임한다 — 안 그러면 오른쪽 크기 단추(3:3·5:5·7:7)를 밀어낸다.
              `title` 을 달아 잘린 이름도 가리키면 읽을 수 있게 둔다. */}
          <h2
            className={teamName ? 'ss-squad-title--team' : undefined}
            title={teamName ?? undefined}
          >
            {teamName ?? 'MY SQUAD'}
          </h2>
          {/* 🔴 「풋살 5인」이라고 **적어 두기만** 하던 자리다 — 이제 고를 수
              있다(사용자 요청, 2026-09-08). 판의 배치가 같이 바뀐다.
              라디오처럼 하나만 골라진다 — 판이 동시에 두 크기일 수는 없다. */}
          <div className="ss-squad-size" role="radiogroup" aria-label="판 크기">
            {(Object.keys(FORMATIONS) as SquadSize[]).map((key) => (
              <button
                key={key}
                type="button"
                role="radio"
                aria-checked={size === key}
                className="ss-squad-size-btn"
                data-on={size === key ? 'true' : undefined}
                onClick={() => changeSize(key)}
              >
                {FORMATIONS[key].label}
              </button>
            ))}
          </div>
        </header>

        {/* 경기장 선 — 장식이라 스크린리더에서 숨긴다. preserveAspectRatio
            를 none 으로 두어 판이 어떤 비율이 되든 선이 판을 꽉 채운다
            (원은 그만큼 타원이 되지만, 배경 장식이라 그편이 낫다 —
            비율을 지키면 위아래에 선 없는 빈 띠가 생긴다). */}
        <svg
          className="ss-squad-pitch"
          viewBox="0 0 100 140"
          preserveAspectRatio="none"
          aria-hidden="true"
          focusable="false"
        >
          {/* 🔴 **바깥 테두리만 온전한 흰색이다**(사용자 요청, 2026-09-08).
              판의 경계라 흐리면 판이 어디까지인지 안 보인다. 안쪽 선들
              (하프라인 · 센터서클 · 페널티/골 에어리어)은 카드가 얹히는
              바탕이라 30% 로 물린다 — 아래 `.ss-squad-pitch` 주석. */}
          <rect className="ss-squad-pitch-edge" x="1" y="1" width="98" height="138" />
          <line x1="1" y1="70" x2="99" y2="70" />
          <circle cx="50" cy="70" r="14" />
          <circle className="ss-squad-pitch-dot" cx="50" cy="70" r="1.2" />
          <rect x="27" y="1" width="46" height="20" />
          <rect x="38" y="1" width="24" height="9" />
          <rect x="27" y="119" width="46" height="20" />
          <rect x="38" y="130" width="24" height="9" />
        </svg>

        {/* 🔴 **격자 칸**. 늘 열두 개를 그려 둔다 — 카드를 끌 때 어디에 놓을
            수 있는지 보여 주는 자리이자, 놓을 때 가장 가까운 칸을 찾는 기준이다
            (`cellAt`). 끌지 않는 동안에는 아무것도 안 그리고 손짓도 안 받는다. */}
        {Array.from({ length: ROWS * COLS }, (_, i) => {
          const col = i % COLS
          const row = Math.floor(i / COLS)
          // 🔴 골키퍼 줄의 양옆은 **아예 안 그린다** — 그리면 `cellAt` 이
          // 거기로 놓을 수 있는 자리로 센다.
          if (!cellExists(col, row)) return null
          const taken = slots.some((sl) => sl.col === col && sl.row === row)
          return (
            <span
              key={`cell-${i}`}
              className="ss-squad-cell"
              data-col={col}
              data-row={row}
              data-free={!taken ? 'true' : undefined}
              aria-hidden="true"
              style={{ gridColumn: col + 1, gridRow: row + 1 }}
            />
          )
        })}

        {slots.map((slot) => {
          const name = mates[slot.area] ?? null
          const held = moving?.area === slot.area
          return (
            <div
              key={slot.area}
              className="ss-squad-seat"
              data-mine={slot.mine ? 'true' : undefined}
              data-held={held ? 'true' : undefined}
              style={{
                gridColumn: slot.col + 1,
                gridRow: slot.row + 1,
                ...(held
                  ? ({
                      transform: `translate(${moving.dx}px, ${moving.dy}px)`,
                    } as React.CSSProperties)
                  : null),
              }}
              /* 🔴 **끄는 것이 옮기는 손짓이다.** 누르는 뜻(빈 카드=추천 열기 ·
                 앉은 카드=빼기)은 그대로 둔다. 손가락이 DRAG_MIN 만큼 움직여야
                 끈 것으로 보고, 그 경우에만 뒤따라오는 click 을 삼킨다. */
              onPointerDown={(e) => {
                if (e.button !== 0) return
                dragFromRef.current = { x: e.clientX, y: e.clientY }
                draggedRef.current = false
              }}
              onPointerMove={(e) => {
                const from = dragFromRef.current
                if (!from) return
                const dx = e.clientX - from.x
                const dy = e.clientY - from.y
                if (!draggedRef.current && Math.hypot(dx, dy) < DRAG_MIN) return
                /* 🔴 포인터를 **여기서** 잡는다 — 누르는 순간이 아니다.
                   누를 때 잡으면 `pointerup` 이 이 상자로 재지정되고, 그러면
                   click 의 과녁이 안쪽 `<button>` 이 아니라 이 상자가 되어
                   **빼기(⊗)도 추천 열기(+)도 통째로 안 눌린다**(사용자 지적).
                   ⚠️ jsdom 은 잡기를 시늉만 하므로 이 결함을 못 잡는다 —
                   시험이 통과했는데도 실물에서 안 눌렸다. */
                if (!draggedRef.current) {
                  draggedRef.current = true
                  e.currentTarget.setPointerCapture(e.pointerId)
                }
                setMoving({ area: slot.area, dx, dy })
              }}
              onPointerUp={(e) => {
                dragFromRef.current = null
                if (!draggedRef.current) return
                if (e.currentTarget.hasPointerCapture?.(e.pointerId)) {
                  e.currentTarget.releasePointerCapture(e.pointerId)
                }
                const cell = cellAt(e.clientX, e.clientY)
                if (cell) moveTo(slot.area, cell.col, cell.row)
                setMoving(null)
              }}
              onPointerCancel={() => {
                dragFromRef.current = null
                draggedRef.current = false
                setMoving(null)
              }}
              /* 🔴 끌 수 없는 입력 장치의 길 — 카드에 초점을 두고 방향키로
                 옮긴다. `preventDefault` 를 해야 화면이 같이 굴러가지 않는다. */
              onKeyDown={(e) => {
                const step: Record<string, [number, number]> = {
                  ArrowLeft: [-1, 0],
                  ArrowRight: [1, 0],
                  ArrowUp: [0, -1],
                  ArrowDown: [0, 1],
                }
                const d = step[e.key]
                if (!d) return
                e.preventDefault()
                moveTo(
                  slot.area,
                  Math.min(COLS - 1, Math.max(0, slot.col + d[0])),
                  Math.min(ROWS - 1, Math.max(0, slot.row + d[1])),
                )
              }}
              /* 끈 뒤에 오는 click 하나를 삼킨다 — 놓자마자 추천이 열리거나
                 그 사람이 빠지면 안 된다. */
              onClickCapture={(e) => {
                if (!draggedRef.current) return
                e.stopPropagation()
                e.preventDefault()
                draggedRef.current = false
              }}
            >
              {slot.mine ? (
                /* 🔴 **내 카드에는 ⊗ 가 없다**(사용자 판단, 2026-09-17).
                   팀을 만든 사람은 **뛴다는 가정**이라 판에서 빠질 일이
                   없다 — 뺄 수 있게 두면 「안 뛴다」가 표현되는데, 그것을
                   담을 자리가 서버에도 없다. 옮기는 것은 그대로 된다
                   (끌어서 다른 칸으로). 남의 카드는 아래에서 ⊗ 로 뺀다. */
                <div className="ss-pcard-mini">
                  {card ? (
                    <PlayerCardView card={card} />
                  ) : (
                    <BlankPlayerCard>
                      <p className="ss-squad-note">아직 카드가 없습니다</p>
                    </BlankPlayerCard>
                  )}
                </div>
              ) : name ? (
                /* 앉은 남의 카드도 같은 규칙 — 카드는 그림이고 ⊗ 만 뺀다. */
                <>
                  <div className="ss-pcard-mini">
                    {/* 🔴 **그 사람의 진짜 카드를 그린다**(2026-09-17). 슬러그를
                        모르거나(지인 판) 아직 못 받았으면 이름표로 남는다 —
                        빈 카드에 이름만 찍혀 있던 것이 여기다. */}
                    {(() => {
                      const slug = mateSlugs[slot.area]
                      const theirs = slug ? mateCards[slug] : undefined
                      return theirs ? (
                        <PlayerCardView card={theirs} />
                      ) : (
                        <BlankPlayerCard>
                          <p className="ss-squad-name">{name}</p>
                        </BlankPlayerCard>
                      )
                    })()}
                  </div>
                  <button
                    type="button"
                    className="ss-squad-remove material-symbols-outlined"
                    aria-label={`${name} 빼기`}
                    onClick={() => {
                      setMates((prev) => ({ ...prev, [slot.area]: null }))
                      setMateSlugs((prev) => ({ ...prev, [slot.area]: null }))
                      // 🔴 **서버에서도 무른다** — 안 그러면 새로고침에 되살아난다.
                      void cancelInvite(slot.area)
                    }}
                  >
                    cancel
                  </button>
                </>
              ) : (
                /* 🔴 **빈 자리만 카드 전체가 버튼이다.** 여는 일(추천 열기 ·
                   넣기)은 되돌릴 수 있어서 과녁이 넓어도 된다 — 가운데 + 만
                   눌리면 카드를 눌렀는데 아무 일도 안 일어나는 순간이 생긴다.
                   **빼는 일은 위에서 ⊗ 로만** 한다(되돌릴 수 없다).
                   버튼이 곧 .ss-pcard-mini 여야 한다 — 그 규칙이 카드를
                   직접 자식으로 찾기 때문에(> .ss-pcard) 사이에 다른
                   요소를 끼우면 축소가 통째로 풀린다. */
                <button
                  type="button"
                  className="ss-pcard-mini ss-squad-seat-btn"
                  // 고른 지인이 있으면 이 버튼은 "여기 넣기"다 — 깜빡이는
                  // 것만으로는 스크린리더에서 아무 차이가 없다.
                  data-placing={placing ? 'true' : undefined}
                  aria-label={
                    placing
                      ? `${posOf(slot)} 자리에 ${placing} 넣기`
                      : `${posOf(slot)} 자리에 선수 넣기`
                  }
                  aria-expanded={placing ? undefined : picking?.area === slot.area}
                  onClick={() => {
                    if (placing) {
                      setMates((prev) => ({ ...prev, [slot.area]: placing }))
                      /* 🔴 **고른 사람의 슬러그를 그 자리로 옮긴다**(미결
                         `paik` 39번, 2026-09-17 — 사용자 요청 「저기서 선택하면
                         스쿼드판에 그 사람 카드는 당연히 똑같이 떠야지」).
                         지인 목록이 슬러그를 안 줘서 이름표만 뜨던 자리였고,
                         같은 날 백엔드에 그 칸을 더했다(정어진 승인).

                         🔴 **없으면 `null` 로 덮는다.** 안 덮으면 **앞 사람
                         카드가 그대로 남아** 새 이름 위에 남의 카드가 그려진다
                         (대표 영상에서 한 번 데인 그 모양이다). 카드를 안 만든
                         사람은 그대로 이름표다 — 정상 갈래다. */
                      setMateSlugs((prev) => ({ ...prev, [slot.area]: placingSlug }))
                      // 판은 열어 둔다 — 여러 명을 이어서 넣는 게 보통이다.
                      setPlacing(null)
                      setPlacingSlug(null)
                      setPlacingUserId(null)
                      // 🔴 **초대를 보낸다** — 이래야 새로고침해도 남는다.
                      if (placingUserId) void invite(slot, placingUserId)
                      return
                    }
                    clearTimeout(timer.current)
                    setClosing(null)
                    // 🔴 추천 판도 챗봇과 **같은 자리**에 선다 — 켜져 있으면
                    // 먼저 물린다(그냥 열면 챗봇 뒤에 가려 나온다).
                    onBotChange?.(false)
                    // 🔴 **자리를 먼저 고른다.** 아래 onOpenScouting 이 켜는
                    // `scouting` 효과는 `picking ?? firstEmpty` 라, 여기서
                    // 먼저 넣어 두어야 **누른 자리**가 남는다. 순서를 뒤집으면
                    // 첫 빈 자리로 밀린다.
                    setPicking(slot)
                    // 지인 찾기도 같이 연다(사용자 요청, 2026-09-16) —
                    // 알약으로 연 것과 같은 한 벌이다.
                    onOpenScouting?.()
                  }}
                >
                  <BlankPlayerCard>
                    <span className="ss-squad-plus material-symbols-outlined" aria-hidden="true">
                      add
                    </span>
                  </BlankPlayerCard>
                </button>
              )}

              {/* 🔴 **수락 대기중**(사용자 설계, 2026-09-16). 추천·지인에서
                  고른 사람은 **팀 밖 사람**이라 바로 뛰는 것이 아니다 —
                  그 사람이 수락해야 선다. 카드 위에서 깜빡여 「아직 아니다」를
                  말한다.

                  🔴 **「준비 완료」는 없앴다**(사용자 판단, 2026-09-17). 이
                  표시의 목적은 「아직 수락 안 했다」를 말하는 것이지 다 된
                  것을 자랑하는 것이 아니다 — **기다리는 것만 말하고, 된 것은
                  조용히 둔다.** 판이 처음부터 차 있게 되면서(팀장 자동 착석)
                  다 된 카드마다 초록 딱지가 붙는 것이 오히려 시끄러웠다.

                  ⚠️ **아직 서버로 안 나간다.** 합류 요청 경로와 알림 타입이
                  계약에 없다(미결 `paik` 37번) — 그때까지 이 표시는 화면
                  안에서만 산다. */}
              {name && !seeded.ready[slot.area] && (
                <span className="ss-squad-pending" aria-live="polite">
                  수락 대기중
                </span>
              )}
              {/* 🔴 **이름표를 눌러 포지션을 직접 정한다**(사용자 요청).
                  기본은 행이 정하고(위=FW · 가운데=MF · 아래=DF · 골문앞=GK),
                  누르면 넷을 돌다가 「자동」으로 돌아온다. 「자동」이면 옮길
                  때마다 다시 행이 정한다.
                  ⚠️ 손으로 정해 둔 것은 `data-set` 으로 드러낸다 — 안 그러면
                  왜 옮겼는데 이름표가 안 바뀌는지 알 수 없다. */}
              <button
                type="button"
                className="ss-squad-pos"
                data-set={slot.pos ? 'true' : undefined}
                aria-label={
                  slot.pos
                    ? `포지션 ${slot.pos} — 직접 정한 값입니다. 눌러서 바꿉니다`
                    : `포지션 ${posOf(slot)} — 자리를 따릅니다. 눌러서 바꿉니다`
                }
                onClick={() => cyclePos(slot.area)}
              >
                {posOf(slot)}
              </button>
            </div>
          )
        })}
      </div>

      </section>

      {/* 지인 찾기 판 — 추천 판 **바로 오른쪽**(둘째 칸)에 같은 방식으로
          나온다. 자리는 globals.css 의 `.ss-friends` 가 정한다. */}
      {friendVisible && (
        <SquadFriends
          placing={placing}
          placed={placed}
          closing={!scouting}
          onChoose={(nickname, cardSlug, userId) => {
            setPlacing(nickname)
            setPlacingSlug(cardSlug)
            setPlacingUserId(userId)
          }}
          onClose={() => onCloseScouting?.()}
        />
      )}

      {/* 🔴 AI 단추는 **판의 오른쪽 변에 붙는다**(사용자 요청). 그래서
          알약 줄이 아니라 **여기**서 그린다 — 판 폭은 `width: max-content`
          라 CSS 상수가 없고(내용이 정한다), 판 바깥에서 맞추려면 그 폭을
          다시 재서 두 곳에서 자리를 정하게 된다. 판 안에서는 `right: 0`
          한 줄이면 무슨 폭이든 정확히 오른쪽 끝이다. */}
      <button
        type="button"
        className="ss-home-ai ss-traveling-edge"
        aria-label="AI 용병 찾기"
        aria-expanded={bot}
        onClick={() => onBotChange?.(!bot)}
      >
        AI
      </button>

      {/* AI 챗봇 — 추천 판과 **같은 첫째 칸**이다(사용자 요청). 여는 쪽이
          상대를 닫는다(`onBotChange` · 빈 자리 누르기). 둘째 칸의 지인 판과는
          자리가 갈렸으므로 겹치지 않는다. */}
      {bot && <MatchBot open onClose={() => onBotChange?.(false)} />}

      {/* 🔴 **알약 줄(팀장 · 팀원 · AI)과 같은 높이, 판 밖 오른쪽**에 선다
          (사용자 요청, 2026-09-10). 머리줄 안에 두었더니 크기 단추가 가운데로
          밀렸다 — 판 바깥 절대배치라 판의 어떤 것도 안 건드린다.

          🔴 **자리를 늘 잡아 둔다**(`visibility`) — 마지막 자리를 채우는 순간
          옆의 것들이 튀지 않게. 접근성 트리에서는 빠진다.

          알약 줄로 올라오면서 명단(판 오른쪽)과 **더는 안 겹치므로**, 열려
          있는 동안에도 그대로 두고 한 번 더 누르면 닫는다. */}
      <button
        type="button"
        className="ss-squad-match"
        data-blink={full && !matching ? 'true' : undefined}
        aria-hidden={!full}
        tabIndex={full ? undefined : -1}
        style={full ? undefined : { visibility: 'hidden' }}
        aria-expanded={matching}
        onClick={() => {
          // 첫째 칸은 한 번에 하나 — 여는 쪽이 다른 것을 닫는다.
          onBotChange?.(false)
          close()
          setMatching((now) => !now)
        }}
      >
        팀 매칭
      </button>

      {/* 비슷한 팀 명단 — 추천 · 챗봇과 **같은 첫째 칸**이다.
          🔴 「팀원」이 켜져 있으면 **안 그린다.** 단추가 사라지는데 판만 남으면
          닫을 길이 그 판의 × 뿐이고, 무엇을 보고 있는지도 흐려진다. 상태를
          effect 로 끄지 않고 **그릴 때 가른다** — 되돌아오면 그대로 다시 뜬다. */}
      {matching && !seeking && (
        <TeamMatch
          size={size}
          closing={false}
          onClose={() => setMatching(false)}
          teamId={myTeamId}
          /* 🔴 **여기서 대기 팝업을 띄우지 않는다**(사용자 요청, 2026-09-16).
             신청은 걸린 것이고 확정은 상대가 수락할 때다 — 그 순간은 알림으로
             오므로, 부모가 이 id 를 기억해 두었다가 그때 띄운다. */
          onRequested={(requestId, team) => onRequested?.(requestId, team)}
        />
      )}

      {/* 경기가 잡혔다 — 화면을 덮는 팝업. 닫으면 홈이 그대로 남는다. */}
      {matched && (
        <MatchWaiting
          us={{
            name: '우리 팀',
            /* 🔴 **판에 선 사람만** 넘긴다. 내 자리는 `card` 가 그려서
               `mates` 에 없으므로 여기서 이름을 따로 얹는다. */
            squad: slots
              .filter((sl) => sl.mine || mates[sl.area])
              .map((sl) => ({
                nickname: sl.mine ? (card?.user.nickname ?? '나') : (mates[sl.area] as string),
                col: sl.col,
                row: sl.row,
                pos: posOf(sl),
                mine: sl.mine,
              })),
          }}
          them={matched}
          myCard={card ?? null}
          onClose={() => {
            setMatched(null)
            onAcceptedShown?.()
          }}
          /* 🔴 **서버로 보낸다**(미결 `paik` 34번 해소, 2026-09-17). 전에는
             팝업만 닫혀서 확정 경기가 「내 경기」에 그대로 남았다.
             🔴 **경기 id 를 모르면 아예 안 낸다** — `onCancel` 을 안 주면
             `MatchWaiting` 이 무르기 단추를 그리지 않는다. */
          onCancel={
            acceptedMatchId
              ? /* 🔴 **보내기만 한다** — 판을 거두는 것은 `MatchWaiting` 이
                   내려가기 연출을 마친 뒤 `onClose` 로 한다. 여기서 먼저
                   거두면 실패해도 판이 사라져, 안 물러진 경기를 물러진
                   것으로 읽는다. */
                async () => {
                  await apiDelete(`/api/matches/${encodeURIComponent(acceptedMatchId)}`)
                }
              : undefined
          }
        />
      )}

      {/* 추천 판 — 스쿼드 판 오른쪽에서 미끄러져 나온다. */}
      {shown && (
        <SquadSuggest
          position={posOf(shown)}
          me={card ? { nickname: card.user.nickname, clip: myClip } : null}
          /* 🔴 **앉은 사람들의 평균을 화면에서 안 낸다**(2026-09-16). 서버가
             그 평균과 가까운 순으로 정렬해서 주므로(계약 3-16절), 화면이 또
             계산하면 두 곳이 갈린다 — 계약 44번의 「하지 말 것」이다. 대신
             후보를 찾을 팀만 넘긴다. */
          teamId={myTeamId}
          closing={picking === null}
          onClose={close}
          onPick={(name, cardSlug, userId) => {
            setMates((prev) => ({ ...prev, [shown.area]: name }))
            // 🔴 슬러그를 같이 남긴다 — 이것이 있어야 그 사람 카드가 그려진다.
            setMateSlugs((prev) => ({ ...prev, [shown.area]: cardSlug }))
            // 🔴 **초대를 보낸다**(계약 49) — 동의 없이 꽂지 않는다. 그 사람이
            //    수락해야 팀원이 되고, 그때까지 카드 위에 「수락 대기중」이 붙는다.
            void invite(shown, userId)
            close()
          }}
        />
      )}
    </div>
  )
}
