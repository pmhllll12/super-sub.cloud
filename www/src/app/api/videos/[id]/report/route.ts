import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 그 클립의 **분석 리포트** — 계약 3-1 `GET /videos/{id}/report`
 * (CCC 31 · 미결 `paik` 7번 · `jin` 27번, 2026-09-10).
 *
 * 🔴 **여기서 모양을 바꾸지 않는다.** 화면이 쓰는 모양으로 옮기는 일은
 * `lib/savedReports.ts` 가 한 곳에서 한다 — 두 곳에서 주무르면 어느 쪽이
 * 정본인지 모르게 된다.
 *
 * ⚠️ 아직 적재 전이면 서버가 404 `REPORT_NOT_READY` 를 준다. **그대로
 * 흘려보낸다** — 「분석 중」과 「결과가 없다」를 화면이 갈라 그려야 한다.
 */
export async function GET(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params
  return withAuth(req, async (token) => {
    return NextResponse.json(await getBackend().getVideoReport(token, id))
  })
}
