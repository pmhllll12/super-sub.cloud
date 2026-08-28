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
