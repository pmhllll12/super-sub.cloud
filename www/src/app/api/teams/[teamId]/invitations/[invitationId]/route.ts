import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 보낸 초대를 **무른다** — 주장만(계약 3-3절).
 *
 * 🔴 `204` 가 아니라 **무른 초대를 그대로 돌려준다** — 삭제라기보다 상태
 * 전이라, 화면이 다른 응답과 같은 파서로 읽는다.
 * ⚠️ **알림이 없다** — 보낸 쪽이 스스로 하는 것이라 알릴 상대가 없다.
 */
export async function DELETE(
  req: NextRequest,
  ctx: { params: Promise<{ teamId: string; invitationId: string }> },
) {
  const { teamId, invitationId } = await ctx.params
  return withAuth(req, async (token) =>
    NextResponse.json(
      await getBackend().cancelTeamInvitation(token, teamId, invitationId),
    ),
  )
}
