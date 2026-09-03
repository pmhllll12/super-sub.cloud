'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ComponentProps,
  type MouseEvent,
} from 'react'

/**
 * 화면을 떠날 때의 연출 — **들어온 방향 그대로 되나간다**(사용자 요청).
 *
 * 등장이 이미 `data-enter` 하나로 돌아가고 있어서(globals.css), 여기서는
 * 값을 `'out'` 으로 바꿔 주기만 한다. 나가는 규칙은 CSS 쪽에 있다.
 *
 * 🔴 **이동을 애니메이션이 끝날 때까지 미룬다.** Next 의 라우팅은 즉시
 * 일어나므로 그냥 두면 화면이 먼저 갈려서 나가는 모습을 아무도 못 본다.
 * 그래서 링크를 가로채 `data-enter='out'` 을 켜고, {@link LEAVE_MS} 뒤에
 * `router.push` 한다.
 *
 * ⚠️ **가로채는 것은 화면을 갈아 끼우는 링크뿐이다.** 새 탭(⌘·Ctrl·가운데
 * 버튼)이나 다른 사이트로 가는 링크는 그대로 둔다 — 브라우저가 하던 일을
 * 뺏으면 사용자가 아는 동작이 깨진다.
 */

/**
 * 나가는 데 걸리는 시간.
 *
 * `globals.css` 의 `[data-enter='out']` 에서 **가장 늦게 끝나는 것**
 * (지연 240ms + 길이 560ms = 800ms)에 **여유 100ms** 를 더한 값이다.
 * 영상 분석 화면의 되감기(820ms)도 이 안에 들어간다.
 *
 * 🔴 여유가 없으면 마지막 프레임이 채 그려지기 전에 화면이 갈려 툭 끊긴다 —
 * 눈에 보이는 것은 이미 65% 지점에서 사라지지만, 딱 맞춰 두면 브라우저가
 * 한 프레임 늦는 것만으로 바로 드러난다. 짧으면 나가다 말고 갈리고, 길면
 * 빈 화면을 기다리게 된다.
 */
export const LEAVE_MS = 900

/**
 * Navigation API 중 우리가 쓰는 만큼만 적어 둔 모양.
 *
 * 🔴 `lib.dom` 에 아직 없어서 직접 적는다 — `any` 로 두면 오타가 그대로 지나간다.
 * 브라우저에 없을 수도 있으므로 쓰는 쪽에서 있는지 먼저 본다.
 */
type NavigateEventLike = Event & {
  navigationType: 'push' | 'replace' | 'reload' | 'traverse'
  cancelable: boolean
  hashChange: boolean
  downloadRequest: string | null
  destination: { url: string; key?: string }
}

type NavigationEventTarget = EventTarget & {
  traverseTo: (key: string) => { finished: Promise<unknown> }
}

/**
 * `leaveTo` 가 null 이면 **provider 밖**이다.
 *
 * 🔴 그때 링크는 **평범한 링크로 되돌아가야 한다.** 기본값을 빈 함수로 두면
 * 클릭을 가로채 놓고 아무 데도 안 가서 링크가 조용히 죽는다 — provider 를
 * 안 감싼 자리(테스트 · 새로 만든 트리)에서 알아채기 어려운 종류의 고장이다.
 */
type Ctx = {
  leaving: boolean
  /**
   * 나가는 중이면 **가려는 곳**, 아니면 null.
   *
   * 🔴 배경 사진이 이걸 본다(`AppFigure`). 화면마다 배경이 다른데, 갈 곳의
   * 배경이 **지금과 같으면 배경은 가만히 있어야** 한다 — 같은 사진이 나갔다
   * 들어오면 이유 없이 깜빡인 것으로 보인다. 그걸 알려면 목적지가 필요하다.
   */
  leavingTo: string | null
  leaveTo: ((href: string) => void) | null
  /** 화면 맨 위 줄(SiteHeader)을 지금 내보내야 하는가. */
  chromeHidden: boolean
  setChromeHidden: ((hidden: boolean) => void) | null
}

