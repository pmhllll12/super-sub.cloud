'use client'

import { useEffect, type RefObject } from 'react'

/**
 * **판 위에서 굴리면 페이지가 안 움직인다** (2026-09-18, 사용자 지적).
 *
 * 홈은 아래가 영상 모음이라, 위에 뜬 판에서 목록을 보려고 굴리면 **페이지가
 * 통째로 내려가** 엉뚱한 자리로 간다. 「비슷한 팀」과 영상 쪽 「다음 영상」
 * 목록에서 같은 일이 났다.
 *
 * 🔴 **`overscroll-behavior: contain` 에 안 기댄다.** 먼저 그것으로 고쳤는데
 * **배포본에서 안 먹었다** — CSS 는 멀쩡히 살아 있었다(빌드본을 받아 확인).
 * 그리고 애초에 스크롤 상자가 아닌 자리(머리줄·아래 안내·`.ss-feed-list`)는
 * 그 속성이 걸리지도 않는다. 그래서 **휠을 우리가 통째로 받는다.**
 *
 * 🔴 **`passive: false` 로 붙인다** — React 의 `onWheel` 은 passive 라
 * `preventDefault()` 가 조용히 무시된다. 이것을 빠뜨리면 「고쳤는데 그대로」가
 * 된다.
 *
 * 🔴 **붙었다는 표식(`data-wheel-guard`)을 남긴다.** 안 붙으면 증상이 고치기
 * 전과 똑같아서, 배포가 안 된 것인지 코드가 틀린 것인지 화면만 보고는 못
 * 가른다 — 실제로 그것으로 한 번 헤맸다.
 */
export function useWheelTrap(
  /** 휠을 받을 판. 이 안에서는 페이지가 안 움직인다. */
  panel: RefObject<HTMLElement | null>,
  /**
   * 대신 굴릴 목록. 판 자신이면 같은 ref 를 준다.
   *
   * ⚠️ **없어도 된다** — 그때는 그냥 삼키기만 한다(구를 것이 없는 판).
   */
  scroller?: RefObject<HTMLElement | null>,
): void {
  useEffect(() => {
    const el = panel.current
    if (!el) return
    el.dataset.wheelGuard = 'on'

    function onWheel(e: WheelEvent) {
      /* 🔴 **구를 수 있으면 우리가 굴린다.** 브라우저에 맡기고 끝에서만
         막는 방식은 배포본에서 안 먹었다(위 머리말). */
      const box = scroller?.current
      if (box && box.scrollHeight > box.clientHeight) {
        box.scrollTop += e.deltaY
      }
      e.preventDefault()
    }

    el.addEventListener('wheel', onWheel, { passive: false })
    return () => {
      delete el.dataset.wheelGuard
      el.removeEventListener('wheel', onWheel)
    }
  }, [panel, scroller])
}
