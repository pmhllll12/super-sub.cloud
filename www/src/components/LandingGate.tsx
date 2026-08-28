'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { INTRO_DONE_EVENT, hasSeenIntro, shouldPlayIntro } from '@/lib/intro'

/**
 * `/`(랜딩) 전용. 로그인 쿠키가 있으면 **인트로가 끝난 뒤** `/home`으로
 * 보낸다.
 *
 * `page.tsx`(서버)는 쿠키 존재만 보고 `loggedIn`을 내려줄 뿐 리다이렉트하지
 * 않는다 — 서버에서 바로 리다이렉트하면 루트 레이아웃의 `IntroGate`가 뜰
 * 기회조차 없어(그 요청 자체가 `/home`으로 응답된다) 로그인한 사람은 인트로를
 * 영영 못 본다. 그래서 판단을 여기, 클라이언트로 미룬다:
 *
 * - 이번에 인트로가 재생되지 않는 상황(이미 본 세션 등, `shouldPlayIntro`
 *   기준은 `IntroGate`와 동일하다)이면 마운트하자마자 바로 판단한다.
 * - 재생된다면 `IntroGate`가 끝날 때 쏘는 [INTRO_DONE_EVENT]를 기다렸다가
 *   판단한다 — 인트로가 나오는 도중에 화면이 홱 바뀌면 안 된다.
 *
 * 로그아웃 상태면 아무 것도 하지 않는다 — `LandingBody`가 그대로 보인다.
 *
 * `router.replace`를 쓴다. `push`면 뒤로 가기를 눌렀을 때 인트로 화면(사실은
 * 이미 다 걷힌 랜딩)으로 돌아오는 게 이상하다 — 히스토리에 남기지 않는다.
 */
export default function LandingGate({ loggedIn }: { loggedIn: boolean }) {
  const router = useRouter()

  useEffect(() => {
    if (!loggedIn) return

    if (!shouldPlayIntro('/', hasSeenIntro())) {
      router.replace('/home')
      return
    }

    const goHome = () => router.replace('/home')
    window.addEventListener(INTRO_DONE_EVENT, goHome)
    return () => window.removeEventListener(INTRO_DONE_EVENT, goHome)
  }, [loggedIn, router])

  return null
}
