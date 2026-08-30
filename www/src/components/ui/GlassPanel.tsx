'use client'

import { useEffect, useRef, type CSSProperties, type MouseEvent as ReactMouseEvent } from 'react'

/**
 * `flutter/lib/core/widgets/glass_panel.dart` 의 `_TravelingEdge` — 카드 둘레를
 * 도는 얇은 흰 빛. `.ss-traveling-edge`(전역 CSS, `globals.css`)가 실제 그리는
 * 일을 한다: 늘 켜진 10% 밑선 위에 conic-gradient 로 좁고 밝은 점 하나가 각도로
 * 돈다. `phase` 는 카드마다 시작 각도를 어긋내는 값(0~1) — 앱의
 * `phase: i * 0.13` 과 같다. 한꺼번에 반짝이지 않게 하려는 용도라 값 자체는
 * 임의로 아무 카드나 달라도 된다.
 *
 * 테두리는 이 컴포넌트가 CSS `border` 로 한 번 더 긋지 않는다 — `border` 를
 * 같이 쓰면 `::after` 의 컨테이닝 블록(패딩 엣지)이 그 border 두께만큼
 * 안쪽으로 밀려, overflow-hidden 클리핑과 겹쳐 "돌아가는 빛이 진짜 바깥
 * 테두리보다 안쪽에서 따로 도는" 두 겹 테두리로 보인다(같은 문제를
 * `components/auth/AuthShell.tsx` 도 겪어서 그쪽은 아예 안쪽 폼 칸에서
 * border 를 빼고 바깥 래퍼 하나에만 준다 — 그 코멘트 참고). `::after` 의
 * 늘 켜진 10% 레이어가 정지 상태의 테두리 역할을 그대로 하므로 실제
 * `border` 없이도 테두리가 사라지지 않는다.
 *
 * `interactive` 가 true 면(홈 화면 목적지 카드) 호버 시 아주 살짝 확대되고
 * 커서를 따라 은은한 후광이 돈다 — 실제 스타일 반영은 전역 CSS 클래스
 * (`.ss-card-interactive`/`.ss-card-glow`)가 하고, 여기서는 mousemove 마다
 * 커서 좌표(`--ss-card-glow-x/y`)만 requestAnimationFrame 으로 묶어 DOM에
 * 직접 쓴다(리액트 상태를 거치면 프레임마다 리렌더가 붙는다 —
 * `prefers-reduced-motion` 을 존중하는 다른 움직임들과 같은 이유). `prefers-reduced-motion: reduce`
 * 면 좌표 갱신 자체를 하지 않는다(CSS 쪽도 이중으로 꺼둔다).
 */
export default function GlassPanel({
  className = '',
  phase = 0,
  interactive = false,
  children,
}: {
  className?: string
  /** 도는 빛의 시작 위상(0~1). 같은 화면에 카드가 여럿이면 다르게 준다. */
  phase?: number
  /** 호버 확대 + 커서를 따라다니는 후광을 켠다. 기본은 꺼짐 — 내비바·프로필
   *  카드 등 기존 화면은 이 prop 을 안 주므로 그대로 정적이다. */
  interactive?: boolean
  children: React.ReactNode
}) {
  const ref = useRef<HTMLDivElement>(null)
  const rafRef = useRef(0)
  const pendingRef = useRef<{ x: number; y: number } | null>(null)
  const reducedMotionRef = useRef(false)

  useEffect(() => {
    if (!interactive) return
    try {
      reducedMotionRef.current = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    } catch {
      reducedMotionRef.current = false
    }
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [interactive])

  const handleMouseMove = interactive
    ? (e: ReactMouseEvent<HTMLDivElement>) => {
        if (reducedMotionRef.current) return
        const el = ref.current
        if (!el) return
        const rect = el.getBoundingClientRect()
        pendingRef.current = { x: e.clientX - rect.left, y: e.clientY - rect.top }
        if (rafRef.current) return
        rafRef.current = requestAnimationFrame(() => {
          rafRef.current = 0
          const p = pendingRef.current
          const target = ref.current
          if (!p || !target) return
          target.style.setProperty('--ss-card-glow-x', `${p.x}px`)
          target.style.setProperty('--ss-card-glow-y', `${p.y}px`)
        })
      }
    : undefined

  return (
    <div
      ref={ref}
      onMouseMove={handleMouseMove}
      className={`ss-traveling-edge relative overflow-hidden ${interactive ? 'ss-card-interactive ss-card-glow' : ''} ${className}`}
      style={
        {
          borderRadius: 'var(--ss-radius-sheet)',
          // 위쪽 아주 옅은 하이라이트(빛이 위에서 드는 느낌) + 유리 바탕색.
          background: 'linear-gradient(to bottom, color-mix(in srgb, var(--ss-fg) 10%, transparent), transparent 40%), var(--ss-glass-bg)',
          backdropFilter: 'blur(var(--ss-glass-blur)) saturate(var(--ss-glass-saturate))',
          WebkitBackdropFilter: 'blur(var(--ss-glass-blur)) saturate(var(--ss-glass-saturate))',
          // 겉은 밝고(::after 의 도는 빛 + 10% 밑선, 진짜 바깥 테두리) 안은 살짝
          // 어둡게(이 inset shadow) — 두 겹으로 두께감을 낸다.
          boxShadow: 'inset 0 0 0 1px color-mix(in srgb, var(--ss-bg) 20%, transparent)',
          '--ss-edge-phase': phase,
        } as CSSProperties
      }
    >
      {children}
    </div>
  )
}
