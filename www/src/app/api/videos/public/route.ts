import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * **공개된 클립 전부** — 남의 것까지. 계약 3-6절 `GET /videos/public` (CCC 20).
 *
 * 홈의 영상 모음이 쓴다. 최근 것이 앞이고 최대 100건이다.
 *
 * 🔴 **로그인이 필요하다.** 익명 홈에서 부를 자리가 생기면 계약을 다시 봐야
 * 한다 — 지금은 계약이 인증을 요구한다.
 * 🔴 **캐시하지 않는다** — 남이 방금 공개한 것이 안 보이면 "공개했는데
 * 안 뜬다"가 된다.
 */
export const dynamic = 'force-dynamic'

export async function GET(req: NextRequest) {
  return withAuth(req, async (token) =>
    NextResponse.json(await getBackend().listPublicVideos(token)),
  )
}
