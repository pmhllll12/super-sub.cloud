import type { PublicPlayerCard } from '@/server/backend'
import GlassPanel from './ui/GlassPanel'

const MUTED = 'color-mix(in srgb, var(--ss-fg) 60%, transparent)'
const FAINT = 'color-mix(in srgb, var(--ss-fg) 40%, transparent)'

/**
 * 수치를 그리지 않는다 (계약서 4절 / 부록 D.5).
 * 점수·등급·별점·진행률 바를 여기에 넣지 않는다.
 * titles 는 받은 것만 온다 — 미달 표식을 만들지 않는다.
 */
export default function PlayerCardView({ card }: { card: PublicPlayerCard }) {
  return (
    <article
      className="relative mx-auto w-full max-w-md overflow-hidden"
      style={{ borderRadius: 'var(--ss-radius-sheet)' }}
    >
      <div
        aria-hidden="true"
        className="absolute inset-0 -z-10 bg-cover bg-center opacity-20"
        style={{ backgroundImage: "url('/player_mono.jpg')" }}
      />
      <GlassPanel className="flex flex-col gap-8 px-8 py-10">
        <h1 className="text-3xl font-bold">{card.user.nickname}</h1>

        <div>
          <h2 className="text-sm font-semibold" style={{ color: MUTED }}>
            호칭
          </h2>
          {card.titles.length === 0 ? (
            <p className="mt-2 text-sm" style={{ color: MUTED }}>
              아직 받은 호칭이 없습니다.
            </p>
          ) : (
            <ul className="mt-3 flex flex-wrap gap-2">
              {card.titles.map((t) => (
                <li
                  key={t.code}
                  className="rounded-full px-3 py-1.5 text-sm"
                  style={{ border: '1px solid var(--ss-glass-border)' }}
                >
                  <span className="mr-1.5 text-xs" style={{ color: FAINT }}>
                    {t.category}
                  </span>
                  <span style={{ color: 'var(--ss-accent)' }}>{t.label}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </GlassPanel>
    </article>
  )
}
