'use client'

import { useEffect, useRef, useState, type CSSProperties } from 'react'
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
  variant = 'text',
  label = '목적지',
  picked = null,
  onPick,
}: {
  destinations: Destination[]
  loggedIn: boolean
  /** 지금 강조할 목적지 제목 — 우하단 번호 목록과 맞추려고 부모가 쥔다. */
  active: string | null
  onActivate: (title: string | null) => void
  /**
   * `text` — 헤더의 자간 넓은 글자 줄(기본).
   * `pill` — 유리 알약 버튼. 헤드라인 자리에 두는 주요 목적지용이다.
   *
   * 동작은 둘이 **완전히 같다**(가리키면 카드, 눌러서 고정, Esc 로 해제).
   * 생김새만 갈린다 — 그래서 컴포넌트를 따로 만들지 않았다. 따로 만들면
   * 고정 · 해제 · 포커스 규칙이 두 벌로 갈라져 따로 늙는다.
   */
  variant?: 'text' | 'pill'
  /** `<nav>` 의 이름. 한 화면에 둘 이상 두면 서로 달라야 한다. */
  label?: string
  /**
   * 지금 골라져 있는 항목(`pill` 전용) — **부모가 쥔다.**
   *
   * 🔴 알약의 선택은 이 컴포넌트 안에 두면 안 된다. 판의 × 로 닫는 것처럼
   * **바깥에서 선택이 풀리는 일**이 있어서, 안에 들고 있으면 알약만 골라진
   * 채로 남는다. 글자 줄의 `pinned`(눌러 띄워 둔 카드)와는 다른 것이다.
   */
  picked?: string | null
  /**
   * **눌러서 고른** 항목(`pill` 전용). `onActivate` 는 가리키기만 해도 불리므로
   * "이 사람이 실제로 고른 것"은 이쪽으로만 알 수 있다 — 알약이 판을 여는
   * 것 같은 실제 동작을 붙이려면 이걸 쓴다.
   */
  onPick?: (title: string) => void
}) {
  const pill = variant === 'pill'
  const navRef = useRef<HTMLElement>(null)
  const [hovered, setHovered] = useState<string | null>(null)
  const [pinned, setPinned] = useState<string | null>(null)
  /** 지금 골라져 있는 것 — 알약은 부모가, 글자 줄은 자기가 쥔다. */
  const selection = pill ? picked : pinned
  /**
   * 🔴 **알약에서는 고른 것과 떠 있는 것이 다르다.**
   * 글자 줄에서 `pinned` 는 "눌러서 띄워 둔 카드"지만, 알약에서 누르는 것은
   * **고르는 행위**다 — 누르면 설명이 사라져야 한다(사용자 요청). 그래서
   * 알약은 `pinned` 를 '골라 둔 것'으로만 쓰고, 떠 있는 것은 지금 가리킨
   * 것(`hovered`)뿐이다.
   */
  const shown = pill ? hovered : (hovered ?? pinned)

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
  // 알약은 여기서 빠진다 — 골라 둔 것은 바깥을 눌렀다고 풀리면 안 된다
  // (띄워 둔 카드가 아니라 선택이다).
  useEffect(() => {
    if (pinned === null || pill) return
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
  }, [pinned, pill, onActivate])

  function show(title: string | null) {
    setHovered(title)
    onActivate(title ?? selection)
  }

  return (
    <nav ref={navRef} aria-label={label}>
      <ul className={`ss-home-nav-list${pill ? ' ss-home-nav-list--pill' : ''}`}>
        {destinations.map((d, i) => {
          const open = shown === d.title
          const closing = !open && exiting === d.title
          return (
            <li
              key={d.title}
              className="relative"
              // 등장 순번. globals.css 가 이 값(--ss-nav-i)에 계단 간격을
              // 곱해 지연으로 쓴다. 둘의 **순서가 서로 반대**다(둘 다 사용자
              // 요청이라 하나로 못 합친다):
              //   글자 줄 — 맨 **왼쪽**('영상 분석')이 0번
              //   알약    — 맨 **오른쪽**('팀 찾기')이 0번
              style={{ '--ss-nav-i': pill ? destinations.length - 1 - i : i } as CSSProperties}
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
                // 눌러서 **골라 둔** 것. 가리키기만 한 것(data-active)과
                // 달라야 한다 — 고른 것만 안쪽이 옅게 칠해진다.
                data-selected={pill && selection === d.title ? 'true' : undefined}
                aria-expanded={open}
                onFocus={() => show(d.title)}
                onClick={() => {
                  if (pill) {
                    // 누르는 것은 **고르는 것**이다 — 설명은 사라진다.
                    // hovered 를 비워야 마우스가 아직 위에 있어도 안 뜬다.
                    // 선택 자체는 부모가 들고 있다(picked).
                    setHovered(null)
                    onActivate(d.title)
                    onPick?.(d.title)
                    return
                  }
                  const next = pinned === d.title ? null : d.title
                  setPinned(next)
                  onActivate(next)
                }}
                className={`ss-home-nav-item${pill ? ' ss-home-nav-item--pill' : ''}`}
                // 🔴 backdrop-filter 는 **인라인으로만** 준다 — globals.css 에
                // 두면 Lightning CSS 를 지나며 떨어져 나간 전례가 있다(추천
                // 판에서 계산값 none). GlassPanel 도 같은 방식이다.
                style={
                  pill
                    ? {
                        backdropFilter:
                          'blur(var(--ss-glass-blur)) saturate(var(--ss-glass-saturate))',
                        WebkitBackdropFilter:
                          'blur(var(--ss-glass-blur)) saturate(var(--ss-glass-saturate))',
                      }
                    : undefined
                }
              >
                {d.title}
              </button>

              {(open || closing) && (
                <div className="ss-home-nav-card" data-state={closing ? 'closing' : 'open'}>
                  <DestinationCard
                    compact
                    // 알약 위로 뜨는 판은 아이콘 · 제목을 뺀다 — 제목이 바로
                    // 아래 알약에 이미 있고, 판이 짧아야 위로 떠도 안 잘린다.
                    bare={pill}
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
