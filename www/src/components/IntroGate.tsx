'use client'

import { useCallback, useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'
import GlitchIntro from './GlitchIntro'
import { INTRO_SEEN_KEY, shouldPlayIntro } from '@/lib/intro'

/**
 * `sessionStorage` 접근은 사파리 프라이빗 모드 등에서 던질 수 있다.
 * 던지면 "이미 봤다"로 친다 — 연출 때문에 앱이 안 열리는 것보다,
 * 인트로를 건너뛰는 편이 안전하다.
 */
function hasSeenIntro(): boolean {
  try {
    return sessionStorage.getItem(INTRO_SEEN_KEY) === '1'
  } catch {
    return true
  }
}

function markIntroSeen(): void {
  try {
    sessionStorage.setItem(INTRO_SEEN_KEY, '1')
  } catch {
    // 못 쓰면 그냥 둔다 — 다음 진입에서 다시 재생될 뿐, 화면은 정상 동작한다.
  }
}

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
  // 실패하면 애니메이션 없이 바로 부른다.
  const handleDone = useCallback(() => {
    setPlaying(false)
    markIntroSeen()
  }, [])

  if (!playing) return null

  return <GlitchIntro onDone={handleDone} />
}
