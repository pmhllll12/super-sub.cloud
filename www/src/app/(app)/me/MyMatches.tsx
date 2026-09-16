'use client'

import { useState } from 'react'
import type { Match } from '@/server/backend'
import { when } from './format'

/**
 * **내 경기** — 서버가 준 다가오는 경기.
 *
 * ✅ **2026-09-16 — 브라우저 목록을 걷었다.** 전에는 팀 매칭으로 잡힌 경기를
 * `lib/bookedMatches.ts` 가 localStorage 에 따로 적었다. 계약에 확정 경기
 * 자리가 없던 시절의 임시였는데, 3-15절이 생기면서 **수락하면 서버에 진짜
 * `match` 가 생기고** 이 목록(`GET /teams/{id}/matches`)에 그대로 온다.
 *
 * 🔴 **둘 다 두면 같은 경기가 두 번 보인다.** 그리고 localStorage 는 mock
 * 이 아니라 **브라우저**라, 진짜 도메인에서도 그대로 돌았다 — 「데모입니다,
 * 상대에게는 가지 않습니다」라는 이제 사실이 아닌 문구와 함께.
 *
 * 🔴 **다음 경기 하나만 보이고 나머지는 접는다**(사용자 요청, 2026-09-11).
 * 경기가 쌓이면 이 박스 하나가 길어져 왼쪽 칸이 통째로 밀린다. 기본으로
 * 알아야 할 것은 **바로 다음 경기 하나**이고, 나머지는 찾아볼 때 편다.
 * ⚠️ **잘라 내는 것이 아니라 접는 것**이다 — 나머지는 처음부터 DOM 에 있고
 * 펴는 것은 높이뿐이다. 잘라 두면 낭독기와 본문 검색에서 사라진다.
 */
const SHOWN = 1
export default function MyMatches({ matches }: { matches: Match[] }) {
  const [open, setOpen] = useState(false)

  const empty = matches.length === 0

  const head = matches.slice(0, SHOWN)
  const rest = matches.slice(SHOWN)

  const row = (m: Match) => (
    <li key={m.id}>
      <p className="ss-profile-match-when">{when(m.played_at)}</p>
      <p className="ss-profile-match-place">{m.place}</p>
      {/* 🔴 **팀 대 팀 확정 경기는 모집이 비어 있다**(계약 3-15절) — 그때는
          이 줄을 아예 안 그린다. 빈 모집란은 「아무도 안 구한다」가 아니라
          「구할 것이 없다」라서, 0 을 적으면 뜻이 반대가 된다. */}
      {m.needs.length > 0 && (
        <p className="ss-profile-muted">
          {m.needs.map((n) => `${n.position_label} ${n.head_count}`).join(' · ')}
        </p>
      )}
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

    </>
  )
}
