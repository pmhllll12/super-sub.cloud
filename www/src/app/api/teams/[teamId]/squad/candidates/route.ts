import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 빈 자리에 넣을 **추천 후보** (계약 3-16절, CCC 44번).
 *
 * 🔴 **순서가 곧 추천이다** — 서버가 이미 「이미 앉은 사람들의 등급 평균과
 * 가까운 순」으로 정렬해서 준다. 여기서도 화면에서도 다시 줄 세우지 않는다.
 *
 * 🔴 `grade` 는 **있을 때만 싣는다.** 「상관없음」을 빈 문자열로 보내면
 * (`grade=`) 없는 등급이라 422 다 — 생략과 `"any"` 만 「안 거른다」는 뜻이다.
 */
export async function GET(req: NextRequest, ctx: { params: Promise<{ teamId: string }> }) {
  const { teamId } = await ctx.params
  const position = req.nextUrl.searchParams.get('position_code')?.trim() ?? ''
  const grade = req.nextUrl.searchParams.get('grade')?.trim() ?? ''
  return withAuth(req, async (token) => {
    if (!position) {
      return NextResponse.json(
        { error: { code: 'VALIDATION_ERROR', message: 'position_code 가 필요합니다.' } },
        { status: 422 },
      )
    }
    return NextResponse.json(
      await getBackend().listSquadCandidates(token, teamId, {
        position_code: position,
        ...(grade && grade !== 'any' ? { grade } : {}),
      }),
    )
  })
}
