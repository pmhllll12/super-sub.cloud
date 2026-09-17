'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { teamById } from '@/lib/teamMatch'

/**
 * 알림함 — **내가 응답해야 하는 것**만 모은다 (계약 3-12·3-15절).
 *
 * 🔴 **`GET /me/notifications` 를 목록의 정본으로 쓰지 않는다.** 그 응답에는
 * 문구도, 상대 팀 이름도, 지금도 유효한 신청인지도 없다(`type` · id 뿐이다).
 * 알림은 "무언가 생겼다"는 신호일 뿐이라, 화면에 그릴 것은 **신청 목록**에서
 * 직접 읽는다 — 그래야 이미 수락·취소된 것이 목록에 남지 않는다.
 *
 * 🔴 **폴링이다.** 실시간 전달 경로가 없다(계약 3-12절 「아직 없는 것」).
 */

/** 받은 경기 신청 한 줄 — 그릴 수 있게 팀 이름까지 붙여 둔 모양. */
export type InboxMatch = {
  kind: 'team-match'
  id: string
  /** 내 팀 id — 수락·거절이 이 팀 밑으로 나간다. */
  teamId: string
  /** 건 쪽 팀 id — 수락한 뒤 대기 화면이 이 팀을 그린다. */
  opponentTeamId: string
  /** 상대 팀 이름. 🔴 계약이 이름을 안 줘서 못 찾을 수 있다 — 그때는 `null`. */
  name: string | null
  region: string | null
  playedAt: string
  place: string
}

/** 받은 지인 신청 한 줄. */
export type InboxContact = {
  kind: 'contact'
  id: string
  note: string | null
}

export type InboxItem = InboxMatch | InboxContact

/** 얼마마다 다시 묻는가. 사람이 수락하는 속도라 촘촘할 이유가 없다. */
const POLL_MS = 15_000

type SentState = { requestId: string; targetTeamId: string }

