import type { Metadata } from 'next'
import { cache } from 'react'
import { notFound } from 'next/navigation'
import PlayerCardView from '@/components/PlayerCardView'
import { BackendError, getBackend, type PublicPlayerCard } from '@/server/backend'

/**
 * generateMetadata 와 페이지 컴포넌트가 같은 slug 로 각각 호출한다.
 * load 는 fetch 가 아니라 모듈 함수라 Next 의 fetch 중복 제거가 적용되지
 * 않으므로 React cache() 로 직접 묶는다 — 요청당 백엔드 호출을 한 번으로 줄인다.
 */
const load = cache(async (slug: string): Promise<PublicPlayerCard | null> => {
  try {
    return await getBackend().getPublicCard(slug)
  } catch (e) {
    if (e instanceof BackendError && e.status === 404) return null
    throw e
  }
})

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
    <main className="mx-auto flex min-h-screen max-w-xl items-center justify-center px-6 py-16">
      <PlayerCardView card={card} />
    </main>
  )
}
