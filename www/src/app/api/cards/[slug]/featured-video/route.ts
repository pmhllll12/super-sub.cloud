import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 그 사람의 **대표 영상** — 계약 3-6절 `GET /cards/{slug}/featured-video`
 * (CCC 27). 추천 판에서 후보 옆에 도는 장면이 이것이다.
 *
 * 🔴 **로그인이 필요하다.** 카드 자체(`/api/cards/{slug}`)는 슬러그만 알면
 * 열리지만, 여기는 **사전 서명 URL 을 내주는 자리**라 익명 긁기를 막는다.
 * 계약이 그렇게 갈라 두었고 이 파일이 `withAuth` 를 쓰는 이유가 그것이다.
 *
 * 🔴 **캐시하지 않는다** — `url` 은 `expires_in` 초 뒤 만료된다
 * (`playback-url` 과 같은 원칙).
 */
export const dynamic = 'force-dynamic'

export async function GET(req: NextRequest, ctx: { params: Promise<{ slug: string }> }) {
  const { slug } = await ctx.params
  return withAuth(req, async (token) =>
    NextResponse.json(await getBackend().getFeaturedVideo(token, slug)),
  )
}
