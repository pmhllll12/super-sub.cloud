import Link from 'next/link'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import PlayerCardView from '@/components/PlayerCardView'
import GlassPanel from '@/components/ui/GlassPanel'
import { BackendError, getBackend, type PlayerCard } from '@/server/backend'
import { SESSION_COOKIE } from '@/server/session'

const MUTED = 'color-mix(in srgb, var(--ss-fg) 60%, transparent)'

export default async function MyCardPage() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value
  if (!token) redirect('/login')

  let card: PlayerCard | null = null
  try {
    card = await getBackend().getMyCard(token)
  } catch (e) {
    if (e instanceof BackendError && e.status === 401) redirect('/login')
    if (!(e instanceof BackendError && e.code === 'CARD_NOT_FOUND')) throw e
  }

  return (
    <main className="mx-auto flex max-w-xl flex-col items-center gap-6 py-16">
      {card ? (
        <>
          <PlayerCardView card={card} />
          <p className="text-sm" style={{ color: MUTED }}>
            공유 링크:{' '}
            <Link href={`/c/${card.public_slug}`} className="underline" style={{ color: 'var(--ss-accent)' }}>
              /c/{card.public_slug}
            </Link>
          </p>
        </>
      ) : (
        <GlassPanel className="px-8 py-10 text-center">
          <h1 className="text-xl font-semibold">아직 선수 카드가 없습니다</h1>
          <p className="mt-2 text-sm" style={{ color: MUTED }}>
            경기 영상이 분석되면 카드가 만들어집니다.
          </p>
        </GlassPanel>
      )}
      <Link href="/me" className="text-sm underline" style={{ color: MUTED }}>
        ← 프로필로
      </Link>
    </main>
  )
}
