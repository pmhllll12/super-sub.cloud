'use client'

import { useEffect, useRef } from 'react'

/**
 * 자식을 **첫 화면 안에 반드시 앉힌다.**
 *
 * 🔴 이게 왜 CSS 가 아니라 JS 인지 — 첫 화면에 남는 높이는
 * `100svh − (위에 있는 것들의 높이)` 인데, 그 "위에 있는 것들" 중 하나가
 * `SiteHeader` 이고 **그 높이가 고정이 아니다.** `(app)/layout.tsx` 주석이
 * 이미 적어 둔 사실이다 — 선수 카드가 있는 사용자와 없는 사용자의 헤더
 * 높이가 다르다. 그래서 `calc(100svh - 150px)` 같은 상수는 내 창에서만
 * 맞고 남의 창에서 잘린다(실제로 두 번 잘렸다).
 *
 * 재는 것은 두 가지다.
 *  ① `--ss-hero-h` — 이 자리에서 화면 바닥까지 실제로 남은 높이.
 *  ② `--ss-fit`    — 글 덩어리가 그 높이보다 크면 얼마나 줄여야 하는지.
 *
 * ②를 `font-size` 가 아니라 `transform: scale` 로 주는 이유: 글자 크기를
 * 줄이면 줄바꿈이 다시 일어나 높이가 예측대로 안 줄어든다(줄 수가 어떻게
 * 바뀔지 모르므로 한 번 재서는 못 맞추고 되풀이해야 한다). 배율은 기하학이라
 * **한 번 재면 정확히 맞는다.**
 *
 * 배율은 배치 크기를 바꾸지 않으므로(transform 은 그리는 크기만 바꾼다)
 * ResizeObserver 가 자기가 방금 준 변화를 다시 재는 되먹임이 생기지 않는다.
 */
export default function HeroFit({
  className,
  children,
  /** 화면 바닥에 남길 여백. */
  bottom = 16,
}: {
  className?: string
  children: React.ReactNode
  bottom?: number
}) {
  const hostRef = useRef<HTMLElement>(null)
  const innerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const host = hostRef.current
    const inner = innerRef.current
    if (!host || !inner) return

    // 🔴 값이 같으면 **쓰지 않는다.** ResizeObserver 안에서 layout 을 건드리는
    //    글을 매번 쓰면 "ResizeObserver loop" 경고가 뜬다.
    const set = (k: string, v: string) => {
      if (host.style.getPropertyValue(k) !== v) host.style.setProperty(k, v)
    }

    const fit = () => {
      // 🔴 문서 기준 위치로 잰다. 화면 기준(rect.top)만 쓰면 스크롤을 내린
      //    상태에서 재게 됐을 때 남은 높이가 엉뚱하게 나온다.
      // 🔴 **두 숫자는 다르다.** 한 번 섞어 써서 글이 아래가 아니라 위로
      //    올라가 아치와 더 겹쳤다.
      //      ① 칸 높이  = 이 자리에서 **화면 바닥까지**. 아래 여백을 여기서
      //                   빼면 안 된다 — 칸이 짧아진 만큼 **다음 판이 첫
      //                   화면에 걸쳐** 스크롤하기도 전에 보인다(실제로 그랬다).
      //      ② 쓸 높이  = 비켜야 할 것 아래부터 여백 위까지 — 얼마나
      //                   **줄여야** 하는지를 정한다.
      //    아래 여백은 칸을 줄이는 것이 아니라 **칸 안에서** 준다(--ss-hero-pad).
      const flowTop = host.getBoundingClientRect().top + window.scrollY
      const floor = window.innerHeight - bottom

      set('--ss-hero-h', `${Math.max(240, window.innerHeight - flowTop)}px`)
      set('--ss-hero-pad', `${bottom}px`)

      // offsetHeight 는 배율을 타지 않는다 — 늘 "줄이기 전" 높이다.
      const natural = inner.offsetHeight
      if (natural <= 0) {
        set('--ss-fit', '1')
        return
      }

      // 🔴 줄이는 것은 **칸 밖으로 나갈 때뿐**이다. 한때는 배경의 아치 글자도
      //    비켜 주려고 늘 조금씩 줄여 뒀는데, 첫 그림은 배율 1 로 나갔다가 재고
      //    나서 작아지는 바람에 **커졌다가 툭 앉는 것**으로 보였다(사용자 지적).
      //    아치는 내리기 시작하면 알아서 비켜 주므로(globals.css) 여기서 피할
      //    일이 없다 — 들어맞는 보통의 경우 배율은 1 이고, 아무것도 안 움직인다.
      set('--ss-fit', `${Math.min(1, (floor - flowTop) / natural)}`)
    }

    fit()
    // 🔴 화면 들어오는 연출(PageEnter)이 자리를 잠깐 옮겨 놓은 채로 재면
    //    남은 높이가 그만큼 틀린다 — 가라앉은 뒤 한 번 더 잰다.
    const settle = window.setTimeout(fit, 1000)
    window.addEventListener('resize', fit)

    // 글꼴이 늦게 오면 줄 수가 바뀐다 — 그때 다시 잰다.
    document.fonts?.ready.then(fit).catch(() => {})

    let ro: ResizeObserver | undefined
    if (typeof ResizeObserver !== 'undefined') {
      ro = new ResizeObserver(fit)
      ro.observe(inner)
    }

    return () => {
      window.clearTimeout(settle)
      window.removeEventListener('resize', fit)
      ro?.disconnect()
    }
  }, [bottom])

  return (
    <header ref={hostRef} className={className}>
      <div ref={innerRef} className="ss-hero-fit">
        {children}
      </div>
    </header>
  )
}
