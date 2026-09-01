import { TransitionLink } from '@/lib/pageTransition'
import GlassPanel from './ui/GlassPanel'

const MUTED = 'color-mix(in srgb, var(--ss-fg) 60%, transparent)'
const FAINT = 'color-mix(in srgb, var(--ss-fg) 40%, transparent)'

// 카드 6장이 공유하는 값 — 카드마다 다르게 주지 않는다. 높이는
// `globals.css` 의 `--ss-card-h` (아이콘+제목+설명 2줄+안내문 1줄이 여유
// 있게 들어가는 값, 앱의 mainAxisExtent: 148 과 같은 이유로 못박음). 폭은
// `--ss-card-w` — 카드 스스로 정한다(놓이는 자리의 폭에 기대지 않는다).
const PANEL_CLASS =
  'flex flex-col items-center justify-center gap-2 px-4 py-6 text-center h-[var(--ss-card-h)] w-[var(--ss-card-w)]'

// 홈 상단 글자 nav 에서 글자 아래 떠오르는 작은 판. 같은 내용을 같은 순서로
// 그리되 크기만 줄인다 — 별도 컴포넌트를 만들면 두 벌이 따로 늙는다.
// 뜨는 자리가 좁으므로 높이를 내용에 맡긴다(고정 높이를 주지 않는다).
// 글자 줄 아래로 떠오르는 작은 판. **제목을 그리지 않는다** — 바로 위 글자에
// 이미 같은 말이 적혀 있어 두 번 읽힌다(사용자 요청). 그만큼 판도 작아졌다.
//
// 🔴 키를 못박는다. 셋이 나란히 서는 것은 아니지만 **번갈아 뜨는 자리라**
// 크기가 다르면 글자를 옮길 때마다 판이 커졌다 작아졌다 한다.
const COMPACT_PANEL_CLASS =
  'flex flex-col items-center justify-center gap-1.5 px-3 py-3 text-center w-[var(--ss-card-compact-w)] h-[var(--ss-card-compact-h)]'

// 알약 버튼(`HomeNav` variant="pill") 위로 떠오르는 것 — **판이 없다.**
// 유리판도 아이콘도 제목도 안내문도 없이 설명 글자만 뜬다(사용자 요청).
// 제목은 바로 아래 알약에 이미 적혀 있고, 판을 두면 그 아래 스쿼드 판과
// 유리가 두 겹으로 겹쳐 둘 다 탁해진다.
const BARE_CLASS = 'ss-nav-bare block whitespace-pre-line text-center'

export default function DestinationCard({
  title,
  icon,
  href,
  summary,
  className = '',
  phase = 0,
  locked = false,
  compact = false,
  bare = false,
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
   *  돌려보낼 카드. 링크는 그대로 두고 "로그인이 필요합니다"만 덧붙인다. */
  locked?: boolean
  /** 홈 글자 nav 에서 떠오르는 작은 판 — 같은 내용, 줄어든 크기. */
  compact?: boolean
  /**
   * 판 없이 **설명 글자만** 그린다(알약 버튼 위로 뜨는 것).
   * 유리판 · 아이콘 · 제목 · 안내문이 전부 빠진다 — 제목이 바로 아래
   * 버튼에 이미 적혀 있고, 판을 두면 스쿼드 판과 유리가 겹쳐 탁해진다.
   */
  bare?: boolean
}) {
  const ready = Boolean(href)
  // 🔴 **'준비 중입니다' 는 그리지 않는다**(사용자 요청). 갈 곳이 없는 카드는
  // 애초에 링크가 아니라(아래 href 분기) 눌러도 아무 일이 없고, 그 줄 하나
  // 때문에 판이 한 뼘 길어졌다. 개발 진행 상태는 화면이 할 말이 아니다.
  //
  // 로그인 안내만 남긴다 — 이건 **사용자가 할 일**을 알려 주는 말이라 다르다.
  // 자리도 그때만 차지한다: 카드 키가 못박혀 있어(--ss-card-compact-h)
  // 빈 줄로 자리를 지켜 줄 필요가 없다.
  const notice = locked ? '로그인이 필요합니다' : null

  const inner = bare ? (
    <span className={`${BARE_CLASS} ${className}`}>{summary}</span>
  ) : (
    <GlassPanel
      phase={phase}
      interactive
      className={`${compact ? COMPACT_PANEL_CLASS : PANEL_CLASS} ${className}`}
    >
      {/* 🔴 아이콘은 **셋 다 완전한 흰색**이다(사용자 요청). 한때 갈 수 있는
          곳만 강조색이고 준비 중인 곳은 흐렸는데, 그러면 아이콘이 "이건 아직
          안 된다"는 표식이 되어 버린다 — 그 말은 아래 안내문이 이미 한다.
          굵기 · 광학 크기는 `.ss-dest-icon` 이 정한다(globals.css). */}
      <span
        aria-hidden="true"
        className={`material-symbols-outlined ss-dest-icon ${compact ? 'text-2xl' : 'text-3xl'}`}
      >
        {icon}
      </span>
      {/* 제목은 큰 카드에만 있다. 작은 판은 글자 줄 바로 아래에 뜨므로
          같은 말이 두 줄로 겹쳐 읽힌다. */}
      {!compact && (
        <span
          className="text-sm font-medium tracking-normal"
          style={{ color: 'var(--ss-fg)' }}
        >
          {title}
        </span>
      )}
      {/* 🔴 **완전한 흰색이다**(사용자 요청). 60% 로 두면 배경 사진의 밝은
          연기 위에서 묻힌다 — 판이 유리라 뒤가 그대로 비친다. 위계는 색이
          아니라 크기로 낸다. */}
      {summary && (
        <span
          className="whitespace-pre-line text-xs leading-snug tracking-normal"
          style={{ color: 'var(--ss-fg)' }}
        >
          {summary}
        </span>
      )}
      {/* 안내문은 늘 같은 자리를 차지해야 카드끼리 세로 위치가 안 어긋난다 —
          보여줄 게 없어도 visibility 로만 숨긴다(display:none 은 자리를 아예
          없애 정렬이 다시 어긋난다). */}
      {notice && (
        <span className="text-xs tracking-normal" style={{ color: FAINT }}>
          {notice}
        </span>
      )}
    </GlassPanel>
  )

  if (href) {
    return (
      <TransitionLink href={href} className="block">
        {inner}
      </TransitionLink>
    )
  }

  return <div>{inner}</div>
}
