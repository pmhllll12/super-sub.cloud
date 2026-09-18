import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 초대 거절 — 🔴 **실패가 아니다.** `200` 이고 아무것도 안 바뀐 것이 맞는
 * 결과다(계약의 「하지 말 것」). 거절하면 그 팀 주장에게 알림이 간다.
 */
export async function POST(
  req: NextRequest,
  ctx: { params: Promise<{ invitationId: string }> },
) {
  const { invitationId } = await ctx.params
  return withAuth(req, async (token) =>
    NextResponse.json(await getBackend().rejectInvitation(token, invitationId)),
  )
}
