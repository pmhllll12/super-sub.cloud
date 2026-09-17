import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 우리 팀 경기 조건 (계약 3-13절, CCC 40번).
 *
 * 🔴 **이걸 올려야 남의 후보 목록에 우리 팀이 뜬다** — 서버가 「경기 조건을
 * 하나라도 등록한 팀만」 후보로 고른다. 전에는 조건이 브라우저에만 남아서
 * (`lib/matchPrefs.ts` 의 localStorage) 우리 팀이 남에게 아예 안 보였다.
 * 🔴 `PUT` 은 **통째로 교체**다 — 하나만 더하려도 전체를 다시 보낸다.
 */
export async function GET(req: NextRequest, ctx: { params: Promise<{ teamId: string }> }) {
  const { teamId } = await ctx.params
  return withAuth(req, async (token) =>
    NextResponse.json(await getBackend().getTeamMatchPrefs(token, teamId)),
  )
}

export async function PUT(req: NextRequest, ctx: { params: Promise<{ teamId: string }> }) {
  const { teamId } = await ctx.params
  return withAuth(req, async (token) => {
    const body = (await req.json().catch(() => null)) as {
      region_ids?: unknown
      slots?: unknown
    } | null
    /* 🔴 **모양을 여기서 본다.** 서버도 막지만, 빈 몸통을 그대로 흘리면
       「통째로 교체」 규칙 때문에 **조건이 전부 지워진다.** */
    if (!body || !Array.isArray(body.region_ids) || !Array.isArray(body.slots)) {
      return NextResponse.json(
        {
          error: {
            code: 'VALIDATION_ERROR',
            message: 'region_ids 와 slots 를 배열로 보내야 합니다.',
          },
        },
        { status: 422 },
      )
    }
    return NextResponse.json(
      await getBackend().putTeamMatchPrefs(token, teamId, {
        region_ids: body.region_ids as string[],
        slots: body.slots as { weekday: number; start_time: string; end_time: string }[],
      }),
    )
  })
}
