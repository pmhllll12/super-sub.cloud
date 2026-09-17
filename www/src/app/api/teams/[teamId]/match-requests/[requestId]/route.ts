import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 신청 팀이 스스로 무른다 — `pending` 일 때만 (계약 3-15절).
 *
 * 🔴 **204 가 아니다.** 취소된 신청을 그대로 돌려준다 — 다른 응답과 같은
 * 모양이라 부르는 쪽이 빈 본문 갈래를 따로 안 만들어도 된다.
 */
export async function DELETE(
  req: NextRequest,
  ctx: { params: Promise<{ teamId: string; requestId: string }> },
) {
  const { teamId, requestId } = await ctx.params
  return withAuth(req, async (token) =>
    NextResponse.json(await getBackend().cancelTeamMatch(token, teamId, requestId)),
  )
}
