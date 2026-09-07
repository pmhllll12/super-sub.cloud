'use client'

import { useLeaving } from '@/lib/pageTransition'

/**
 * 프로필 화면의 **무대**. 하는 일은 하나 — 지금 이 화면을 떠나는 중인지를
 * `data-leaving` 으로 알린다. 나머지 연출은 전부 CSS 가 한다(globals.css 의
 * "들고 남" 절).
 *
 * 🔴 `main` 을 클라이언트 컴포넌트로 만들지 않았다. 이 껍데기만 클라이언트고
 * 안에 담기는 것(카드 · 소속 · 정보 · 내 경기)은 서버에서 그린 그대로 내려온다.
 */
export default function ProfileStage({
  children,
  editing = false,
}: {
  children: React.ReactNode
  /** 카드 편집 모드인가 — 판 안의 배치가 통째로 바뀐다(globals.css). */
  editing?: boolean
}) {
  const leaving = useLeaving()
  return (
    <main
      className="ss-profile"
      data-leaving={leaving ? 'true' : undefined}
      data-editing={editing ? 'true' : undefined}
    >
      {children}
    </main>
  )
}
