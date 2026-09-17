import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 「맞는 상대」 후보 (계약 3-13절, CCC 40번).
 *
 * 🔴 **이미 정렬돼 있다.** 유사도 점수가 없고, 근거는 `reasons` 의 **사실값
 * 문장**이다 — 화면이 겹침을 다시 계산하지 않는다(계약의 「하지 말 것」:
 * 다시 계산하면 서버와 다른 답이 나온다).
 */
export async function GET(req: NextRequest, ctx: { params: Promise<{ teamId: string }> }) {
  const { teamId } = await ctx.params
  return withAuth(req, async (token) =>
    NextResponse.json(await getBackend().listMatchCandidates(token, teamId)),
  )
}
