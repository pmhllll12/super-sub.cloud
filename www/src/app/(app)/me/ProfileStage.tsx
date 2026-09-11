'use client'

import { useEffect, useState } from 'react'
import { useLeaving } from '@/lib/pageTransition'
import { ReportPanelContext } from './reportPanel'

/**
 * 들어오는 연출이 다 끝나는 시각 — 가장 늦은 것(1080ms 지연 + 460ms)에
 * 여유를 조금 얹었다. `globals.css` 의 「들고 남」 절과 **같이 고쳐야 한다.**
 */
const ENTER_MS = 1700

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

  /**
   * 🔴 **들어오는 연출이 끝났는가.**
   *
   * 들고 나는 연출은 요소가 붙는 순간 도는데, 이 화면에는 **나중에 붙는
   * 것들**이 있다 — 리포트 판은 영상을 넘길 때마다 잠깐 떨어졌다 돌아오고,
   * 「이 장면이 돕니다」 줄은 대표 영상을 세울 때 생긴다. 그때마다 1080ms
   * 를 기다렸다 나타나면 **눌러 놓고 1초 넘게 아무 일도 안 일어난다.**
   *
   * 그래서 처음 한 번만 연출을 걸고, 끝나면 꺼 둔다 — CSS 쪽은
   * `.ss-profile:not([data-entered]) …` 로 받는다.
   */
  /**
   * 🔴 **리포트 판이 열려 있는가.** 오른쪽 칸의 단추가 켜고, 그러면 왼쪽
   * 칸이 통째로 왼쪽으로 밀려난다(사용자 요청) — 두 칸의 공통 조상이
   * 여기뿐이라 값을 여기서 쥔다(`data-editing` 과 같은 구조).
   */
  const [report, setReport] = useState(false)

  const [entered, setEntered] = useState(false)
  useEffect(() => {
    const t = setTimeout(() => setEntered(true), ENTER_MS)
    return () => clearTimeout(t)
  }, [])

  return (
    <ReportPanelContext.Provider value={{ open: report, setOpen: setReport }}>
      <main
        className="ss-profile"
        data-entered={entered ? 'true' : undefined}
        data-leaving={leaving ? 'true' : undefined}
        data-editing={editing ? 'true' : undefined}
        data-report={report ? 'true' : undefined}
      >
        {children}
      </main>
    </ReportPanelContext.Provider>
  )
}
