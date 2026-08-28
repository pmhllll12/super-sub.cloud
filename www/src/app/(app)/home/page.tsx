import BrandMark from '@/components/ui/BrandMark'
import DestinationCard from '@/components/DestinationCard'
import { requireUser } from '@/server/currentUser'

// flutter/lib/features/home/presentation/screens/home_screen.dart 의 _kDestinations 와 같은 순서 · 같은 뜻.
const DESTINATIONS: { title: string; icon: string; href?: string }[] = [
  { title: '영상 분석', icon: 'videocam', href: '/analysis' },
  { title: '용병 매칭', icon: 'sports_soccer' },
  { title: '내 선수 카드', icon: 'id_card', href: '/me/card' },
  { title: '내 팀', icon: 'groups' },
  { title: '레슨 · 코치', icon: 'school' },
  { title: '내 프로필', icon: 'person', href: '/me' },
]

export default async function HomePage() {
  const user = await requireUser()

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col items-center gap-10 px-6 py-16">
      <BrandMark />
      <p className="text-lg font-medium" style={{ color: 'var(--ss-fg)' }}>
        {user.nickname}
      </p>
      <div className="grid w-full grid-cols-2 gap-3">
        {DESTINATIONS.map((d) => (
          <DestinationCard key={d.title} title={d.title} icon={d.icon} href={d.href} />
        ))}
      </div>
    </main>
  )
}
