import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 팀에서 나간다(본인) 또는 뺀다(주장) — 계약 3-3절.
 *
 * 🔴 `memberId` 는 **그 사람의 `user_id`** 다(백엔드가 `LeaveTeamCommand`
 * 의 `user_id` 로 받는다). 소속 행의 id 가 아니다.
 *
 * 🔴 **마지막 주장은 못 나간다**(`409 LAST_OWNER`) — 소유권 이양 경로가 아직
 * 없다. 화면에서 미리 막지 않고 이 코드를 그대로 올려 보낸다.
 */
export async function DELETE(
  req: NextRequest,
  ctx: { params: Promise<{ teamId: string; memberId: string }> },
) {
  const { teamId, memberId } = await ctx.params
  return withAuth(req, async (token) => {
    await getBackend().leaveTeam(token, teamId, memberId)
    return new NextResponse(null, { status: 204 })
  })
}
