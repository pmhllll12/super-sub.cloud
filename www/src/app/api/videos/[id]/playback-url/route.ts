import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 그 클립을 재생할 수 있는 주소 — 계약 3-6절 `GET /videos/{id}/playback-url`.
 *
 * 🔴 **캐시하지 않는다.** 사전 서명 URL 은 `expires_in`(기본 900초) 뒤 만료되므로
 * 재생 직전에 받아야 한다. 여기에 `revalidate` 를 걸면 만료된 주소를 나눠 준다.
 */
export const dynamic = 'force-dynamic'

export async function GET(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params
  return withAuth(req, async (token) => NextResponse.json(await getBackend().getPlaybackUrl(token, id)))
}
