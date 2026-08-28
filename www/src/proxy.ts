import { NextResponse, type NextRequest } from 'next/server'
import { SESSION_COOKIE } from '@/server/session'

/**
 * 로그인하지 않은 사람은 어느 경로로 들어와도 로그인 화면으로 보낸다.
 *
 * 처음에는 `/`(홈)와 `/c/{slug}`(공개 카드)를 열어 뒀지만, "아무나 들어오면
 * 안 된다"는 판단으로 **사이트 전체를 닫았다**(2026-08-28). 공유 링크로 받은
 * 카드도 로그인해야 보인다 — 학원 프로젝트라 공개 범위를 좁히는 쪽을 골랐다.
 *
 * 여는 곳은 로그인·회원가입 두 화면뿐이다. 가입을 막으면 새 사람이 들어올
 * 길이 없어져서 `/signup` 은 남겨 둔다.
 *
 * ⚠️ Next.js 16 에서 `middleware.ts` 는 **`proxy.ts` 로 이름이 바뀌었다**
 * (기능은 같다). `middleware.ts` 로 만들면 조용히 안 걸리므로 되돌리지 말 것.
 * — node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/proxy.md
 *
 * 여기서 하는 건 **쿠키가 있는지**까지다. 토큰이 진짜 유효한지는 각 화면의
 * `requireUser()` 가 백엔드에 물어서 확인한다 — 프록시는 CDN 가까이에서
 * 도는 자리라 백엔드 왕복을 넣을 곳이 아니다.
 */
const PUBLIC_PATHS = new Set(['/login', '/signup'])

export function proxy(request: NextRequest) {
  if (PUBLIC_PATHS.has(request.nextUrl.pathname)) return NextResponse.next()
  if (request.cookies.get(SESSION_COOKIE)?.value) return NextResponse.next()

  // 원래 가려던 경로의 쿼리는 떼고 보낸다 — 로그인 화면에 끌고 갈 이유가 없다.
  return NextResponse.redirect(new URL('/login', request.nextUrl))
}

export const config = {
  /**
   * 넘기는 것들:
   * - `api` — Route Handler 는 스스로 인증을 확인하고 401 JSON 을 준다.
   *   여기서 리다이렉트하면 fetch 가 로그인 HTML 을 받아 들고 깨진다
   * - `_next` — 빌드 산출물(청크·폰트·이미지 최적화)
   * - **점이 들어간 경로** — `public/` 의 파일들이 `/login_figure.jpg` 처럼
   *   루트에 붙는다. 막으면 **로그인 화면 자신의 배경 사진이 안 뜬다**
   */
  matcher: ['/((?!api|_next|.*\\.).*)'],
}
