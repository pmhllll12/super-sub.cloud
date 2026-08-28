import { cookies } from 'next/headers'
import { BackendError, getBackend, type User } from '@/server/backend'
import { SESSION_COOKIE } from '@/server/session'
import HomeParallax, { type Destination } from '@/components/HomeParallax'
import FloatingNavBar from '@/components/ui/FloatingNavBar'

// flutter/lib/features/home/presentation/screens/home_screen.dart 의 _kDestinations 와 같은 순서 · 같은 뜻.
// '내 선수 카드' 는 앱엔 아직 route 가 없지만(미완성) 웹엔 /me/card 가 실재하므로 여기선 링크를 건다.
//
// 카드 6장은 로그인 여부와 무관하게 항상 보인다. 로그인이 필요한 카드
// (/me/card, /me)를 로그인 안 한 채 누르면 그 경로의 requireUser() 가
// 알아서 /login 으로 돌려보낸다 — 여기서 따로 막지 않는다.
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

/**
 * 마크업만 따로 뺀 것 — `Home` 이 서버 컴포넌트로 쿠키 · 백엔드를 부르게
 * 되면서 테스트가 이 함수를 직접 렌더한다(쿠키/백엔드 호출 분기를 타지
 * 않는다).
 *
 * 하단 내비바는 로그인했을 때만 보여준다 — 로그인 안 한 사람은 갈 데가
 * 대부분 막혀 있어 의미가 없다. `(app)` 레이아웃(`max-w-[1120px] px-6
 * pb-32` + `FloatingNavBar`)과 같은 모양을, 내비바가 있을 때만 반영한다
 * (`pb-32` 는 내비바에 콘텐츠가 가리지 않게 하는 여백이라 내비바가 없으면
 * 필요 없다).
 */
export function HomeBody({ user }: { user: Pick<User, 'nickname'> | null }) {
  return (
    <>
      <div className={`mx-auto max-w-[1120px] px-6 ${user ? 'pb-32' : ''}`}>
        <main className="mx-auto flex min-h-screen max-w-2xl flex-col items-center gap-10 py-16">
          <HomeParallax user={user} destinations={DESTINATIONS} />
        </main>
      </div>
      {user && <FloatingNavBar />}
    </>
  )
}

// `/` 가 곧 홈이다 — 앱처럼 홈이 하나뿐이다(공개 랜딩과 로그인 후 런처로
// 나뉘어 있지 않다). 인트로(`IntroGate`, 루트 레이아웃)를 지나면 로그인
// 여부와 무관하게 이 화면이 나오고, 인사말 자리만 갈린다: 로그인했으면
// 닉네임 + 로그아웃, 안 했으면 로그인 · 회원가입 버튼(`HomeParallax`).
//
// 쿠키만 있고 토큰이 썩었으면(백엔드가 401) 로그아웃 상태로 취급한다 —
// 로그인으로 튕기지 않는다. 홈은 로그인 없이도 정상 화면이라 여기서까지
// 리다이렉트할 이유가 없다(보호된 카드를 눌렀을 때만 그 경로가 알아서
// /login 으로 보낸다).
export default async function Home() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value
  let user: User | null = null
  if (token) {
    try {
      user = await getBackend().getMe(token)
    } catch (e) {
      if (!(e instanceof BackendError && e.status === 401)) throw e
    }
  }
  return <HomeBody user={user} />
}
