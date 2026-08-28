import HomeParallax, { type Destination } from '@/components/HomeParallax'
import { requireUser } from '@/server/currentUser'

// flutter/lib/features/home/presentation/screens/home_screen.dart 의 _kDestinations 와 같은 순서 · 같은 뜻.
// '내 선수 카드' 는 앱엔 아직 route 가 없지만(미완성) 웹엔 /me/card 가 실재하므로 여기선 링크를 건다.
const DESTINATIONS: Destination[] = [
  {
    title: '영상 분석',
    icon: 'videocam',
    summary: '경기 영상을 올리면\n실력 리포트가 나옵니다',
    href: '/analysis',
  },
  {
    title: '용병 매칭',
    icon: 'sports_soccer',
    summary: '경기를 찾고\n지원 현황을 봅니다',
  },
  {
    title: '내 선수 카드',
    icon: 'id_card',
    summary: '호칭을 모으고\n카드를 공유합니다',
    href: '/me/card',
  },
  {
    title: '내 팀',
    icon: 'groups',
    summary: '팀원과 스쿼드를\n관리합니다',
  },
  {
    title: '레슨 · 코치',
    icon: 'school',
    summary: '제휴 코치와\n연결합니다',
  },
  {
    title: '내 프로필',
    icon: 'person',
    summary: '닉네임과\n가입 정보',
    href: '/me',
  },
]

export default async function HomePage() {
  const user = await requireUser()

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col items-center gap-10 px-6 py-16">
      <HomeParallax nickname={user.nickname} destinations={DESTINATIONS} />
    </main>
  )
}
