import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/** 거절. **대상 팀 주장만** (계약 3-15절). 신청 팀에 알림이 간다. */
export async function POST(
  req: NextRequest,
  ctx: { params: Promise<{ teamId: string; requestId: string }> },
) {
  const { teamId, requestId } = await ctx.params
  return withAuth(req, async (token) =>
    NextResponse.json(await getBackend().rejectTeamMatch(token, teamId, requestId)),
  )
}