export function useNotifyInbox() {
  const [teamId, setTeamId] = useState<string | null>(null)
  const [items, setItems] = useState<InboxItem[]>([])
  /**
   * **내가 건 신청이 수락됐다** — 대기 화면을 띄울 신호다.
   *
   * 🔴 `null` 에서 값이 생기는 순간이 곧 "잡혔다"이다. 신청을 건 시점이
   * 아니다 — 그 둘을 같게 두면 대기 화면이 상대 응답 전에 뜬다.
   */
  const [acceptedTeamId, setAcceptedTeamId] = useState<string | null>(null)
  /**
   * 그렇게 잡힌 **경기의 id**. 🔴 **무르려면 이것이 있어야 한다**(미결 `paik`
   * 34번) — 계약의 취소는 `DELETE /matches/{match_id}` 라 팀 id 로는 못 부른다.
   * 팀 id 만 들고 있던 것이 34번이 열려 있던 이유였다.
   */
  const [acceptedMatchId, setAcceptedMatchId] = useState<string | null>(null)
  const sent = useRef<SentState[]>([])

  // 내 팀 — 계약의 경기 신청 경로가 전부 `teams/{id}` 밑이라 먼저 알아야 한다.
  useEffect(() => {
    let alive = true
    void (async () => {
      try {
        const res = await fetch('/api/me')
        if (!res.ok || !alive) return
        const me = (await res.json().catch(() => null)) as {
          teams?: { team_id: string; role: string }[]
        } | null
        // 🔴 **주장인 팀만** 본다 — 신청을 받고 수락하는 것은 주장의 일이라,
        // 팀원인 팀을 골라 두면 그 경로가 전부 403 이다.
        const mine = me?.teams?.find((t) => t.role === 'owner') ?? null
        if (alive) setTeamId(mine?.team_id ?? null)
      } catch {
        /* 로그인 전이면 조용히 없는 것으로 둔다 — 헤더는 늘 그려진다. */
      }
    })()
    return () => {
      alive = false
    }
  }, [])

  const reload = useCallback(async () => {
    const next: InboxItem[] = []
    if (teamId) {
      try {
        const res = await fetch(`/api/teams/${encodeURIComponent(teamId)}/match-requests`)
        if (res.ok) {
          const rows = ((await res.json().catch(() => null)) ?? []) as {
            id: string
            requester_team_id: string
            target_team_id: string
            proposed_played_at: string
            proposed_place: string
            status: string
            /** 수락됐을 때만 찬다 — 「무르기」가 이걸로 부른다(계약). */
            match_id: string | null
          }[]
          for (const r of rows) {
            // 받은 것 중 **아직 대기중**인 것만 응답할 거리가 있다.
            if (r.status === 'pending' && r.target_team_id === teamId) {
              const them = teamById(r.requester_team_id)
              next.push({
                kind: 'team-match',
                id: r.id,
                teamId,
                opponentTeamId: r.requester_team_id,
                name: them?.name ?? null,
                region: them?.region ?? null,
                playedAt: r.proposed_played_at,
                place: r.proposed_place,
              })
            }
            // 내가 건 것이 수락됐으면 그 순간 대기 화면을 띄운다.
            if (
              r.status === 'accepted' &&
              r.requester_team_id === teamId &&
              sent.current.some((s) => s.requestId === r.id)
            ) {
              setAcceptedTeamId(r.target_team_id)
              // 수락된 행에는 확정 경기 id 가 실려 온다(계약 `match_id`).
              setAcceptedMatchId(r.match_id ?? null)
            }
          }
        }
      } catch {
        /* 한 번 실패해도 폴링이 계속 돈다 — 화면을 비우지 않는다. */
      }
    }
    try {
      const res = await fetch('/api/me/contacts/requests')
      if (res.ok) {
        const rows = ((await res.json().catch(() => null)) ?? []) as {
          id: string
          note: string | null
        }[]
        for (const r of rows) next.push({ kind: 'contact', id: r.id, note: r.note })
      }
    } catch {
      /* 위와 같다. */
    }
    setItems(next)
  }, [teamId])

  useEffect(() => {
    // 한 번 읽고, 그 뒤로는 주기마다 다시 묻는다. 규칙은 effect 안의 setState 를
    // 싫어하지만 여기서 상태가 바뀌는 것은 **응답이 온 뒤**다.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void reload()
    const t = window.setInterval(() => void reload(), POLL_MS)
    return () => clearInterval(t)
  }, [reload])

  /** 경기 신청을 수락한다 — 확정 경기가 생긴다. */
  const acceptMatch = useCallback(
    async (item: InboxMatch) => {
      const res = await fetch(
        `/api/teams/${encodeURIComponent(item.teamId)}/match-requests/${encodeURIComponent(item.id)}/accept`,
        { method: 'POST' },
      )
      if (!res.ok) throw new Error('수락하지 못했습니다.')
      /* 수락 응답이 확정 경기 id 를 준다 — 대기 판의 「무르기」가 그걸 쓴다. */
      const made = (await res.json().catch(() => null)) as { match_id?: string | null } | null
      setAcceptedMatchId(made?.match_id ?? null)
      /* 🔴 **수락한 그 순간이 「잡혔다」이다** — 대기 화면을 띄울 신호를 여기서
         켠다. 폴링이 다시 돌기를 기다리면 최대 15초 동안 아무 일도 안 일어난
         것처럼 보인다. */
      setAcceptedTeamId(item.opponentTeamId)
      await reload()
    },
    [reload],
  )

  const rejectMatch = useCallback(
    async (item: InboxMatch) => {
      await fetch(
        `/api/teams/${encodeURIComponent(item.teamId)}/match-requests/${encodeURIComponent(item.id)}/reject`,
        { method: 'POST' },
      )
      await reload()
    },
    [reload],
  )

  const acceptContact = useCallback(
    async (item: InboxContact) => {
      await fetch(`/api/me/contacts/${encodeURIComponent(item.id)}/accept`, { method: 'POST' })
      await reload()
    },
    [reload],
  )

  /** 내가 신청을 걸었다고 알려 준다 — 수락되는 순간을 알아보려면 필요하다. */
  const noteSent = useCallback((requestId: string, targetTeamId: string) => {
    sent.current = [...sent.current, { requestId, targetTeamId }]
  }, [])

  return {
    teamId,
    items,
    count: items.length,
    acceptedTeamId,
    acceptedMatchId,
    clearAccepted: () => {
      setAcceptedTeamId(null)
      setAcceptedMatchId(null)
    },
    acceptMatch,
    rejectMatch,
    acceptContact,
    noteSent,
    reload,
  }
}