const LeaveContext = createContext<Ctx>({
  leaving: false,
  leavingTo: null,
  leaveTo: null,
  chromeHidden: false,
  setChromeHidden: null,
})

/** 지금 화면이 나가는 중인가 — `data-enter` 를 정할 때 쓴다. */
export function useLeaving(): boolean {
  return useContext(LeaveContext).leaving
}

/** 나가는 중이면 가려는 곳. 배경 사진이 방향과 필요 여부를 정할 때 쓴다. */
export function useLeavingTo(): string | null {
  return useContext(LeaveContext).leavingTo
}

/**
 * 헤더를 내보내 둔 상태인가 — `useLeaving()` 과 **같은 자리에서 같은 값**으로
 * 쓰인다(`data-enter='out'`). 화면을 떠나는 것은 아니지만 헤더는 나가야 하는
 * 경우가 있어서 갈라 두었다(영상 분석에서 판이 화면을 채울 때).
 */
export function useChromeHidden(): boolean {
  return useContext(LeaveContext).chromeHidden
}

/**
 * 이 화면이 떠 있는 동안 헤더를 내보낸다. 끄거나 화면을 떠나면 저절로 돌아온다.
 *
 * 🔴 헤더는 **레이아웃**이 그리므로 화면 컴포넌트가 직접 못 만진다. 라우팅을
 * 건너 살아 있는 이 provider 를 통해서만 말을 걸 수 있다.
 */
export function useHideChrome(hidden: boolean): void {
  const { setChromeHidden } = useContext(LeaveContext)
  useEffect(() => {
    setChromeHidden?.(hidden)
    return () => setChromeHidden?.(false)
  }, [hidden, setChromeHidden])
}

