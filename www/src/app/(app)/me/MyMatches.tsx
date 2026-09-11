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
 *
 * 🔴 **다음 경기 하나만 보이고 나머지는 접는다**(사용자 요청, 2026-09-11).
 * 경기가 쌓이면 이 박스 하나가 길어져 왼쪽 칸이 통째로 밀린다. 기본으로
 * 알아야 할 것은 **바로 다음 경기 하나**이고, 나머지는 찾아볼 때 편다.
 * ⚠️ **잘라 내는 것이 아니라 접는 것**이다 — 나머지는 처음부터 DOM 에 있고
 * 펴는 것은 높이뿐이다. 잘라 두면 낭독기와 본문 검색에서 사라진다.
 */
const SHOWN = 1
export default function MyMatches({ matches }: { matches: Match[] }) {
  const [booked, setBooked] = useState<BookedMatch[]>([])
  useEffect(() => setBooked(listBooked()), [])
  const [open, setOpen] = useState(false)

  const empty = matches.length === 0 && booked.length === 0

  /* 🔴 **두 목록을 한 줄 배열로 세고 자른다.** 서버 경기가 없을 때 잡힌
     경기가 그 자리를 받아야 한다 — 각자 하나씩 보이면 둘이 된다.
     그리면서는 여전히 갈라서 표를 단다(위 주석). */
  const rows = [
    ...matches.map((m) => ({ kind: 'server' as const, m })),
    ...booked.map((m) => ({ kind: 'booked' as const, m })),
  ]
  const head = rows.slice(0, SHOWN)
  const rest = rows.slice(SHOWN)

  /** 한 줄. 🔴 **두 갈래를 한 함수에서 그린다** — 두 벌로 두면 한쪽만 늙는다. */
  const row = (r: (typeof rows)[number]) =>
    r.kind === 'server' ? (
      <li key={r.m.id}>
        <p className="ss-profile-match-when">{when(r.m.played_at)}</p>
        <p className="ss-profile-match-place">{r.m.place}</p>
        {r.m.needs.length > 0 && (
          <p className="ss-profile-muted">
            {r.m.needs.map((n) => `${n.position_label} ${n.head_count}`).join(' · ')}
          </p>
        )}
      </li>
    ) : (
      <li key={`booked-${r.m.id}`} data-booked="true">
        <p className="ss-profile-match-when">{when(r.m.playedAt)}</p>
        <p className="ss-profile-match-place">{r.m.place}</p>
        {/* 누구와 붙는지가 이 줄의 요점이다 — 서버 경기는 상대가 없다. */}
        <p className="ss-profile-muted">
          <span className="ss-profile-match-tag">팀 매칭</span>
          {r.m.opponent}
        </p>
      </li>
    )

  return (
    <>
      {empty ? (
        /* ⚠️ "경기가 없다" 가 아니라 "**다가오는** 것이 없다" 다 —
           계약이 지난 경기를 이 목록에서 빼기 때문이다(3-4절).
           지난 경기가 있어도 여기는 비어 있을 수 있다. */
        <p className="ss-profile-muted">다가오는 경기가 없습니다.</p>
      ) : (
        <>
          <ul className="ss-profile-match-list">{head.map(row)}</ul>

          {rest.length > 0 && (
            <>
              {/* 🔴 접는 것은 `max-height` 가 아니라 **`grid-template-rows`**
                  (0fr → 1fr) 다. 상한과 실제 높이가 다르면 전환이 안 보이는
                  구간에서 시간이 소모돼 속도가 튄다 — 이 화면의 왼쪽 칸
                  접기가 같은 이유로 그렇게 되어 있다.
                  🔴 접힌 동안에는 **접근성 트리에서도 뺀다.** 안 그러면
                  낭독기에는 넷이 다 들리는데 눈에는 둘만 보인다. */}
              <div
                className="ss-profile-match-fold"
                data-testid="match-fold"
                data-open={open ? 'true' : 'false'}
                aria-hidden={open ? undefined : 'true'}
              >
                <div>
                  <ul className="ss-profile-match-list">{rest.map(row)}</ul>
                </div>
              </div>

              {/* 🔴 **몇 개가 더 있는지 적는다** — 「더보기」만 두면 한 줄이
                  더 있는지 열 줄이 더 있는지 모르고 누르게 된다. */}
              <button
                type="button"
                className="ss-profile-match-more"
                aria-expanded={open}
                onClick={() => setOpen((v) => !v)}
              >
                {open ? '접기' : `더보기 ${rest.length}`}
              </button>
            </>
          )}
        </>
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
