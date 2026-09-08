import { type Destination } from '@/components/HomeNav'

/**
 * 이 앱의 목적지 목록.
 *
 * 🔴 `app/page.tsx` 가 아니라 여기 있는 이유: 상단 글자 내비가 홈뿐 아니라
 * **로그인 뒤 모든 화면**의 헤더(`SiteHeader`)에 나온다. 페이지 파일에 두면
 * 레이아웃이 페이지를 import 하게 되어 방향이 거꾸로 선다.
 */

/**
 * 알약 '용병 찾기' 의 제목 — **이 줄에서 유일하게 실제 동작이 붙어 있다.**
 * 누르면 스쿼드 판 오른쪽에 **AI 추천 판과 지인 찾기 판이 나란히** 열린다
 * (`HomeStage` → `SquadPanel`). 그 판단을 제목으로 하므로 아래 FEATURED 의
 * 제목과 **글자까지 같아야** 한다.
 *
 * 🔴 **`picked`(고른 알약)로 그 판을 열지 않는다.** 이 제목이
 * `DEFAULT_FEATURED` 이기도 해서, `picked === MATCH_BOT` 으로 열면 **홈에
 * 들어오자마자 떠 있고 ×를 눌러도 `defaultActive` 로 되돌아가 다시 열린다**
 * — 챗봇을 이 알약으로 열던 시절에 실제로 그랬다(미결 `min` 7번, 실측).
 * `HomeStage` 가 "눌렀다"를 따로 든 상태로 잡는 것이 그 때문이다.
 *
 * ⚠️ 챗봇(`MatchBot`)은 이 알약이 아니라 판 오른쪽 변의 **AI 단추**가 연다
 * (`SquadPanel` 의 `ss-home-ai`).
 */
export const MATCH_BOT = '용병 찾기'

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
    title: MATCH_BOT,
    icon: 'sports_soccer',
    summary: '사람이 모자란 경기에\n뛸 사람을 찾습니다',
  },
  {
    title: '팀 찾기',
    icon: 'groups',
    summary: '함께 뛸 팀을 찾고\n지원합니다',
  },
  // 🔴 '지인 찾기' 알약은 **없앴다**(사용자 요청, 2026-09-08). 용병을 찾는
  // 일과 아는 사람을 찾는 일이 결국 **같은 자리를 채우는 한 가지 일**이라,
  // 단추를 둘로 나누면 어느 쪽을 눌러야 하는지부터 고르게 된다. 지금은
  // '용병 찾기' 하나가 **추천 판과 지인 판을 같이** 연다 — 고르는 것은
  // 여전히 사람이지만, 그 선택지가 한 화면에 다 나와 있다.
]

/** 아무것도 안 가리켰을 때 강조해 둘 항목 — 둘 중 '용병 찾기'가 기본이다.
 *  🔴 이 값이 곧 MATCH_BOT 이라 **판을 여는 조건으로 쓰면 안 된다**(위 주석). */
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
    href: '/market',
    authRequired: true,
  },
  {
    title: '경기장 예약',
    icon: 'stadium',
    summary: '가까운 구장을 찾고\n시간을 잡습니다',
  },
]
