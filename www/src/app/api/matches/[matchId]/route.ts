import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 확정 경기를 **무른다** — 계약 3-4절 `DELETE /matches/{match_id}`, `204`.
 *
 * 🔴 **팀 대 팀이면 주최·상대 어느 쪽 주장이든** 취소할 수 있다. 취소 안 한
 * 쪽 주장에게 알림이 간다.
 *
 * 🔴 **에러를 그대로 올려 보낸다** — `403`(주장 아님) · `404` · `409`
 * (`MATCH_HAS_APPLICATIONS`, 지원이 붙어 있다) · `422`(지난 경기). 화면이
 * 미리 막지 않고 서버가 준 문구를 보여 준다: 지원이 몇인지도, 상대 팀 주장이
 * 누구인지도 **서버만 안다**(마지막 주장 나가기와 같은 원칙).
 */
export async function DELETE(
  req: NextRequest,
  ctx: { params: Promise<{ matchId: string }> },
) {
  const { matchId } = await ctx.params
  return withAuth(req, async (token) => {
    await getBackend().cancelMatch(token, matchId)
    return new NextResponse(null, { status: 204 })
  })
}
