import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/** 카드를 자리에 등재한다. 주장만 — 바뀐 스쿼드 전체가 돌아온다. */
export async function POST(req: NextRequest, ctx: { params: Promise<{ teamId: string }> }) {
  const { teamId } = await ctx.params
  return withAuth(req, async (token) => {
    let body: { player_card_id?: unknown; position_code?: unknown }
    try {
      body = await req.json()
    } catch {
      return NextResponse.json(
        { error: { code: 'BAD_REQUEST', message: '요청 형식이 잘못되었습니다.' } },
        { status: 400 },
      )
    }
    if (typeof body.player_card_id !== 'string' || typeof body.position_code !== 'string') {
      return NextResponse.json(
        {
          error: {
            code: 'VALIDATION_ERROR',
            message: 'player_card_id 와 position_code 가 필요합니다.',
          },
        },
        { status: 422 },
      )
    }
    const squad = await getBackend().addSquadMember(token, teamId, {
      player_card_id: body.player_card_id,
      position_code: body.position_code,
    })
    return NextResponse.json(squad, { status: 201 })
  })
}
