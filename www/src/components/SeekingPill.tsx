'use client'

import { usePathname } from 'next/navigation'
import { TransitionLink } from '@/lib/pageTransition'
import type { TeamSeeking } from '@/lib/useTeamSeeking'

/**
 * **「팀 찾는 중」 — 어느 화면에 있든 머리칸에 남는 표시** (사용자 요청,
 * 2026-09-18: "팀매칭을 시작하면 다른페이지로 이동해도 여전히 찾고있는
 * 상태를 유지").
 *
 * 머리칸은 로그인한 모든 화면이 같이 쓰므로(`SiteHeader`), 여기 두면 홈을
 * 떠나도 찾기가 끊기지 않는다. 누르면 홈으로 돌아가고, 홈의 판은 같은
 * 저장소를 읽어 **팀 매칭을 편 채로** 열린다(`SquadPanel`).
 *
 * 🔴 **안 찾는 중이면 아무것도 그리지 않는다.** 늘 자리를 차지하면 머리칸이
 * 붐비고, 찾고 있다는 사실이 눈에 안 띈다.
 */
export default function SeekingPill({ seeking }: { seeking: TeamSeeking }) {
  const pathname = usePathname()
  if (!seeking.seeking) return null

  const found = seeking.teams.length
  const fresh = seeking.fresh.length
  /* 홈에서는 판이 이미 옆에 떠 있다 — 같은 것을 가리키는 고리를 또 두지 않고
     상태만 적는다. */
  const atHome = pathname === '/'

  const body = (
    <>
      <span aria-hidden="true" className="ss-seeking-dot" />
      <span>
        팀 찾는 중
        {seeking.loaded && found > 0 ? ` · ${found}곳` : ''}
      </span>
      {fresh > 0 && (
        /* 🔴 **새로 생긴 것만** 센다 — 전체 수는 옆에 이미 있다. 한 곳이
           빠지고 다른 곳이 들어오면 전체 수는 그대로라, 이 칸이 없으면
           「새 팀이 생겼다」가 화면에 아예 안 나타난다. */
        <span className="ss-seeking-new">새로 {fresh}곳</span>
      )}
    </>
  )

  const shared =
    'inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm whitespace-nowrap'

  return (
    <div className="ss-seeking-wrap flex items-start">
      {atHome ? (
        <span className={`ss-seeking-pill ${shared}`} aria-live="polite">
          {body}
        </span>
      ) : (
        <TransitionLink
          href="/"
          className={`ss-seeking-pill ${shared}`}
          aria-label={
            fresh > 0
              ? `팀 찾는 중 — 새로 ${fresh}곳이 생겼습니다. 눌러서 홈의 팀 매칭으로 갑니다`
              : '팀 찾는 중 — 눌러서 홈의 팀 매칭으로 갑니다'
          }
        >
          {body}
        </TransitionLink>
      )}
    </div>
  )
}
