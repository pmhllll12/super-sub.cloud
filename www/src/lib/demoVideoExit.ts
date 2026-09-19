'use client'

/** 사용법 영상에 「비켜 달라」고 알리는 창 이벤트. `DemoVideo` 가 듣는다. */
export const DEMO_EXIT_EVENT = 'supersub:demo-exit'

/**
 * 영상이 빠져나가는 데 기다려 주는 최대 시간. 영상이 없거나(다른 화면) 이벤트를
 * 못 받아도 로그인이 이보다 오래 멈추지 않는다 — 🔴 **로그인을 영상에 볼모로
 * 잡히게 두지 않는다.**
 */
export const DEMO_EXIT_MAX_MS = 400

export type DemoExitDetail = { done: () => void }

/**
 * 로그인에 성공한 직후, 홈으로 가기 **전에** 부른다(사용자 요청). 사용법 영상과
 * 붙은 단추가 가장 가까운 가장자리로 빠져나간 뒤에 풀린다 — 그다음 홈으로 가면
 * 영상이 같은 가장자리에서 들어와 로그인 화면에서의 자리·크기 그대로 앉는다.
 *
 * 로그인 길(이메일·원티드 테스트용·구글)마다 `router.push('/home')` 앞에 둔다.
 */
export function leaveDemoVideo(): Promise<void> {
  if (typeof window === 'undefined') return Promise.resolve()
  return new Promise((resolve) => {
    let settled = false
    const done = () => {
      if (settled) return
      settled = true
      resolve()
    }
    window.dispatchEvent(new CustomEvent<DemoExitDetail>(DEMO_EXIT_EVENT, { detail: { done } }))
    setTimeout(done, DEMO_EXIT_MAX_MS)
  })
}
