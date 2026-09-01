'use client'

import { useEffect, useRef } from 'react'
import { useLeaving } from '@/lib/pageTransition'

/**
 * 한 화면을 **번갈아 쓴다.**
 *
 * 이 화면은 굴러가지 않는다(사용자 요청). 굴리려는 몸짓은 자리를 옮기는 신호일
 * 뿐이고, 실제로 일어나는 일은 이것뿐이다.
 *
 * ```
 *   내리려 하면   표지 글이 나간다  →  그 자리에 두 문이 들어온다
 *   올리려 하면   두 문이 나간다   →  그 자리에 표지 글이 돌아온다
 * ```
 *
 * 🔴 **굴리지 않는 것이 연출의 절반이다.** 화면이 밀리면 표지 글이 옆으로 나가는
 * 동안 위로도 같이 올라가 두 축이 섞여 보인다(사용자 지적). 굴림 자체를 없애면
 * (globals.css 의 `body:has(.ss-market-entry) { overflow: hidden }`) 옆으로만 간다.
 *
 * 🔴 신호는 `<html>` 의 두 속성으로 흘린다. 이걸 보고 움직여야 하는 것이 페이지
 * 안(표지 글 · 두 문)과 루트(`AppFigure` 의 아치 글자)로 흩어져 있어 공통 조상이
 * 문서뿐이다.
 *   `data-ss-scrolled='true'`  표지 글이 나가 있다
 *   `data-ss-gates='out'`      두 문이 나가는 중이다(되돌아가는 길)
 */

/** 두 문이 다 나가고 표지 글이 돌아오기까지. `globals.css` 의 500ms 와 짝이다. */
const GATES_OUT_MS = 520

/**
 * 화면을 떠난 뒤 "나갔다" 는 표시를 지우기까지 기다리는 시간.
 *
 * `AppFigure` 가 나가는 배경 층을 걷는 시각(`MOVE_MS + MARK_TAIL_MS`)보다
 * 넉넉해야 한다 — 그 전에 지우면 나가던 아치 글자가 되돌아온다.
 */
const LEAVE_TAIL_MS = 1600

/**
 * 이보다 작은 굴림은 **없던 것으로 친다.**
 *
 * 🔴 트랙패드는 한 번 굴리는 동안 `deltaY` 가 0 이나 아주 작은 반대 부호로도
 * 들어온다. 부호만 보고 방향을 정하면 내리는 몸짓 한가운데에 "올린다" 가 섞여
 * 방금 내보낸 것을 도로 불러들인다.
 */
const DEAD_ZONE = 4

/**
 * 지금 살아 있는 문지기가 몇 번째인가.
 *
 * 🔴 개발 모드(StrictMode)는 effect 를 **마운트 → 정리 → 다시 마운트** 로 한 번
 * 더 돌린다. 그 가짜 정리가 예약해 둔 "표시 지우기" 타이머가 나중에 터지면서,
 * 멀쩡히 내보낸 표시를 지워 사라졌던 것이 다시 나왔다(사용자 지적).
 */
let generation = 0

export default function HeroGate() {
  /**
   * 🔴 떠나는 중에는 아무것도 되돌리지 않는다 — 있던 자리 그대로 나가야 한다.
   * ref 로 들고 있는 이유는 아래 effect 를 다시 걸지 않기 위해서다.
   */
  const leaving = useLeaving()
  const leavingRef = useRef(leaving)
  useEffect(() => {
    leavingRef.current = leaving
  }, [leaving])

  useEffect(() => {
    const el = document.documentElement
    const mine = ++generation
    let back = 0
    let touchY = 0

    const set = (key: 'ssScrolled' | 'ssGates', v: string | null) => {
      if (v === null) delete el.dataset[key]
      else if (el.dataset[key] !== v) el.dataset[key] = v
    }

    set('ssScrolled', 'false')
    set('ssGates', null)

    const away = () => el.dataset.ssScrolled === 'true'

    const show = () => {
      if (away()) return
      set('ssGates', null)
      set('ssScrolled', 'true')
    }

    /** 문이 먼저 나가고, 그 뒤에 표지 글이 돌아온다. */
    const back0 = () => {
      if (!away() || back) return
      set('ssGates', 'out')
      back = window.setTimeout(() => {
        back = 0
        set('ssScrolled', 'false')
        set('ssGates', null)
      }, GATES_OUT_MS)
    }

    const move = (dir: number) => {
      if (dir === 0 || leavingRef.current) return
      if (dir > 0) show()
      else back0()
    }

    const dirOf = (d: number) => (d > DEAD_ZONE ? 1 : d < -DEAD_ZONE ? -1 : 0)

    const onWheel = (e: WheelEvent) => {
      if (e.ctrlKey) return
      move(dirOf(e.deltaY))
    }

    const onTouchStart = (e: TouchEvent) => {
      touchY = e.touches[0]?.clientY ?? 0
    }

    const onTouchMove = (e: TouchEvent) => {
      const y = e.touches[0]?.clientY ?? 0
      // 손가락이 위로 = 내용은 아래로 = 내리는 것.
      move(dirOf(touchY - y))
    }

    /** 자판으로도 오갈 수 있어야 한다 — 굴림이 없으니 이게 유일한 다른 길이다. */
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown' || e.key === 'PageDown' || e.key === ' ') move(1)
      else if (e.key === 'ArrowUp' || e.key === 'PageUp') move(-1)
    }

    window.addEventListener('wheel', onWheel, { passive: true })
    window.addEventListener('touchstart', onTouchStart, { passive: true })
    window.addEventListener('touchmove', onTouchMove, { passive: true })
    window.addEventListener('keydown', onKey)

    return () => {
      window.removeEventListener('wheel', onWheel)
      window.removeEventListener('touchstart', onTouchStart)
      window.removeEventListener('touchmove', onTouchMove)
      window.removeEventListener('keydown', onKey)
      if (back) clearTimeout(back)
      set('ssGates', null)
      // 🔴 나간 표시는 바로 지우지 않는다 — 떠나는 순간에도 배경 층은 아직
      //    밀려 나가는 중이라, 지우면 아치 글자가 되돌아와 다시 나타난다.
      window.setTimeout(() => {
        if (generation === mine) delete el.dataset.ssScrolled
      }, LEAVE_TAIL_MS)
    }
  }, [])

  return null
}
