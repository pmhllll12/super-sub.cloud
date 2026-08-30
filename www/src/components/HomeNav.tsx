'use client'

import { useEffect, useRef, useState } from 'react'
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
 *
 * 고정한 카드는 **다른 데를 누르거나 Esc 를 누르면** 풀린다 — 안 그러면
 * 한 번 누른 카드가 화면에 계속 떠 있는다.
 *
 * 사라질 때는 바로 없애지 않고 {@link CARD_EXIT_MS} 동안 흐려지며
 * 물러난다. 그동안 DOM 에 남겨 둬야 해서(`exiting`) 지금 떠 있는 것과
 * 지금 사라지는 중인 것을 따로 센다.
 */
// 카드가 나타나고 사라지는 시간 — globals.css 의 ss-card-in/out 과 같아야
// 한다. 여기가 짧으면 애니메이션 도중에 잘리고, 길면 사라진 자리가 남는다.
const CARD_EXIT_MS = 180

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
  const navRef = useRef<HTMLElement>(null)
  const [hovered, setHovered] = useState<string | null>(null)
  const [pinned, setPinned] = useState<string | null>(null)
  const shown = hovered ?? pinned

  // 방금까지 떠 있다가 지금 물러나는 중인 카드. 애니메이션이 끝날 때까지만 산다.
  const [exiting, setExiting] = useState<string | null>(null)
  const prevShown = useRef<string | null>(null)
  useEffect(() => {
    const prev = prevShown.current
    prevShown.current = shown
    if (!prev || prev === shown) return
    setExiting(prev)
    const t = setTimeout(() => setExiting((e) => (e === prev ? null : e)), CARD_EXIT_MS)
    return () => clearTimeout(t)
  }, [shown])

  // 고정해 둔 카드는 바깥을 누르거나 Esc 를 누르면 풀린다. pointerdown 으로
  // 잡는다 — click 은 마우스를 뗄 때라 그 사이 화면이 이미 바뀌어 있을 수 있다.
  useEffect(() => {
    if (pinned === null) return
    function onPointerDown(e: PointerEvent) {
      if (navRef.current?.contains(e.target as Node)) return
      setPinned(null)
      onActivate(null)
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key !== 'Escape') return
      setPinned(null)
      onActivate(null)
    }
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [pinned, onActivate])

  function show(title: string | null) {
    setHovered(title)
    onActivate(title ?? pinned)
  }

  return (
    <nav ref={navRef} aria-label="목적지">
      <ul className="flex flex-wrap items-center justify-end gap-x-6 gap-y-2">
        {destinations.map((d) => {
          const open = shown === d.title
          const closing = !open && exiting === d.title
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

              {(open || closing) && (
                <div className="ss-home-nav-card" data-state={closing ? 'closing' : 'open'}>
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
