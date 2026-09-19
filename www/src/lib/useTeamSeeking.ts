'use client'

import { useCallback, useEffect, useState } from 'react'
import { findCandidates, type CandidateTeam } from '@/lib/teamMatch'
import {
  markSeen,
  readSeeking,
  startSeeking,
  stopSeeking,
  subscribe,
  type Seeking,
} from '@/lib/seekingStore'

/**
 * **팀을 찾는 중인 동안 계속 돈다** (사용자 요청, 2026-09-18).
 *
 * 머리칸(`SiteHeader`)에 매달려 있어 **로그인한 모든 화면에서** 산다 —
 * `useNotifyInbox` 와 같은 자리, 같은 이유다. 그래서 「팀 매칭」을 켜 두고
 * 영상 분석으로 가도 찾기가 안 끊긴다.
 *
 * 🔴 **켜져 있을 때만 부른다.** 안 찾는 중이면 요청이 한 번도 안 나간다.
 * 앞단이 Cloudflare 라 요청 제한이 **엣지별로 묶여 있고**(미결 `jin` 37번)
 * 남들 요청까지 같이 걸리므로, 상시 폴링을 하나 더 얹지 않는다.
 *
 * 🔴 **탭이 안 보이면 쉰다.** 배경 탭이 며칠 떠 있는 것이 흔한데, 그 탭이
 * 계속 부르면 얻는 것 없이 제한만 먹는다. 다시 보이는 순간 한 번 부른다 —
 * 그래서 돌아왔을 때 값이 낡아 보이지 않는다.
 */

/**
 * 얼마마다 다시 묻는가.
 *
 * 알림함(15초)보다 **성기게** 잡았다. 저쪽은 사람이 수락하기를 기다리는
 * 것이고 이쪽은 **남이 팀을 다 채우고 조건까지 올리기**를 기다리는 것이라,
 * 분 단위로 바뀌는 값이 아니다. 후보 질의가 팀마다 여러 번 조회하는 것도
 * 성기게 잡은 까닭이다(`list_candidate_facts`).
 */
const POLL_MS = 60_000

export type TeamSeeking = {
  /** 찾는 중인가. 안 찾으면 `null`. */
  seeking: Seeking | null
  /** 지금 잡히는 후보 전부. */
  teams: CandidateTeam[]
  /**
   * **시작한 뒤 새로 생긴** 후보만. 🔴 「몇 곳인가」가 아니라 「어느 팀인가」로
   * 센다 — 한 곳이 빠지고 다른 곳이 들어오면 수는 같은데 새 팀은 생긴 것이다.
   */
  fresh: CandidateTeam[]
  /** 한 번이라도 조회를 마쳤는가 — 그리기 전에 「0곳」이라고 적지 않으려고. */
  loaded: boolean
  start: (teamId: string) => void
  stop: () => void
  /** 새로 생긴 것을 **봤다**고 표시한다(알림을 닫을 때). */
  acknowledge: () => void
}

export function useTeamSeeking(): TeamSeeking {
  const [seeking, setSeeking] = useState<Seeking | null>(null)
  const [teams, setTeams] = useState<CandidateTeam[]>([])
  const [loaded, setLoaded] = useState(false)

  /* 🔴 **그릴 때 저장소를 읽지 않는다**(하이드레이션) — 붙은 뒤에 읽는다.
     서버가 그린 HTML 에는 이 브라우저의 값이 있을 수 없어서, 처음부터 읽으면
     서버와 클라이언트가 다른 것을 그려 React 가 경고한다. */
  useEffect(() => {
    const sync = () => setSeeking(readSeeking())
    sync()
    return subscribe(sync)
  }, [])

  const teamId = seeking?.teamId ?? null

  const reload = useCallback(async () => {
    if (!teamId) return
    try {
      const rows = await findCandidates(teamId)
      setTeams(rows)
      setLoaded(true)
    } catch {
      /* 한 번 실패해도 계속 돈다 — 표시를 지우지 않는다. 지우면 「그만 찾게
         됐나」로 읽히는데 실제로는 조회 한 번이 어긋났을 뿐이다. */
    }
  }, [teamId])

  useEffect(() => {
    if (!teamId) return
    let stopped = false
    const run = () => {
      if (stopped) return
      if (typeof document !== 'undefined' && document.visibilityState !== 'visible') return
      void reload()
    }
    run()
    const timer = window.setInterval(run, POLL_MS)
    /* 다시 보이는 순간 한 번 — 돌아왔는데 낡은 값이 떠 있지 않게. */
    document.addEventListener('visibilitychange', run)
    return () => {
      stopped = true
      clearInterval(timer)
      document.removeEventListener('visibilitychange', run)
    }
  }, [teamId, reload])

  /* 🔴 **그만두면 들고 있던 후보를 effect 에서 지우지 않고 그릴 때 가른다.**
     effect 에서 지우면 화면이 한 번 더 그려지고(연쇄 렌더), 무엇보다 다시
     켰을 때 첫 조회가 올 때까지 빈 목록이 잠깐 스친다. 안 찾는 중이면
     「없는 것」으로 **읽기만** 하면 된다. */
  const on = Boolean(teamId)
  const shown = on ? teams : []
  const seen = seeking?.seen ?? []
  const fresh = on && loaded ? shown.filter((t) => !seen.includes(t.id)) : []

  return {
    seeking,
    teams: shown,
    fresh,
    loaded: on && loaded,
    start: useCallback((id: string) => startSeeking(id), []),
    stop: useCallback(() => stopSeeking(), []),
    acknowledge: useCallback(() => markSeen(teams.map((t) => t.id)), [teams]),
  }
}
