import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/** 등재를 뺀다. **카드는 지워지지 않는다** — 스쿼드에서 빠질 뿐이다. */
export async function DELETE(
  req: NextRequest,
  ctx: { params: Promise<{ teamId: string; memberId: string }> },
) {
  const { teamId, memberId } = await ctx.params
  return withAuth(req, async (token) =>
    NextResponse.json(await getBackend().removeSquadMember(token, teamId, memberId)),
  )
}
