'use client'

import { useEffect, type RefObject } from 'react'

/**
 * 마우스의 화면 좌우 위치에 따라 가로 스크롤 컨테이너가 계속 흐르게 한다
 * (드래그가 아니라 커서 위치 기반). 화면 가운데 근처({@link DEADZONE})에서는
 * 멈추고, 가장자리로 갈수록 최대 속도({@link MAX_SPEED})까지 빨라진다.
 * 커서 좌표를 그대로 위치에 꽂지 않고 목표 "속도"를 매 프레임 서서히
 * 따라가게({@link EASE}) 해서 마우스가 홱 움직여도 뚝뚝 끊기지 않는다
 * (`useMouseParallax` 가 목표 "위치"를 EASE 로 따라가는 것과 같은 원리를
 * 속도에 적용한 것).
 *
 * `el.scrollLeft` 를 직접 쓰고 `transform` 은 안 쓴다 — 이 컨테이너에는
 * `useMouseParallax` 가 이미 시차용으로 `transform` 을 쓰고 있어서, 같은
 * 속성을 여기서 또 쓰면 둘 중 하나가 다른 하나를 덮어써 버린다.
 * `scrollLeft` 는 `transform` 과 완전히 다른 값이라 시차와 부딪히지 않고
 * 자연스럽게 합성된다(박스 자체는 시차로 살짝 흔들리고, 그 안의 스크롤
 * 위치는 이 훅이 따로 흐르게 한다).
 *
 * 무한 루프: `destinations.map(...)` 을 `loopCopies` 벌 이어붙였다고
 * 가정하고(가운데 벌에서 시작), `scrollLeft` 가 양쪽 끝 벌 하나를
 * 넘어가면 티 안 나게 한 벌 폭만큼 되돌린다. 이 되돌림은 자동 흐름과
 * 별개로 `scroll` 이벤트에서 항상 검사한다 — reduced-motion 이거나
 * 마우스가 없는(pointer: coarse) 기기라 아래 rAF 자동 흐름이 꺼져 있어도,
 * 손으로 스크롤/스와이프할 때 똑같이 끝에서 막히지 않고 돌아야 하기
 * 때문이다.
 */
const DEADZONE = 0.15
/** 화면 가장자리에서의 최고 속도(px/frame, 60fps 기준 초당 약 500px). */
const MAX_SPEED = 8.5
const EASE = 0.06

export function useCarouselFlow(containerRef: RefObject<HTMLElement | null>, loopCopies: number) {
  useEffect(() => {
    const el = containerRef.current
    if (!el || loopCopies < 1) return

    let setWidth = 0
    const measure = () => {
      setWidth = el.scrollWidth / loopCopies
    }
    measure()
    // 테스트(jsdom)엔 ResizeObserver 가 없다 — 없으면 그냥 처음 한 번만
    // 잰다(레이아웃이 안 바뀌는 환경이니 문제 없다). 실제 브라우저는 전부
    // 지원한다.
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(measure) : null
    ro?.observe(el)

    const wrap = () => {
      if (setWidth <= 0) return
      if (el.scrollLeft >= setWidth * (loopCopies - 1)) {
        el.scrollLeft -= setWidth
      } else if (el.scrollLeft <= 0) {
        el.scrollLeft += setWidth
      }
    }
    el.addEventListener('scroll', wrap, { passive: true })

    // 시작 위치 — 가운데 벌. 앞뒤로 최소 한 벌씩 버퍼가 있어야 양쪽
    // 방향 모두 진짜 스크롤 경계(clamp)에 안 닿고 계속 흐를 수 있다.
    el.scrollLeft = setWidth * Math.floor(loopCopies / 2)

    let reduced = false
    let finePointer = false
    try {
      reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      finePointer = window.matchMedia('(pointer: fine)').matches
    } catch {
      reduced = true
    }

    // reduced-motion 이거나 정밀 포인터가 없으면 자동 흐름은 켜지 않는다
    // — 컨테이너는 그냥 보통의 가로 스크롤(overflow-x: auto)로 남아
    // 손 스크롤 · 스와이프로 볼 수 있고, 위 wrap() 이 그 스크롤에도 계속
    // 반응해 끝에서 막히지 않는다.
    if (reduced || !finePointer) {
      return () => {
        el.removeEventListener('scroll', wrap)
        ro?.disconnect()
      }
    }

    let targetNX = 0
    let velocity = 0
    let rafId = 0

    const handleMove = (e: MouseEvent) => {
      const nx = (e.clientX / window.innerWidth - 0.5) * 2 // -1(왼쪽 끝) ~ 1(오른쪽 끝)
      targetNX = Math.abs(nx) < DEADZONE ? 0 : nx
    }
    const handleLeave = () => {
      targetNX = 0
    }

    const tick = () => {
      // 마우스가 오른쪽(nx>0)이면 scrollLeft 증가(카드가 왼쪽으로 흐름),
      // 왼쪽(nx<0)이면 scrollLeft 감소(카드가 오른쪽으로 흐름) — 부호를
      // 그대로 속도에 옮기면 요구한 방향과 맞는다.
      const targetVelocity = targetNX * MAX_SPEED
      velocity += (targetVelocity - velocity) * EASE
      if (Math.abs(velocity) > 0.01) {
        el.scrollLeft += velocity
      }
      rafId = requestAnimationFrame(tick)
    }

    window.addEventListener('mousemove', handleMove)
    document.addEventListener('mouseleave', handleLeave)
    rafId = requestAnimationFrame(tick)

    return () => {
      cancelAnimationFrame(rafId)
      window.removeEventListener('mousemove', handleMove)
      document.removeEventListener('mouseleave', handleLeave)
      el.removeEventListener('scroll', wrap)
      ro?.disconnect()
    }
  }, [containerRef, loopCopies])
}
