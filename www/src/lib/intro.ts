/** 인트로를 재생할 자리. 앱 진입 두 곳뿐이다. */
const ENTRY_PATHS = ['/', '/login']

/**
 * 인트로(글리치 워드마크)를 재생할지 판단하는 순수 함수.
 *
 * - `/`, `/login` 같은 앱 진입점에서만 재생한다.
 * - 공개 카드 공유 링크(`/c/{slug}`)나 로그인한 화면(`/home`, `/me` 등)에서는
 *   재생하지 않는다 — 공유 링크를 열자마자 2.5초를 막으면 공유가 성립하지 않는다.
 * - 세션에서 이미 봤으면 다시 재생하지 않는다.
 */
export function shouldPlayIntro(pathname: string, seen: boolean): boolean {
  if (seen) return false
  return ENTRY_PATHS.includes(pathname)
}

export const INTRO_SEEN_KEY = 'supersub_intro_seen'

/**
 * `sessionStorage` 접근은 사파리 프라이빗 모드 등에서 던질 수 있다.
 * 던지면 "이미 봤다"로 친다 — 연출 때문에 앱이 안 열리는 것보다,
 * 인트로를 건너뛰는 편이 안전하다.
 *
 * `IntroGate`(전역 오버레이)와 `LandingGate`(`/`의 로그인 후 이동 판단) 둘 다
 * "이번에 인트로가 재생되는가"를 같은 기준으로 판단해야 해서 여기 하나로
 * 모았다 — 따로 두면 둘의 판단이 어긋날 수 있다.
 */
export function hasSeenIntro(): boolean {
  try {
    return sessionStorage.getItem(INTRO_SEEN_KEY) === '1'
  } catch {
    return true
  }
}

export function markIntroSeen(): void {
  try {
    sessionStorage.setItem(INTRO_SEEN_KEY, '1')
  } catch {
    // 못 쓰면 그냥 둔다 — 다음 진입에서 다시 재생될 뿐, 화면은 정상 동작한다.
  }
}

/**
 * `IntroGate`가 인트로를 끝낼 때(스스로 마쳤든, 이미지 로드 실패로 조기
 * 종료했든) 쏘는 전역 이벤트.
 *
 * `/` 페이지(`LandingGate`)처럼 "인트로가 끝난 뒤에 갈 곳을 정해야" 하는
 * 쪽이 구독한다. `IntroGate`는 `usePathname()`만 보고 `loggedIn` 여부를
 * 모르므로(레이아웃 전역이라 서버 쿠키를 안 읽는다) 이동 판단 자체는 여기서
 * 하지 않는다 — 이벤트만 쏘고, 판단은 구독자 몫이다.
 */
export const INTRO_DONE_EVENT = 'supersub:intro-done'