export function PageTransitionProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  /**
   * 나가는 중이면 **떠나던 경로**, 아니면 null.
   *
   * 🔴 참/거짓이 아니라 **경로**를 들고 있는 것이 핵심이다. 이 provider 는
   * 라우팅을 건너 살아남으므로(루트 레이아웃) 새 화면이 나가는 상태로
   * 태어나면 안 되는데, 그걸 effect 에서 풀면 **한 프레임 늦는다** —
   *
   *   나가는 중(보임) → 새 화면이 아직 'out' 인 채로 한 번 그려짐(깜빡)
   *   → effect 가 풀어 'false'(사라짐) → 그제서야 밖에서 들어옴
   *
   * 실제로 그렇게 보였다("깜빡이다가 사라졌다가 다시 들어온다"). 경로를
   * 비교하면 새 경로가 온 **그 렌더에서** 곧바로 거짓이 되어 중간 프레임이
   * 아예 생기지 않는다.
   */
  const [leavingFrom, setLeavingFrom] = useState<string | null>(null)
  /** 가려는 곳. `leavingFrom` 과 짝이라 같이 세우고 같이 버린다. */
  const [leavingTo, setLeavingTo] = useState<string | null>(null)
  const [chromeHidden, setChromeHidden] = useState(false)
  const leaving = leavingFrom !== null && leavingFrom === pathname
  const timer = useRef(0)

  // 다 옮겨 갔으면 들고 있던 경로도 버린다(예약해 둔 이동도 같이 거둔다).
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLeavingFrom(null)
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLeavingTo(null)
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setChromeHidden(false)
    return () => clearTimeout(timer.current)
  }, [pathname])

  const leaveTo = useCallback(
    (href: string) => {
      // 이미 간 곳으로 또 가지 않는다 — 나가는 연출만 돌고 제자리가 된다.
      if (href === pathname) return
      // 움직임을 줄이라고 한 사람에게는 기다릴 이유가 없다.
      const reduced =
        typeof window !== 'undefined' &&
        window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
      if (reduced) {
        router.push(href)
        return
      }
      setLeavingFrom(pathname)
      setLeavingTo(href)
      clearTimeout(timer.current)
      timer.current = window.setTimeout(() => router.push(href), LEAVE_MS)
    },
    [router, pathname],
  )

  /**
   * 🔴 **뒤로 · 앞으로 가기도 링크와 똑같이 나갔다 들어온다**(사용자 요청).
   *
   * 링크는 우리가 클릭을 가로채 나가는 연출을 돌린 뒤에 옮기지만, 브라우저의
   * 뒤로/앞으로 단추는 그 길을 안 지난다 — 화면이 툭 갈려서 나가는 연출만 빠진
   * 반쪽이 된다(사용자 지적).
   *
   * 그래서 **오가는 것 자체를 한 번 물린다**: 이동을 취소하고(preventDefault),
   * 나가는 연출을 돌리고, 끝나면 **같은 자리로 다시 보낸다**(`traverseTo`).
   * 링크가 하는 일과 순서가 같으므로 보이는 것도 같다.
   *
   * 🔴 **주소가 같은 이동은 그냥 보낸다.** 화면 안에서 판을 여닫는 걸음도
   * 기록에 쌓이는데(`MarketGates`), 그건 화면을 떠나는 것이 아니라서 나가는
   * 연출을 돌리면 안 된다.
   *
   * ⚠️ Navigation API 가 있는 브라우저(크롬 계열)에서만 걸린다. 없으면 지금까지처럼
   * 뒤로/앞으로가 곧바로 갈린다 — 기능이 죽는 것이 아니라 연출만 빠진다.
   */
  useEffect(() => {
    const nav = (window as unknown as { navigation?: NavigationEventTarget }).navigation
    if (!nav) return

    let replaying = false

    const onNavigate = (e: NavigateEventLike) => {
      if (replaying) return
      if (e.navigationType !== 'traverse' || !e.cancelable) return
      if (e.hashChange || e.downloadRequest !== null) return
      // 같은 주소면 화면을 떠나는 것이 아니다(판 여닫기 등) — 손대지 않는다.
      if (e.destination.url === window.location.href) return
      const key = e.destination.key
      if (!key) return
      // 움직임을 줄이라고 한 사람에게는 기다릴 이유가 없다(링크와 같은 규칙).
      if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return

      e.preventDefault()
      setLeavingFrom(window.location.pathname)
      setLeavingTo(new URL(e.destination.url).pathname)
      clearTimeout(timer.current)
      timer.current = window.setTimeout(() => {
        replaying = true
        nav.traverseTo(key).finished.catch(() => {}).finally(() => {
          replaying = false
        })
      }, LEAVE_MS)
    }

    nav.addEventListener('navigate', onNavigate as EventListener)
    return () => nav.removeEventListener('navigate', onNavigate as EventListener)
  }, [])

  return (
    <LeaveContext.Provider
      value={{ leaving, leavingTo: leaving ? leavingTo : null, leaveTo, chromeHidden, setChromeHidden }}
    >
      {children}
    </LeaveContext.Provider>
  )
}

/**
 * 나가는 연출을 거쳐 이동하는 링크. 그 밖에는 `next/link` 와 똑같다 —
 * `href` 를 그대로 두므로 새 탭 열기 · 링크 주소 복사 · 스크린리더가 다 산다.
 */
export function TransitionLink({
  href,
  onClick,
  ...rest
}: ComponentProps<typeof Link> & { href: string }) {
  const { leaveTo } = useContext(LeaveContext)

  return (
    <Link
      href={href}
      onClick={(e: MouseEvent<HTMLAnchorElement>) => {
        onClick?.(e)
        if (e.defaultPrevented) return
        // provider 밖이면 가로채지 않는다 — 평범한 링크로 둔다.
        if (!leaveTo) return
        // 새 탭 · 새 창 · 다운로드는 브라우저에게 맡긴다.
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return
        e.preventDefault()
        leaveTo(href)
      }}
      {...rest}
    />
  )
}
