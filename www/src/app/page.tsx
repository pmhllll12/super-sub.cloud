import { type User } from '@/server/backend'
import { requireUser } from '@/server/currentUser'
import HomeParallax, { type Destination } from '@/components/HomeParallax'
import FloatingNavBar from '@/components/ui/FloatingNavBar'

// flutter/lib/features/home/presentation/screens/home_screen.dart 의 _kDestinations 와 같은 순서 · 같은 뜻.
// '내 선수 카드' 는 앱엔 아직 route 가 없지만(미완성) 웹엔 /me/card 가 실재하므로 여기선 링크를 건다.
//
// 카드 6장은 로그인 여부와 무관하게 항상 보인다. href 가 있는 세 카드
// (/analysis, /me/card, /me)는 전부 그 경로의 requireUser() 에 걸리는
// 로그인 전용 화면이다 — 로그인 안 한 채 누르면 결국 /login 으로 돌아간다.
// 그 사실을 카드에 미리 적어 두려고(눌러 보기 전엔 몰랐던 예전 방식 대신)
// authRequired: true 로 표시한다 — HomeParallax 가 로그인 여부와 대조해
// "로그인이 필요합니다" 안내문을 보여줄지 정한다. 링크 자체는 그대로
// 살아 있다 — 카드를 비활성으로 막지 않는다.
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
    title: '내 선수 카드',
    icon: 'id_card',
    summary: '호칭을 모으고\n카드를 공유합니다',
    href: '/me/card',
    authRequired: true,
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
    authRequired: true,
  },
]

/**
 * 마크업만 따로 뺀 것 — `Home` 이 서버 컴포넌트로 쿠키 · 백엔드를 부르게
 * 되면서 테스트가 이 함수를 직접 렌더한다(쿠키/백엔드 호출 분기를 타지
 * 않는다).
 *
 * 홈은 격자가 아니라 화면 전체를 쓰는 캐러셀이라 `(app)` 레이아웃처럼
 * `max-w-[1120px]` 로 가운데 폭을 좁힐 이유가 없다 — 워드마크(좌상단) ·
 * 인사말(우상단) · 글래스 테두리 판까지 `HomeParallax` 가 전부
 * `position: fixed` 로 화면 전체 기준으로 배치한다.
 *
 * 하단 내비바는 로그인했을 때만 보여준다 — 로그인 안 한 사람은 갈 데가
 * 대부분 막혀 있어 의미가 없다. 캐러셀은 세로로 스크롤하는 화면이
 * 아니라(카드가 화면 세로 가운데 고정) 내비바를 위한 별도 아래쪽 여백이
 * 필요 없다 — 내비바는 늘 `fixed` 라 그 위에 얹힌다.
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
