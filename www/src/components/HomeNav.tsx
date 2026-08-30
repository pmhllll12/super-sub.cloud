'use client'

import { useState } from 'react'
import DestinationCard from './DestinationCard'

export type Destination = {
  title: string
  icon: string
  summary: string
  href?: string
  /** 이 목적지가 결국 requireUser() 에 걸리는 로그인 전용 경로인가 — 로그인
   *  안 한 사람에게는 "로그인이 필요합니다" 안내를 보여준다(링크 자체는
   *  살려 둔다, 눌러야 /login 으로 보내는 지금 방식 그대로). */
  authRequired?: boolean
}

/**
 * 홈 상단의 글자 내비 — 레퍼런스(Nile Travel)의 `TOURS ABOUT US GALLERY …`
 * 자리다. 예전에는 화면 아래 카드 6장을 가로로 흘리는 캐러셀이었는데,
 * 카드가 배경 사진을 절반 넘게 가렸다. 글자만 남기고 카드는 **가리켰을
 * 때만** 그 글자 아래로 떠오르게 바꿨다.
 *
 * 🔴 **글자는 링크가 아니라 버튼이다. 이동은 떠오른 카드가 한다.**
 * 사용자가 정한 동작이 "글자에 대거나 누르면 카드가 나오고, 그 카드를
 * 누르면 이동"이라서다. 글자까지 링크로 만들면 같은 곳으로 가는 링크가
 * 한 항목에 둘이 되어(글자 + 카드) 스크린리더에서도 테스트에서도 어느
 * 쪽인지 모호해진다.
 *
 * 마우스가 없는 자리(터치 · 키보드)를 위해 셋 다 받는다:
 * - `hover` — 대면 나오고 치우면 사라진다
 * - `focus` — Tab 으로 닿아도 나온다(그래야 그 다음 Tab 이 카드 링크로 간다)
 * - `click` — 눌러서 **고정**한다. 터치에는 hover 가 없어 이것뿐이다.
 *   한 번 더 누르면 풀린다. 고정된 것과 지금 가리킨 것이 다르면 가리킨
 *   쪽이 이긴다(`hovered ?? pinned`).
 */
export default function HomeNav({
  destinations,
  loggedIn,
  active,
  onActivate,
}: {
  destinations: Destination[]
  loggedIn: boolean
  /** 지금 강조할 목적지 제목 — 우하단 번호 목록과 맞추려고 부모가 쥔다. */
  active: string | null
  onActivate: (title: string | null) => void
}) {
  const [hovered, setHovered] = useState<string | null>(null)
  const [pinned, setPinned] = useState<string | null>(null)
  const shown = hovered ?? pinned

  function show(title: string | null) {
    setHovered(title)
    onActivate(title ?? pinned)
  }

  return (
    <nav aria-label="목적지">
      <ul className="flex flex-wrap items-center justify-end gap-x-6 gap-y-2">
        {destinations.map((d) => {
          const open = shown === d.title
          return (
            <li
              key={d.title}
              className="relative"
              onMouseEnter={() => show(d.title)}
              onMouseLeave={() => show(null)}
              // 포커스가 이 항목(글자 + 떠오른 카드) 밖으로 나갈 때만 닫는다 —
              // 글자에서 카드 링크로 Tab 하는 사이에 닫히면 카드를 누를 수 없다.
              onBlur={(e) => {
                if (!e.currentTarget.contains(e.relatedTarget as Node | null)) show(null)
              }}
            >
              <button
                type="button"
                data-active={active === d.title ? 'true' : undefined}
                aria-expanded={open}
                onFocus={() => show(d.title)}
                onClick={() => {
                  const next = pinned === d.title ? null : d.title
                  setPinned(next)
                  onActivate(next)
                }}
                className="ss-home-nav-item"
              >
                {d.title}
              </button>

              {open && (
                <div className="ss-home-nav-card">
                  <DestinationCard
                    compact
                    title={d.title}
                    icon={d.icon}
                    summary={d.summary}
                    href={d.href}
                    locked={Boolean(d.authRequired) && !loggedIn}
                  />
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
