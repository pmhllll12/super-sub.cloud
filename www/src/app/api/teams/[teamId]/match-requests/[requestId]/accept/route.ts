import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 수락 → 확정 경기가 생긴다(응답의 `match_id`). **대상 팀 주장만** (계약 3-15절).
 *
 * 🔴 수락되는 순간 **두 팀의 다른 `pending` 신청은 서버가 `cancelled` 로
 * 정리한다** — 이중 예약 방지다. 화면에서 따로 막지 않는다.
 */
export async function POST(
  req: NextRequest,
  ctx: { params: Promise<{ teamId: string; requestId: string }> },
) {
  const { teamId, requestId } = await ctx.params
  return withAuth(req, async (token) =>
    NextResponse.json(await getBackend().acceptTeamMatch(token, teamId, requestId)),
  )
}
