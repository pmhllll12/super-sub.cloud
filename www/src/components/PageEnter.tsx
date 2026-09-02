'use client'

import { useLeaving } from '@/lib/pageTransition'
import { useIntroDone } from '@/lib/useIntroDone'

/**
 * 문서형 화면의 **등장 · 퇴장 껍데기**.
 *
 * 홈은 `HomeStage` 가 세 덩어리에 `data-enter` 를 직접 걸지만, 그건 한 화면을
 * 통째로 쓰는 연출 전용이다. 위에서 아래로 읽는 화면(레슨 · 상점 · 앞으로
 * 만들 것들)은 그럴 덩어리가 없어서 이 껍데기가 대신 건다.
 *
 * 🔴 안에서 움직일 것들은 `ss-rise` 를 달고 `--ss-rise-i` 로 차례를 준다.
 * 규칙은 globals.css 한 곳에 있고 여기서는 신호만 켠다 — 화면마다 애니메이션을
 * 따로 쓰기 시작하면 금세 제각각이 된다.
 *
 * `useIntroDone()` 은 인트로가 재생되지 않는 경로에서 **마운트 직후 참**이
 * 된다. 그 거짓 → 참이 곧 등장의 방아쇠다.
 */
export default function PageEnter({
  className = '',
  children,
}: {
  className?: string
  children: React.ReactNode
}) {
  const leaving = useLeaving()
  const entered = useIntroDone()

  return (
    <main className={className} data-enter={leaving ? 'out' : entered ? 'true' : 'false'}>
      {children}
    </main>
  )
}
