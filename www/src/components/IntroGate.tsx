'use client'

import { useCallback, useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'
import GlitchIntro from './GlitchIntro'
import { INTRO_DONE_EVENT, hasSeenIntro, markIntroSeen, shouldPlayIntro } from '@/lib/intro'

/** 앱 진입점(`/`, `/login`)에서 세션당 한 번, 잉크 번짐 인트로를 띄운다. */
export default function IntroGate() {
  const pathname = usePathname()
  const [playing, setPlaying] = useState(false)

  useEffect(() => {
    if (!shouldPlayIntro(pathname, hasSeenIntro())) return

    // 서버에는 sessionStorage 가 없어 이 판단 자체가 클라이언트 마운트 뒤에만
    // 가능하다 — 렌더 중에는 계산할 수 없는 값이라 effect 안에서 켠다.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPlaying(true)
  }, [pathname])

  // GlitchIntro가 자기 애니메이션(3600ms) 끝에 스스로 부른다 — 이미지 로드에
  // 실패하면 애니메이션 없이 바로 부른다. `INTRO_DONE_EVENT`는 `/`(LandingGate)
  // 처럼 "인트로가 끝난 뒤에 갈 곳을 정해야" 하는 쪽을 위한 신호다 — 여기서는
  // `loggedIn` 여부를 모르니 이동 판단은 하지 않고 이벤트만 쏜다.
  const handleDone = useCallback(() => {
    setPlaying(false)
    markIntroSeen()
    try {
      window.dispatchEvent(new Event(INTRO_DONE_EVENT))
    } catch {
      // 구형 환경 등에서 CustomEvent/Event 생성이 막혀 있어도 인트로
      // 자체는 이미 끝났다 — 여기서 실패해도 화면이 안 열리면 안 된다.
    }
  }, [])

  if (!playing) return null

  return <GlitchIntro onDone={handleDone} />
}
