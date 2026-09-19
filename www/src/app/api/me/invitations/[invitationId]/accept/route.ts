import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/** 초대 수락 — 그때 `team_member` 가 `member` 로 생긴다(계약 3-3절). */
export async function POST(
  req: NextRequest,
  ctx: { params: Promise<{ invitationId: string }> },
) {
  const { invitationId } = await ctx.params
  return withAuth(req, async (token) =>
    NextResponse.json(await getBackend().acceptInvitation(token, invitationId)),
  )
}
