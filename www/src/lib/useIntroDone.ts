'use client'

import { useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'
import { INTRO_DONE_EVENT, hasSeenIntro, shouldPlayIntro } from '@/lib/intro'

/**
 * 인트로가 끝나기를 못 기다려 주는 한계. 이걸 넘기면 그냥 시작한다.
 *
 * 🔴 **안전장치가 없으면 화면이 영영 안 나온다.** 등장 애니메이션은 시작
 * 전 상태가 `opacity: 0` 이라, 어떤 이유로든 `INTRO_DONE_EVENT` 가 안 오면
 * 홈이 통째로 빈 화면이 된다. 인트로 전체 길이(4500ms)보다 넉넉히 잡는다.
 */
export const ENTRANCE_MAX_WAIT_MS = 7000

/**
 * "인트로가 끝났는가" — 홈의 등장 애니메이션을 시작할 순간이다.
 *
 * 인트로가 이번에 재생되지 않는 경로(이미 봤거나 진입점이 아닌 곳)에서는
 * 마운트 직후 바로 참이 된다. 재생되는 경우에만 `IntroGate` 가 쏘는
 * {@link INTRO_DONE_EVENT} 를 기다린다 — 안 기다리면 애니메이션이 잉크
 * **아래에서** 다 끝나 버려서 걷혔을 땐 이미 제자리에 있다.
 *
 * 판단 기준을 `IntroGate` 와 같은 함수(`shouldPlayIntro`)로 맞춰 둔 것이
 * 중요하다. 따로 판단하면 한쪽은 기다리고 한쪽은 안 트는 어긋남이 난다.
 */
export function useIntroDone(): boolean {
  const pathname = usePathname()
  const [done, setDone] = useState(false)

  useEffect(() => {
    // sessionStorage 는 서버에 없어 마운트 뒤에만 읽을 수 있다.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (!shouldPlayIntro(pathname, hasSeenIntro())) return setDone(true)

    const start = () => setDone(true)
    window.addEventListener(INTRO_DONE_EVENT, start)
    const timer = setTimeout(start, ENTRANCE_MAX_WAIT_MS)
    return () => {
      window.removeEventListener(INTRO_DONE_EVENT, start)
      clearTimeout(timer)
    }
  }, [pathname])

  return done
}
