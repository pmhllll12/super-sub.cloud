'use client'

import { useEffect, useState } from 'react'
import type { Match } from '@/server/backend'
import { listBooked, type BookedMatch } from '@/lib/bookedMatches'
import { when } from './format'

/**
 * **내 경기** — 서버가 준 다가오는 경기 + **팀 매칭으로 잡힌 것**.
 *
 * 🔴 **두 목록을 섞지 않는다.** 위쪽(`matches`)은 서버가 준 진짜 경기이고,
 * 아래(`booked`)는 팀 매칭 데모가 브라우저에 적어 둔 것이다(계약에 자리가
 * 없다 — `lib/bookedMatches.ts`). 한 배열로 뭉치면 어느 것이 진짜인지 화면도
 * 다음 사람도 알 수 없다. **줄에 표를 달아 가른다.**
 *
 * 🔴 **그릴 때 저장소를 읽지 않는다.** 서버엔 없는 값이라 서버가 그린 첫
 * 화면과 갈려 하이드레이션이 깨진다(공개 목록 · 카드 꾸미기에서 데인 자리).
 * 붙은 뒤에 한 번 읽어 얹는다.
 */
export default function MyMatches({ matches }: { matches: Match[] }) {
  const [booked, setBooked] = useState<BookedMatch[]>([])
  useEffect(() => setBooked(listBooked()), [])

  const empty = matches.length === 0 && booked.length === 0

  return (
    <>
      {empty ? (
        /* ⚠️ "경기가 없다" 가 아니라 "**다가오는** 것이 없다" 다 —
           계약이 지난 경기를 이 목록에서 빼기 때문이다(3-4절).
           지난 경기가 있어도 여기는 비어 있을 수 있다. */
        <p className="ss-profile-muted">다가오는 경기가 없습니다.</p>
      ) : (
        <ul className="ss-profile-match-list">
          {matches.map((m) => (
            <li key={m.id}>
              <p className="ss-profile-match-when">{when(m.played_at)}</p>
              <p className="ss-profile-match-place">{m.place}</p>
              {m.needs.length > 0 && (
                <p className="ss-profile-muted">
                  {m.needs.map((n) => `${n.position_label} ${n.head_count}`).join(' · ')}
                </p>
              )}
            </li>
          ))}

          {booked.map((m) => (
            <li key={`booked-${m.id}`} data-booked="true">
              <p className="ss-profile-match-when">{when(m.playedAt)}</p>
              <p className="ss-profile-match-place">{m.place}</p>
              {/* 누구와 붙는지가 이 줄의 요점이다 — 서버 경기는 상대가 없다. */}
              <p className="ss-profile-muted">
                <span className="ss-profile-match-tag">팀 매칭</span>
                {m.opponent}
              </p>
            </li>
          ))}
        </ul>
      )}

      {/* ⚠️ 데모라는 것을 숨기지 않는다 — 숨기면 진짜로 잡힌 줄 안다. */}
      {booked.length > 0 && (
        <p className="ss-profile-muted ss-profile-match-note">
          「팀 매칭」은 아직 데모입니다 — 이 브라우저에만 남고 상대에게는 가지 않습니다.
        </p>
      )}
    </>
  )
}
