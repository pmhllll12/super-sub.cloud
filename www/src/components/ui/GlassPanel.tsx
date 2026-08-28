import type { CSSProperties } from 'react'

/**
 * `flutter/lib/core/widgets/glass_panel.dart` 의 `_TravelingEdge` — 카드 둘레를
 * 도는 얇은 흰 빛. `.ss-traveling-edge`(전역 CSS, `globals.css`)가 실제 그리는
 * 일을 한다: 늘 켜진 10% 밑선 위에 conic-gradient 로 좁고 밝은 점 하나가 각도로
 * 돈다. `phase` 는 카드마다 시작 각도를 어긋내는 값(0~1) — 앱의
 * `phase: i * 0.13` 과 같다. 한꺼번에 반짝이지 않게 하려는 용도라 값 자체는
 * 임의로 아무 카드나 달라도 된다.
 */
export default function GlassPanel({
  className = '',
  phase = 0,
  children,
}: {
  className?: string
  /** 도는 빛의 시작 위상(0~1). 같은 화면에 카드가 여럿이면 다르게 준다. */
  phase?: number
  children: React.ReactNode
}) {
  return (
    <div
      className={`ss-traveling-edge relative overflow-hidden ${className}`}
      style={
        {
          borderRadius: 'var(--ss-radius-sheet)',
          background: 'var(--ss-glass-bg)',
          border: '1px solid var(--ss-glass-border)',
          backdropFilter: 'blur(var(--ss-glass-blur))',
          WebkitBackdropFilter: 'blur(var(--ss-glass-blur))',
          '--ss-edge-phase': phase,
        } as CSSProperties
      }
    >
      {children}
    </div>
  )
}
