'use client'

import { usePathname } from 'next/navigation'
import { TransitionLink } from '@/lib/pageTransition'
import { requestMatchOpen } from '@/lib/seekingStore'
import type { ConfirmedMatch } from '@/lib/useNotifyInbox'

/**
 * **「경기 잡힘」 — 잡힌 경기로 돌아가는 길** (사용자 요청, 2026-09-18:
 * "경기매칭이 성사된 상태에서 다른페이지를 이동했어도 다시 경기매칭이 성사된
 * 페이지로 돌아올수있게").
 *
 * 전에는 경기 화면이 **「방금 잡혔다」는 사건**에만 떴다. 그 사건은 이 탭의
 * 기억에만 있어서 **새로고침하면 사라졌고**, 그러면 잡힌 경기를 다시 볼 길이
 * 없었다. 이 표시는 **서버가 아는 확정 경기**를 근거로 하므로 언제 들어와도
 * 남아 있다.
 *
 * 🔴 **저절로 안 뜬다, 누를 때만 뜬다**(사용자 결정). 경기 화면은 화면을
 * 통째로 덮어서, 다른 일을 하러 들어온 사람이 매번 닫아야 하면 방해가 된다.
 */

/** `2026-09-19T09:00:00` → `9/19 토 09:00`. 머리칸이라 짧게 적는다. */
function shortWhen(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const day = ['일', '월', '화', '수', '목', '금', '토'][d.getDay()]
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getMonth() + 1}/${d.getDate()} ${day} ${p(d.getHours())}:${p(d.getMinutes())}`
}

export default function MatchPill({
  match,
  onReopen,
}: {
  match: ConfirmedMatch | null
  /**
   * 홈에서 눌렀을 때 — 그 자리에서 판을 연다.
   *
   * 🔴 **홈이 아니면 안 준다.** 경기 화면을 그리는 것은 홈의 판 하나뿐이라,
   * 다른 화면에서는 열 대상이 없다 — 그때는 「열어 달라」를 적어 두고 홈으로
   * 보낸다(`requestMatchOpen`).
   */
  onReopen?: () => void
}) {
  const pathname = usePathname()
  if (!match) return null

  const atHome = pathname === '/'
  const label = `경기 잡힘 · ${shortWhen(match.playedAt)}`
  const shared =
    'inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm whitespace-nowrap'

  const body = (
    <>
      <span aria-hidden="true" className="material-symbols-outlined ss-match-pill-icon">
        sports_soccer
      </span>
      <span>{label}</span>
    </>
  )

  return (
    <div className="ss-seeking-wrap flex items-start">
      {atHome && onReopen ? (
        <button type="button" className={`ss-match-pill ${shared}`} onClick={onReopen}>
          {body}
        </button>
      ) : (
        <TransitionLink
          href="/"
          className={`ss-match-pill ${shared}`}
          onClick={() => requestMatchOpen(match.matchId)}
          aria-label={`${label} — 눌러서 경기 화면으로 갑니다`}
        >
          {body}
        </TransitionLink>
      )}
    </div>
  )
}
