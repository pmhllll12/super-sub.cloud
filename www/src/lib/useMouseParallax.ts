'use client'

import { useEffect, useRef, type RefObject } from 'react'

export type ParallaxLayer = {
  ref: RefObject<HTMLElement | null>
  /** 마우스가 화면 이 끝에서 저 끝까지(정규화 좌표 -1~1) 움직일 때 이 층이 움직이는 최대 거리(px). */
  strength: number
}

/**
 * 목표 좌표를 향해 프레임마다 이만큼씩 좁혀간다(선형 보간 계수). 클수록
 * 마우스를 즉시 따라가 뚝뚝 끊겨 보이고, 작을수록 굼떠 보인다. 0.08 은
 * 사람 눈에 "서서히 따라온다"로 읽히면서도 반응이 굼뜨다는 느낌은 없는
 * 지점으로 실측해 골랐다(약 0.5초 안에 목표에 거의 도달한다).
 */
const EASE = 0.08

/**
 * 배경 사진 · 워드마크 · 카드처럼 여러 층을 서로 다른 배율로 마우스에
 * 반응시켜 시차(패럴랙스)를 낸다.
 *
 * - `prefers-reduced-motion: reduce` 이거나 정밀 포인터(마우스)가 없는
 *   기기(`pointer: fine` 이 아님 — 터치 등)에서는 아무 것도 하지 않는다.
 *   리스너도 rAF 도 시작하지 않는다.
 * - `mousemove` 핸들러는 목표 좌표만 기록한다. 실제 스타일 반영은
 *   `requestAnimationFrame` 루프에서 한 번에 한다 — 이벤트마다 스타일을
 *   쓰면 프레임이 떨어진다.
 * - 리액트 상태를 거치지 않고 `ref.current.style.transform` 을 직접 쓴다 —
 *   프레임마다 리렌더가 일어나면 그것대로 비용이다. `transform` 만
 *   바꾸므로 레이아웃 재계산은 없다.
 * - 마우스가 창을 벗어나면 목표를 가운데(0,0)로 되돌려 살짝 제자리로
 *   돌아오게 한다.
 */
export function useMouseParallax(layers: ParallaxLayer[]) {
  const layersRef = useRef(layers)

  // 매 렌더 이후(렌더 도중이 아니라)에 최신 layers 로 갱신한다 — 렌더 중에
  // ref.current 를 쓰면 안 된다는 React 규칙 때문에 별도 effect 로 뺐다.
  // 아래 rAF 루프는 layersRef.current 를 프레임마다 새로 읽으므로 이 effect
  // 가 언제 커밋되든(마운트 시 다른 effect 와의 순서와 무관하게) 다음 프레임엔
  // 항상 최신 값을 본다.
  useEffect(() => {
    layersRef.current = layers
  })

  useEffect(() => {
    let reduced = false
    let finePointer = false
    try {
      reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      finePointer = window.matchMedia('(pointer: fine)').matches
    } catch {
      return
    }
    if (reduced || !finePointer) return

    let targetX = 0
    let targetY = 0
    let currentX = 0
    let currentY = 0
    let rafId = 0

    const handleMove = (e: MouseEvent) => {
      targetX = (e.clientX / window.innerWidth - 0.5) * 2
      targetY = (e.clientY / window.innerHeight - 0.5) * 2
    }

    const handleLeave = () => {
      targetX = 0
      targetY = 0
    }

    const tick = () => {
      currentX += (targetX - currentX) * EASE
      currentY += (targetY - currentY) * EASE

      for (const layer of layersRef.current) {
        const el = layer.ref.current
        if (!el) continue
        const dx = currentX * layer.strength
        const dy = currentY * layer.strength
        el.style.transform = `translate3d(${dx.toFixed(2)}px, ${dy.toFixed(2)}px, 0)`
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
  }, [])
}
