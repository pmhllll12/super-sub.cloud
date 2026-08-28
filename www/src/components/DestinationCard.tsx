import Link from 'next/link'
import GlassPanel from './ui/GlassPanel'

// 준비 안 된 카드는 앱처럼 눌러야 알 수 있게 두지 않는다 — 카드 안에 바로 표시한다.
const MUTED = 'color-mix(in srgb, var(--ss-fg) 60%, transparent)'
const FAINT = 'color-mix(in srgb, var(--ss-fg) 40%, transparent)'

// 카드 6장이 공유하는 값 — 카드마다 다르게 주지 않는다. 높이는
// `globals.css` 의 `--ss-card-h` (아이콘+제목+설명 2줄+안내문 1줄이 여유
// 있게 들어가는 값, 앱의 mainAxisExtent: 148 과 같은 이유로 못박음).
const PANEL_CLASS =
  'flex flex-col items-center justify-center gap-2 px-4 py-6 text-center h-[var(--ss-card-h)]'

export default function DestinationCard({
  title,
  icon,
  href,
  summary,
  className = '',
  phase = 0,
  locked = false,
}: {
  title: string
  icon: string
  href?: string
  /** 앱 home_screen.dart 의 두 줄 설명. `\n` 으로 줄바꿈을 나타낸다. */
  summary?: string
  className?: string
  /** GlassPanel 테두리를 도는 빛의 시작 위상(0~1) — 여러 카드가 한꺼번에 반짝이지 않게 어긋낸다. */
  phase?: number
  /** 갈 곳은 있지만(href) 로그인이 안 돼 있어 그 경로가 결국 /login 으로
   *  돌려보낼 카드. 링크는 그대로 두고 안내문만 "준비 중입니다" 자리에
   *  "로그인이 필요합니다"로 바꿔 보여준다. */
  locked?: boolean
}) {
  const ready = Boolean(href)
  // 준비 중/로그인 필요 안내문 — 항상 같은 자리(같은 높이)를 차지해야
  // 카드마다 아이콘·제목·설명 세로 위치가 어긋나지 않는다. 보여줄 문구가
  // 없는(로그인 없이 바로 쓸 수 있는) 카드도 자리만 남기고 visibility 로
  // 숨긴다 — display:none 은 자리를 아예 없애 버려 정렬이 다시 어긋난다.
  const notice = !ready ? '준비 중입니다' : locked ? '로그인이 필요합니다' : null

  const inner = (
    <GlassPanel phase={phase} interactive className={`${PANEL_CLASS} ${className}`}>
      <span
        aria-hidden="true"
        className="material-symbols-outlined text-3xl"
        style={{ color: ready ? 'var(--ss-accent)' : FAINT }}
      >
        {icon}
      </span>
      <span className="text-sm font-medium tracking-normal" style={{ color: ready ? 'var(--ss-fg)' : MUTED }}>
        {title}
      </span>
      {summary && (
        <span className="whitespace-pre-line text-xs leading-snug tracking-normal" style={{ color: MUTED }}>
          {summary}
        </span>
      )}
      <span
        className="text-xs tracking-normal"
        style={{ color: FAINT, visibility: notice ? 'visible' : 'hidden' }}
        aria-hidden={notice ? undefined : true}
      >
        {notice ?? ' '}
      </span>
    </GlassPanel>
  )

  if (href) {
    return (
      <Link href={href} className="block">
        {inner}
      </Link>
    )
  }

  return <div>{inner}</div>
}
