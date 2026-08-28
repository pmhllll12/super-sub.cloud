'use client'

import { useEffect, type RefObject } from 'react'

/**
 * 마우스의 화면 좌우 위치에 따라 가로 스크롤 컨테이너가 흐르게 한다
 * (드래그가 아니라 커서 위치 기반). 화면 가운데 근처({@link DEADZONE})에서는
 * 멈추고, 가장자리로 갈수록 최대 속도({@link MAX_SPEED})까지 빨라진다.
 * 커서 좌표를 그대로 위치에 꽂지 않고 목표 "속도"를 매 프레임 서서히
 * 따라가게({@link EASE}) 해서 마우스가 홱 움직여도 뚝뚝 끊기지 않는다
 * (`useMouseParallax` 가 목표 "위치"를 EASE 로 따라가는 것과 같은 원리를
 * 속도에 적용한 것).
 *
 * 카드는 6장 한 벌뿐이다(무한 루프 없음) — 양 끝(첫 카드 앞 · 마지막 카드
 * 뒤)에서 멈춘다. 경계에 딱 닿아 덜컥 멈추지 않도록, 경계까지 남은
 * 거리가 {@link EDGE_SOFT_ZONE} 안으로 들어오면 속도를 그 거리에 비례해
 * 줄인다 — 자연히 감속하며 선다.
 *
 * `el.scrollLeft` 를 직접 쓰고 `transform` 은 안 쓴다 — 이 컨테이너에는
 * `useMouseParallax` 가 이미 시차용으로 `transform` 을 쓰고 있어서, 같은
 * 속성을 여기서 또 쓰면 둘 중 하나가 다른 하나를 덮어써 버린다.
 * `scrollLeft` 는 `transform` 과 완전히 다른 값이라 시차와 부딪히지 않고
 * 자연스럽게 합성된다(박스 자체는 시차로 살짝 흔들리고, 그 안의 스크롤
 * 위치는 이 훅이 따로 흐르게 한다).
 */
const DEADZONE = 0.15
/** 화면 가장자리에서의 최고 속도(px/frame, 60fps 기준 초당 약 500px). */
const MAX_SPEED = 8.5
const EASE = 0.06
/** 스크롤 양 끝에서 이만큼(px) 안으로 들어오면 속도를 남은 거리에 비례해
 *  줄인다 — 경계에 부딪혀 뚝 멈추지 않고 서서히 선다. */
const EDGE_SOFT_ZONE = 80

export function useCarouselFlow(containerRef: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const el = containerRef.current
    if (!el) return

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
    // 손 스크롤 · 스와이프로 볼 수 있다.
    if (reduced || !finePointer) return

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

      const maxScroll = el.scrollWidth - el.clientWidth
      let v = velocity
      if (v > 0) {
        const remaining = maxScroll - el.scrollLeft
        if (remaining < EDGE_SOFT_ZONE) v *= Math.max(0, remaining / EDGE_SOFT_ZONE)
      } else if (v < 0) {
        const remaining = el.scrollLeft
        if (remaining < EDGE_SOFT_ZONE) v *= Math.max(0, remaining / EDGE_SOFT_ZONE)
      }
      if (Math.abs(v) > 0.01) {
        el.scrollLeft = Math.min(maxScroll, Math.max(0, el.scrollLeft + v))
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
    }
  }, [containerRef])
}
