import { type User } from '@/server/backend'
import { requireUser } from '@/server/currentUser'
import HomeParallax from '@/components/HomeParallax'
import { type Destination } from '@/components/HomeNav'
import FloatingNavBar from '@/components/ui/FloatingNavBar'

// 홈 상단 글자 내비에 적히는 6개. 앱(flutter/.../home_screen.dart)의
// _kDestinations 에서 출발했지만 2026-08-30 에 웹에서 다시 골랐다:
//   - '내 선수 카드'를 '내 프로필'에 합쳤다(카드는 이제 /me 안에 있다)
//   - '레슨 · 코치'를 '레슨 · 상점'으로
//   - '경기장 예약'을 새로 넣어 6개를 맞췄다
//
// href 가 있는 두 곳(/analysis, /me)은 그 경로의 requireUser() 에 걸리는
// 로그인 전용 화면이다 — authRequired: true 로 표시해 두면 로그인 안 한
// 사람에게 카드가 "로그인이 필요합니다"를 미리 보여준다(링크는 살려 둔다).
// 나머지 넷은 아직 갈 곳이 없어 카드에 "준비 중입니다"가 뜬다.
const DESTINATIONS: Destination[] = [
  {
    title: '영상 분석',
    icon: 'videocam',
    summary: '경기 영상을 올리면\n실력 리포트가 나옵니다',
    href: '/analysis',
    authRequired: true,
  },
  {
    title: '용병 매칭',
    icon: 'sports_soccer',
    summary: '경기를 찾고\n지원 현황을 봅니다',
  },
  {
    title: '내 프로필',
    icon: 'person',
    summary: '선수 카드와\n가입 정보',
    href: '/me',
    authRequired: true,
  },
  {
    title: '내 팀',
    icon: 'groups',
    summary: '팀원과 스쿼드를\n관리합니다',
  },
  {
    title: '레슨 · 상점',
    icon: 'storefront',
    summary: '제휴 코치와 장비를\n한자리에서',
  },
  {
    title: '경기장 예약',
    icon: 'stadium',
    summary: '가까운 구장을 찾고\n시간을 잡습니다',
  },
]

/**
 * 마크업만 따로 뺀 것 — `Home` 이 서버 컴포넌트로 쿠키 · 백엔드를 부르게
 * 되면서 테스트가 이 함수를 직접 렌더한다(쿠키/백엔드 호출 분기를 타지
 * 않는다).
 *
 * 홈은 격자가 아니라 화면 한 장을 통째로 쓰므로 `(app)` 레이아웃처럼
 * `max-w-[1120px]` 로 가운데 폭을 좁히지 않는다 — 헤더 · 하단 줄을
 * `HomeParallax` 가 `position: fixed` 로 화면 전체 기준으로 배치한다.
 *
 * 하단 내비바는 로그인했을 때만 보여준다 — 로그인 안 한 사람은 갈 데가
 * 대부분 막혀 있어 의미가 없다. 세로로 스크롤하는 화면이 아니라 내비바를
 * 위한 별도 아래쪽 여백이 필요 없다 — 내비바는 늘 `fixed` 라 위에 얹힌다.
 */
export function HomeBody({ user }: { user: Pick<User, 'nickname'> | null }) {
  return (
    <>
      <HomeParallax user={user} destinations={DESTINATIONS} />
      {user && <FloatingNavBar />}
    </>
  )
}

// `/` 가 곧 홈이다 — 앱처럼 홈이 하나뿐이다(공개 랜딩과 로그인 후 런처로
// 나뉘어 있지 않다). 인트로(`IntroGate`, 루트 레이아웃)를 지나면 이 화면이 나온다.
//
// 2026-08-28 부터 **로그인해야 들어올 수 있다.** 앞단의 `proxy.ts` 가 쿠키
// 없는 요청을 이미 `/login` 으로 보내지만, 그건 쿠키가 "있는지"까지만 본다 —
// 썩은 토큰을 들고 온 경우까지 막으려면 여기서 백엔드에 확인해야 한다.
// `requireUser()` 가 그 일을 하고, 401 이면 `/login` 으로 보낸다.
//
// `HomeBody` 는 여전히 `user: null` 을 받을 수 있게 두었다 — 인사말 자리가
// 갈리는 마크업은 테스트가 직접 렌더해 검증한다.
export default async function Home() {
  const user: User = await requireUser()
  return <HomeBody user={user} />
}
