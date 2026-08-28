import Link from 'next/link'
import GlassPanel from './ui/GlassPanel'

// 준비 안 된 카드는 앱처럼 눌러야 알 수 있게 두지 않는다 — 카드 안에 바로 표시한다.
const MUTED = 'color-mix(in srgb, var(--ss-fg) 60%, transparent)'
const FAINT = 'color-mix(in srgb, var(--ss-fg) 40%, transparent)'

export default function DestinationCard({
  title,
  icon,
  href,
  summary,
  className = '',
  phase = 0,
}: {
  title: string
  icon: string
  href?: string
  /** 앱 home_screen.dart 의 두 줄 설명. `\n` 으로 줄바꿈을 나타낸다. */
  summary?: string
  className?: string
  /** GlassPanel 테두리를 도는 빛의 시작 위상(0~1) — 여러 카드가 한꺼번에 반짝이지 않게 어긋낸다. */
  phase?: number
}) {
  const ready = Boolean(href)

  const inner = (
    <GlassPanel
      phase={phase}
      className={`flex h-full flex-col items-center justify-center gap-2 px-4 py-6 text-center ${className}`}
    >
      <span
        aria-hidden="true"
        className="material-symbols-outlined text-3xl"
        style={{ color: ready ? 'var(--ss-accent)' : FAINT }}
      >
        {icon}
      </span>
      <span className="text-sm font-medium" style={{ color: ready ? 'var(--ss-fg)' : MUTED }}>
        {title}
      </span>
      {summary && (
        <span className="whitespace-pre-line text-xs leading-snug" style={{ color: MUTED }}>
          {summary}
        </span>
      )}
      {!ready && (
        <span className="text-xs" style={{ color: FAINT }}>
          준비 중입니다
        </span>
      )}
    </GlassPanel>
  )

  if (href) {
    return (
      <Link href={href} className="block h-full">
        {inner}
      </Link>
    )
  }

  return <div className="h-full">{inner}</div>
}
