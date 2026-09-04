'use client'

import { useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'
import type { PublicPlayerCard } from '@/server/backend'
import PlayerCardView from '@/components/PlayerCardView'
import BrandMark from '@/components/ui/BrandMark'
import HomeNav, { type Destination } from '@/components/HomeNav'
import { HEADER_LINK_CLASS, HEADER_LINK_HOVER_CLASS } from '@/components/LogoutButton'
import { useIntroDone } from '@/lib/useIntroDone'
import { TransitionLink, useChromeHidden, useLeaving } from '@/lib/pageTransition'

/** 프로필에서 로고가 가운데였다는 표시 — 홈이 되돌아오는 연출을 켤 때 읽는다. */
const MARK_WAS_CENTERED = 'ss-mark-was-centered'

/**
 * 화면 맨 위 줄 — 워드마크 · 목적지 글자 · 내 프로필.
 *
 * 홈에만 있던 것을 **로그인 뒤 모든 화면**으로 옮겼다(사용자 요청). 화면마다
 * 다시 만들지 않고 이 하나를 홈(`HomeStage`)과 `(app)` 레이아웃이 같이 쓴다 —
 * 두 벌이면 목적지가 늘 때 한쪽만 고치게 된다.
 *
 * 🔴 **홈에서만 화면에 고정한다**(`fixed`). 홈은 한 화면을 통째로 쓰는 배치라
 * 헤더가 흐름에 있으면 가운데 정렬이 밀린다. 다른 화면은 위에서 아래로 읽는
 * 문서라 흐름에 두는 편이 낫다 — 고정해 두면 그만큼 본문에 위 여백을 따로
 * 줘야 하고, 그 값이 카드 유무에 따라 달라져 어긋난다.
 */
export default function SiteHeader({
  user,
  card = null,
  destinations,
  fixed = false,
}: {
  user: { nickname: string } | null
  card?: PublicPlayerCard | null
  destinations: Destination[]
  /** 홈처럼 화면에 고정할 것인가. 기본은 흐름에 둔다. */
  fixed?: boolean
}) {
  /**
   * 인트로가 걷히면 각자 바깥에서 제자리로 들어온다(globals.css 의
   * `[data-enter]`). 워드마크만 빠진다 — 인트로의 글자가 그 자리로 날아와
   * 앉으므로 따로 등장시키면 같은 글자가 두 번 나타난다.
   */
  const leaving = useLeaving()
  // 화면을 떠나는 것은 아니지만 헤더만 비켜야 할 때가 있다 — 영상 분석에서
  // 판이 화면을 채우는 순간이다. 나가는 모습은 완전히 같다.
  const hidden = useChromeHidden()
  const entered = useIntroDone()
  // 'out' 이면 들어온 방향 그대로 되나간다(globals.css).
  const enter = leaving || hidden ? 'out' : entered ? 'true' : 'false'

  /** 지금 가리킨 목적지. 글자 줄 안에서만 쓰는 강조다. */
  const [active, setActive] = useState<string | null>(null)

  /**
   * 🔴 **지금 보고 있는 화면은 목적지에서 뺀다**(사용자 요청). 영상 분석
   * 화면에서 '영상 분석' 글자를 누르면 같은 자리로 다시 가는 셈이라, 눌러도
   * 아무 일이 없는 것처럼 보인다(나가는 연출까지 돌고 제자리다).
   */
  const pathname = usePathname()
  const shown = destinations.filter((d) => d.href !== pathname)

  /**
   * 🔴 **프로필 화면에서는 목적지 글자도 '내 프로필'도 내보내지 않는다**
   * (사용자 요청). 위 `shown` 이 "지금 보고 있는 화면은 목적지에서 뺀다"는
   * 규칙인데, 이 화면은 그 규칙을 **줄 전체에** 적용한 셈이다. 남는 길은
   * 워드마크(홈)뿐이다.
   *
   * 🔴 **DOM 에서 빼지 않고 안 보이게만 한다.** 목적지 글자 칸은
   * `flex: 1 1 auto` 에 `justify-content: flex-end` 라(globals.css), 한쪽
   * 덩어리가 없어지면 남은 것들이 자리를 다시 나눠 갖는다 — 화면을 오갈
   * 때마다 글자 줄이 좌우로 튄다(실측: 프로필만 빼도 그랬다). 자리를
   * 남기면 그 튐이 없다.
   *
   * `visibility: hidden` 이라 링크는 눌리지도, 탭으로 잡히지도, 읽어 주는
   * 기계에 걸리지도 않는다. 헤더가 통째로 타는 등장 · 퇴장 연출
   * (`data-enter`)은 그대로다 — 다른 화면에서와 같은 방식으로 사라졌다가
   * 같은 방식으로 돌아온다.
   */
  const bare = pathname === '/me'

  /**
   * 🔴 **되돌아오는 연출**을 위한 표시.
   *
   * 로고가 가운데로 가는 것은 프로필에서 애니메이션으로 보이는데, 거기서
   * **나갈 때**는 안 보였다 — 홈은 `(app)` 그룹 밖이라 헤더가 새로 태어나고,
   * 새 헤더는 자기가 어디서 왔는지 모른 채 처음부터 왼쪽에 있기 때문이다.
   *
   * 그래서 프로필에 있는 동안 표시를 남겨 두고, 홈이 그것을 보고 한 번만
   * 되돌아오는 연출을 켠다. `sessionStorage` 인 것은 새로고침이나 새 탭까지
   * 따라오면 안 되기 때문이다.
   */
  const [returning, setReturning] = useState(false)

  useEffect(() => {
    try {
      if (bare) {
        sessionStorage.setItem(MARK_WAS_CENTERED, '1')
        return
      }
      // 홈에서만 되돌린다 — 다른 화면으로 빠져나갈 때는 로고가 원래 왼쪽이라
      // 움직일 것이 없다. 표시는 어디로 갔든 지운다(한 번만 도는 연출이다).
      const had = sessionStorage.getItem(MARK_WAS_CENTERED)
      if (had) sessionStorage.removeItem(MARK_WAS_CENTERED)
      // 🔴 이 상태만은 **렌더 중에 맞출 수 없다.** `sessionStorage` 는
      // 브라우저에만 있어서, 렌더 중에 읽으면 서버가 그린 것과 달라져
      // hydration 이 깨진다. 마운트한 뒤에 한 번 읽는 수밖에 없다.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      if (had && pathname === '/') setReturning(true)
    } catch {
      // 사생활 보호 모드 등에서 sessionStorage 가 막힐 수 있다 — 연출 하나
      // 때문에 헤더가 죽지 않게 조용히 넘어간다.
    }
  }, [bare, pathname])

  return (
    <div
      // 워드마크 · 목적지 글자 · 인사말 세 덩어리 사이는 목적지 글자
      // **칸 사이(40px)보다 넉넉히** 띄운다 — 안 그러면 닉네임이 목적지
      // 글자 하나처럼 붙어 읽힌다(실측: 32px 이면 그렇게 보였다).
      // 🔴 `relative` 와 `fixed` 를 **같이 쓰지 않는다.** 유틸리티 클래스는
      // 문자열에 적은 순서가 아니라 **CSS 파일에 실린 순서**로 이긴다 —
      // Tailwind 에서는 `relative` 가 `fixed` 보다 뒤에 있어서, 둘 다 주면
      // 늘 `relative` 가 이긴다. 홈 헤더가 흐름에 남아 무대를 통째로 아래로
      // 밀어냈다. 자리를 정하는 클래스는 **하나만** 고른다.
      className={`ss-home-header z-20 flex items-start justify-between gap-16 ${
        fixed ? 'fixed inset-x-0 top-0' : 'relative'
      }`}
      style={{ padding: 'var(--ss-home-content-pad)' }}
      data-enter={enter}
    >
      {/* 홈으로 가는 길. 인트로의 글자가 날아와 앉는 자리이기도 하다
          (`[data-brand-mark]` 로 찾는다 — BrandMark 참고). */}
      <TransitionLink
        href="/"
        aria-label="홈"
        className={`ss-home-mark${bare ? ' ss-home-mark-center' : ''}${
          returning ? ' ss-home-mark-returning' : ''
        }`}
      >
        <BrandMark size={26} />
      </TransitionLink>

      <div className={`ss-home-nav-slot${bare ? ' ss-home-gone' : ''}`}>
        <HomeNav
          destinations={shown}
          loggedIn={Boolean(user)}
          active={active}
          onActivate={setActive}
        />
      </div>

      {user ? (
        /* '내 프로필' 자리다 — 목적지 글자 줄에 같은 항목을 또 두지
           않는다(사용자 요청). 카드가 있으면 그 카드를 작게 줄여
           보여주고, 없으면 닉네임 글자로 대신한다. 어느 쪽이든 누르면
           /me 로 가고, 카드 아래에 무엇인지 적어 둔다 — 카드만 있으면
           눌러 보기 전엔 어디로 가는지 알 수 없다. */
        <TransitionLink
          href="/me"
          className={`ss-home-profile shrink-0${bare ? ' ss-home-gone' : ''}`}
        >
          {card ? (
            <span className="ss-pcard-mini">
              <PlayerCardView card={card} />
            </span>
          ) : (
            <span style={{ color: 'var(--ss-fg)' }}>{user.nickname}</span>
          )}
          <span className="ss-home-profile-label">내 프로필</span>
        </TransitionLink>
      ) : (
        <div className="flex shrink-0 items-center gap-1">
          <TransitionLink
            href="/login"
            className={`${HEADER_LINK_CLASS} ${HEADER_LINK_HOVER_CLASS}`}
            style={{ color: 'var(--ss-accent)' }}
          >
            로그인
          </TransitionLink>
          <TransitionLink
            href="/signup"
            className={`${HEADER_LINK_CLASS} ${HEADER_LINK_HOVER_CLASS}`}
            style={{ color: 'var(--ss-fg)' }}
          >
            회원가입
          </TransitionLink>
        </div>
      )}
    </div>
  )
}
