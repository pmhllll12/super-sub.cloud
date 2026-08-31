import { type Destination } from '@/components/HomeNav'

/**
 * 이 앱의 목적지 목록.
 *
 * 🔴 `app/page.tsx` 가 아니라 여기 있는 이유: 상단 글자 내비가 홈뿐 아니라
 * **로그인 뒤 모든 화면**의 헤더(`SiteHeader`)에 나온다. 페이지 파일에 두면
 * 레이아웃이 페이지를 import 하게 되어 방향이 거꾸로 선다.
 */

/**
 * 알약만 실제 동작이 붙어 있다 — 누르면 스쿼드 판 옆에 지인 찾기가 열린다
 * (`SquadPanel`). 그 판단을 제목으로 하므로 아래 FEATURED 의 제목과
 * **글자까지 같아야** 한다.
 */
export const FRIEND_SEARCH = '지인 찾기'

// 홈 상단 글자 내비에 적히는 목적지. 앱(flutter/.../home_screen.dart)의
// _kDestinations 에서 출발했지만 2026-08-30 에 웹에서 다시 골랐다:
//   - '내 선수 카드'를 '내 프로필'에 합쳤다(카드는 이제 /me 안에 있다)
//   - '레슨 · 코치'를 '레슨 · 상점'으로
//   - '경기장 예약'을 새로 넣었다
//   - 그리고 '내 프로필'을 이 줄에서 뺐다 — 우상단 **닉네임**이 그 자리다
//     (`HomeStage`). 같은 곳으로 가는 항목을 한 화면에 둘 두지 않는다.
//   - 2026-08-31: '용병 매칭' · '내 팀' 을 이 줄에서 빼서 헤드라인 자리의
//     알약 버튼으로 옮기고 이름도 '용병 찾기' · '팀 찾기' 로 바꿨다
//     (FEATURED). 같은 이유로 두 목록은 안 겹친다.
//
// href 가 있는 '영상 분석'은 requireUser() 에 걸리는 로그인 전용 화면이다 —
// authRequired: true 로 표시해 두면 로그인 안 한 사람에게 카드가 "로그인이
// 필요합니다"를 미리 보여준다(링크는 살려 둔다). 나머지는 아직 갈 곳이
// 없어 카드가 링크가 아니다(눌러도 아무 일이 없다).
// 헤드라인 자리(옛 `FIND YOUR SQUAD`)에 유리 알약 버튼으로 크게 내놓는 둘.
// **아래 DESTINATIONS 와 겹치지 않는다** — 같은 곳으로 가는 항목을 한 화면에
// 둘 두지 않는다(우상단 '내 프로필'을 글자 줄에서 뺀 것과 같은 규칙).
export const FEATURED: Destination[] = [
  {
    title: '용병 찾기',
    icon: 'sports_soccer',
    summary: '사람이 모자란 경기에\n뛸 사람을 찾습니다',
  },
  {
    title: '팀 찾기',
    icon: 'groups',
    summary: '함께 뛸 팀을 찾고\n지원합니다',
  },
  {
    // 🔴 제목이 `HomeStage` 의 FRIEND_SEARCH 와 **글자까지 같아야** 한다 —
    // 이 알약만 실제 동작(스쿼드 판 옆에 지인 찾기 열기)이 붙어 있고, 그
    // 판단을 제목으로 한다.
    title: FRIEND_SEARCH,
    icon: 'person_search',
    summary: '아는 사람을 찾아\n스쿼드에 넣습니다',
  },
]

/** 아무것도 안 가리켰을 때 강조해 둘 항목 — 둘 중 '용병 찾기'가 기본이다. */
export const DEFAULT_FEATURED = FEATURED[0].title

export const DESTINATIONS: Destination[] = [
  {
    title: '영상 분석',
    icon: 'camera_video',
    summary: '경기 영상을 올리면\n실력 리포트가 나옵니다',
    href: '/analysis',
    authRequired: true,
  },
  {
    title: '레슨 · 상점',
    icon: 'add_business',
    summary: '제휴 코치와 장비를\n한자리에서',
  },
  {
    title: '경기장 예약',
    icon: 'stadium',
    summary: '가까운 구장을 찾고\n시간을 잡습니다',
  },
]
