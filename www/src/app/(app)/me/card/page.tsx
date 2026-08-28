import Link from 'next/link'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import PlayerCardView from '@/components/PlayerCardView'
import { BackendError, getBackend, type PlayerCard } from '@/server/backend'
import { SESSION_COOKIE } from '@/server/session'

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
    <main className="mx-auto max-w-xl px-6 py-16">
      {card ? (
        <>
          <PlayerCardView card={card} />
          <p className="mt-6 text-sm text-neutral-500">
            공유 링크:{' '}
            <Link href={`/c/${card.public_slug}`} className="underline">
              /c/{card.public_slug}
            </Link>
          </p>
        </>
      ) : (
        <div className="rounded-2xl border p-8">
          <h1 className="text-xl font-semibold">아직 선수 카드가 없습니다</h1>
          <p className="mt-2 text-sm text-neutral-500">
            경기 영상이 분석되면 카드가 만들어집니다.
          </p>
        </div>
      )}
      <Link href="/me" className="mt-8 inline-block text-sm underline">
        ← 프로필로
      </Link>
    </main>
  )
}
