'use client'

import { useEffect, useRef } from 'react'

/**
 * **판이 화면 아래로 넘치지 않게** 키를 재서 `--ss-fit-h` 에 담는다.
 *
 * 🔴 **왜 필요한가** (2026-09-17, 실측). 홈의 두 판(「팀원」 `.ss-teams` ·
 * 「팀장」 `.ss-tm`)은 스쿼드 판 상자(`.ss-squad-wrap`)에 `inset: 0` 으로
 * 매달려 있고, 그 상자는 **경기장 판 높이라 어느 창에서나 702px 고정**이다.
 * 헤드라인 아래에 매달려 있어서 **창이 낮을수록 아래가 화면 밖으로 나간다** —
 * 헤드리스 크롬 실측: 맥북 14"(1512×857)는 9px, PC 1366×768 은 72px,
 * 1280×720 은 108px, 1024×768 은 117px.
 *
 * 🔴 **그리고 그건 스크롤로 되찾을 수 없다.** `body` 의 `overflow-x: clip` 이
 * **세로까지 `clip` 으로 만든다**(CSS 규칙 — 한 축이 `clip` 이면 다른 축의
 * `visible` 도 `clip` 이 된다). 그래서 넘친 부분은 **잘린다.** `clip` 을 모르는
 * 브라우저에서는 반대로 **페이지가 통째로 내려간다** — 사용자들이 「PC 에서는
 * 스크롤하면 내려간다」고 말한 것이 이것으로 보인다. 증상이 갈릴 뿐 뿌리는
 * 하나다: **판이 화면에 안 맞는다.**
 *
 * 그래서 판을 화면 아래 끝에서 멈추게 하고, 넘치는 내용은 **판 안에서**
 * 구르게 한다(`.ss-teams-list`·`.ss-prefs` 가 이미 `overflow-y: auto` 다).
 * 경기장 판 크기는 건드리지 않는다(사용자 판단).
 *
 * 🔴 **자기 자신이 아니라 부모 상자를 잰다.** 판은 열리고 닫히는 연출 중에
 * 옮겨질 수 있어서 그때 잰 `top` 은 제자리가 아니다. 부모(`.ss-squad-wrap`)는
 * 안 움직인다.
 *
 * ⚠️ **CSS 만으로는 못 한다.** 판의 화면 위 자리는 「가운데 정렬된 헤드라인
 * 아래」라 창 높이에 따라 달라지는데(실측 125 · 164 · 248px), 그 값을 CSS 가
 * 읽을 방법이 없다. `100svh` 에서 빼려면 그 자리를 알아야 한다.
 */
export function useFitToViewport<T extends HTMLElement>(
  /** 화면 아래 끝에 남길 여백. */
  bottomGap = 16,
  /** 이보다는 안 줄인다 — 더 줄면 판이 읽을 수 없게 된다. */
  min = 260,
) {
  const ref = useRef<T>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const box = el.parentElement ?? el

    function fit() {
      if (!el) return
      const top = box.getBoundingClientRect().top
      const room = Math.round(window.innerHeight - top - bottomGap)
      /* 넉넉하면 아무것도 안 건다 — `none` 이면 판은 지금처럼 제 키로 선다.
         (맥북처럼 이미 들어가는 창에서 괜히 값을 박지 않는다.) */
      el.style.setProperty('--ss-fit-h', room >= box.offsetHeight ? 'none' : `${Math.max(min, room)}px`)
    }

    fit()
    window.addEventListener('resize', fit)

    /* 위 글자가 줄바꿈되거나 글꼴이 늦게 붙어 자리가 밀리면 다시 잰다.
       🔴 **없을 수도 있다고 보고 쓴다** — jsdom 에 없고, 이 문제를 겪는다고
       알려진 **오래된 브라우저**에도 없을 수 있다. 없으면 창 크기 바뀔 때만
       다시 재고, 그것만으로도 판은 화면 안에 선다. */
    const ro = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(fit)
    ro?.observe(box)
    ro?.observe(document.documentElement)
    return () => {
      window.removeEventListener('resize', fit)
      ro?.disconnect()
    }
  }, [bottomGap, min])

  return ref
}
