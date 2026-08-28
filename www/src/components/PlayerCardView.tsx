import type { PublicPlayerCard } from '@/server/backend'

/**
 * 수치를 그리지 않는다 (계약서 4절 / 부록 D.5).
 * 점수·등급·별점·진행률 바를 여기에 넣지 않는다.
 * titles 는 받은 것만 온다 — 미달 표식을 만들지 않는다.
 */
export default function PlayerCardView({ card }: { card: PublicPlayerCard }) {
  return (
    <article className="rounded-2xl border p-8">
      <h1 className="text-3xl font-bold">{card.user.nickname}</h1>

      <h2 className="mt-8 text-sm font-semibold text-neutral-500">호칭</h2>
      {card.titles.length === 0 ? (
        <p className="mt-2 text-sm text-neutral-500">아직 받은 호칭이 없습니다.</p>
      ) : (
        <ul className="mt-3 flex flex-wrap gap-2">
          {card.titles.map((t) => (
            <li key={t.code} className="rounded-full border px-3 py-1.5 text-sm">
              <span className="mr-1.5 text-xs text-neutral-400">{t.category}</span>
              {t.label}
            </li>
          ))}
        </ul>
      )}
    </article>
  )
}
