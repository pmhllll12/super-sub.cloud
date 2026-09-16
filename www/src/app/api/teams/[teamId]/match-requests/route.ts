import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/** 그 팀이 **보낸 것 + 받은 것** 전부, 최신순 (계약 3-15절). 주장만. */
export async function GET(req: NextRequest, ctx: { params: Promise<{ teamId: string }> }) {
  const { teamId } = await ctx.params
  return withAuth(req, async (token) =>
    NextResponse.json(await getBackend().listTeamMatchRequests(token, teamId)),
  )
}

/**
 * 팀이 팀에게 경기를 건다 (계약 3-15절).
 *
 * 🔴 **개인이 모집 경기에 지원하는 `POST /matches/{id}/applications` 와 다른
 * 경로다.** 이름이 비슷해서 헷갈리기 쉽다 — 이쪽은 스쿼드가 다 찬 두 팀이
 * 맞붙는 흐름이고, 받는 사람은 상대 팀 **주장**이다.
 */
export async function POST(req: NextRequest, ctx: { params: Promise<{ teamId: string }> }) {
  const { teamId } = await ctx.params
  return withAuth(req, async (token) => {
    let body: { target_team_id?: unknown; played_at?: unknown; place?: unknown }
    try {
      body = await req.json()
    } catch {
      return NextResponse.json(
        { error: { code: 'BAD_REQUEST', message: '요청 형식이 잘못되었습니다.' } },
        { status: 400 },
      )
    }
    const { target_team_id, played_at, place } = body
    if (
      typeof target_team_id !== 'string' ||
      typeof played_at !== 'string' ||
      typeof place !== 'string'
    ) {
      return NextResponse.json(
        {
          error: {
            code: 'VALIDATION_ERROR',
            message: 'target_team_id · played_at · place 가 필요합니다.',
          },
        },
        { status: 422 },
      )
    }
    const made = await getBackend().requestTeamMatch(token, teamId, {
      target_team_id,
      played_at,
      place,
    })
    return NextResponse.json(made, { status: 201 })
  })
}
