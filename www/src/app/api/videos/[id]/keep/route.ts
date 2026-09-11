import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 「내 프로필에 리포트 저장」 — 계약 3-6절 `POST /videos/{id}/keep`
 * (미결 `jin` 24번 5조각, 2026-09-11).
 *
 * 🔴 본문이 없다 — 부를지 말지가 전부다. **멱등**이라 두 번 불러도 그대로다.
 * 🔴 이 호출 전까지 그 클립은 **임시**다(작업이 생긴 클립만). 화면을 벗어나면
 * 곧 지워지거나(`DELETE /videos/{id}`), 그것도 놓치면 서버가 24시간 뒤에
 * 지운다 — 분석에 실패해 다시 볼 리포트가 없는 클립을 남기지 않는 길이다.
 */
export async function POST(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params
  return withAuth(req, async (token) => NextResponse.json(await getBackend().keepVideo(token, id)))
}
