'use client'

import { useEffect, useId, useRef, useState, type CSSProperties } from 'react'
import DestinationCard from './DestinationCard'
import { TransitionLink } from '@/lib/pageTransition'

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
 * 🔴 **2026-09-08 에 글자 줄이 뒤집혔다**(사용자 요청). 전에는 *글자가
 * 버튼이고 떠오른 유리 카드가 링크*였다. 지금은 반대다:
 *
 *   - **아이콘이 글자 위에 서고, 그 둘을 한 링크가 감싼다** — 눌러서 이동
 *   - 떠오르는 것은 **설명 글자뿐**이다. 유리판(사각 버튼)도 아이콘도 없다
 *     (알약 줄이 이미 그 모양이었다 — `DestinationCard` 의 `bare`)
 *
 * 뒤집으면서 **한 항목에 링크는 여전히 하나**다. 둘 다 링크로 두면 같은 곳으로
 * 가는 링크가 둘이 되어 낭독기에서도 시험에서도 어느 쪽인지 모호해진다 —
 * 원래 글자를 버튼으로 둔 이유가 그것이었고, 이제 반대쪽이 버튼(설명)이다.
 *
 * 마우스가 없는 자리(터치 · 키보드)를 위해 둘을 받는다:
 * - `hover` — 대면 설명이 나오고 치우면 사라진다
 * - `focus` — Tab 으로 닿아도 나온다
 *
 * ⚠️ **눌러서 고정하는 것은 없앴다.** 이제 누르면 이동이라 고정할 자리가
 * 없다 — 터치에서는 설명을 못 보고 바로 들어가는데, 그게 링크의 평범한
 * 동작이라 오히려 예측 가능하다. 알약 줄은 그대로다(거기서 누르는 것은
 * 여전히 '고르는 것'이다).
 *
 * 사라질 때는 바로 없애지 않고 {@link CARD_EXIT_MS} 동안 흐려지며
 * 물러난다. 그동안 DOM 에 남겨 둬야 해서(`exiting`) 지금 떠 있는 것과
 * 지금 사라지는 중인 것을 따로 센다.
 */
// 카드가 나타나고 사라지는 시간 — globals.css 의 ss-card-in/out 과 같아야
// 한다. 여기가 짧으면 애니메이션 도중에 잘리고, 길면 사라진 자리가 남는다.
const CARD_EXIT_MS = 180

/**
 * 글자 줄 항목의 껍데기 — **갈 곳이 있으면 링크, 없으면 버튼**이다.
 *
 * 🔴 `<a>` 를 href 없이 두면 Tab 으로 닿지도 않고 눌러도 아무 일이 없다.
 * 갈 곳이 없는 목적지가 아직 있어서(계약이 안 열린 화면) 그 경우를 갈라야 한다.
 */
function Trigger({
  href,
  children,
  ...rest
}: {
  href?: string
  children: React.ReactNode
} & React.HTMLAttributes<HTMLElement>) {
  if (href) {
    return (
      <TransitionLink href={href} {...rest}>
        {children}
      </TransitionLink>
    )
  }
  return (
    <button type="button" {...rest}>
      {children}
    </button>
  )
}

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
   * 채로 남는다.
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
  const ids = useId()
  const [hovered, setHovered] = useState<string | null>(null)
  /** 지금 골라져 있는 것 — 알약만 있다(부모가 쥔다). */
  const selection = pill ? picked : null
  /**
   * 🔴 **떠 있는 것은 지금 가리킨 것뿐이다.** 알약에서 누르는 것은 *고르는
   * 행위*라 설명이 사라져야 하고(사용자 요청), 글자 줄에서 누르는 것은 이제
   * *이동*이라 띄워 둘 것이 없다 — 양쪽 다 `hovered` 하나로 정해진다.
   */
  const shown = hovered

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

  /* ⚠️ **바깥 클릭 · Esc 로 푸는 장치는 걷어냈다**(2026-09-08). 그건 *눌러서
     고정한 카드*를 풀기 위한 것이었는데, 글자 줄에서 누르는 것이 이동이 되면서
     고정 자체가 없어졌다 — 풀 것이 없는 자리에 문서 전역 리스너를 걸어 둘
     이유가 없다. */

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
              {pill ? (
                <button
                  type="button"
                  data-active={active === d.title ? 'true' : undefined}
                  // 눌러서 **골라 둔** 것. 가리키기만 한 것(data-active)과
                  // 달라야 한다 — 고른 것만 안쪽이 옅게 칠해진다.
                  data-selected={selection === d.title ? 'true' : undefined}
                  aria-expanded={open}
                  onFocus={() => show(d.title)}
                  onClick={() => {
                    // 누르는 것은 **고르는 것**이다 — 설명은 사라진다.
                    // hovered 를 비워야 마우스가 아직 위에 있어도 안 뜬다.
                    // 선택 자체는 부모가 들고 있다(picked).
                    setHovered(null)
                    onActivate(d.title)
                    onPick?.(d.title)
                  }}
                  className="ss-home-nav-item ss-home-nav-item--pill"
                  // 🔴 backdrop-filter 는 **인라인으로만** 준다 — globals.css 에
                  // 두면 Lightning CSS 를 지나며 떨어져 나간 전례가 있다(추천
                  // 판에서 계산값 none). GlassPanel 도 같은 방식이다.
                  style={{
                    backdropFilter:
                      'blur(var(--ss-glass-blur)) saturate(var(--ss-glass-saturate))',
                    WebkitBackdropFilter:
                      'blur(var(--ss-glass-blur)) saturate(var(--ss-glass-saturate))',
                  }}
                >
                  {d.title}
                </button>
              ) : (
                /* 🔴 **아이콘이 글자 위에 서고, 둘을 한 링크가 감싼다**
                   (사용자 요청, 2026-09-08). 아이콘은 원래 떠오르는 유리
                   카드 안에 있었는데, 그 판을 없애면서 갈 데가 없어졌다 —
                   글자 위가 그 자리다.

                   🔴 갈 곳이 없으면 **링크가 아니라 버튼**이다. `<a>` 를
                   href 없이 두면 Tab 으로 닿지도 않고 눌러도 아무 일이 없어
                   "왜 안 되나"만 남는다. */
                <Trigger
                  href={d.href}
                  className="ss-home-nav-item ss-home-nav-item--stack"
                  data-active={active === d.title ? 'true' : undefined}
                  aria-describedby={open ? `${ids}-${i}` : undefined}
                  onFocus={() => show(d.title)}
                >
                  {/* 굵기 · 광학 크기는 `.ss-dest-icon` 이 정한다(globals.css) —
                      유리 카드 안에 있을 때와 같은 값을 쓴다. */}
                  <span
                    aria-hidden="true"
                    className="material-symbols-outlined ss-dest-icon ss-home-nav-icon"
                  >
                    {d.icon}
                  </span>
                  <span className="ss-home-nav-label">{d.title}</span>
                </Trigger>
              )}

              {(open || closing) && (
                <div
                  className="ss-home-nav-card"
                  data-state={closing ? 'closing' : 'open'}
                  id={pill ? undefined : `${ids}-${i}`}
                >
                  <DestinationCard
                    compact
                    /* 🔴 **양쪽 다 판이 없다**(2026-09-08). 알약 위로 뜨던 것만
                       그랬는데, 글자 줄도 사각 판을 걷어내고 설명만 남겼다
                       (사용자 요청). 아이콘 · 제목은 이미 버튼 쪽에 있다. */
                    bare
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
