import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import PlayerCardView from '@/components/PlayerCardView'
import { BackendError, getBackend, type PublicPlayerCard } from '@/server/backend'

async function load(slug: string): Promise<PublicPlayerCard | null> {
  try {
    return await getBackend().getPublicCard(slug)
  } catch (e) {
    if (e instanceof BackendError && e.status === 404) return null
    throw e
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>
}): Promise<Metadata> {
  const { slug } = await params
  const card = await load(slug)
  if (!card) return { title: '카드를 찾을 수 없습니다 · Super-Sub' }

  const title = `${card.user.nickname} · Super-Sub`
  const description =
    card.titles.length > 0
      ? card.titles.map((t) => t.label).join(' · ')
      : '생활체육 선수 카드'

  return {
    title,
    description,
    openGraph: { title, description, type: 'profile' },
    twitter: { card: 'summary_large_image', title, description },
  }
}

export default async function PublicCardPage({
  params,
}: {
  params: Promise<{ slug: string }>
}) {
  const { slug } = await params
  const card = await load(slug)
  if (!card) notFound()

  return (
    <main className="mx-auto max-w-xl px-6 py-16">
      <PlayerCardView card={card} />
    </main>
  )
}
