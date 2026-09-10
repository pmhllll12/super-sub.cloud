import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/** 카드를 자리에 등재한다. 주장만 — 바뀐 스쿼드 전체가 돌아온다. */
export async function POST(req: NextRequest, ctx: { params: Promise<{ teamId: string }> }) {
  const { teamId } = await ctx.params
  return withAuth(req, async (token) => {
    let body: {
      player_card_id?: unknown
      position_code?: unknown
      grid_col?: unknown
      grid_row?: unknown
    }
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
    /* 판 칸은 **선택**이다 — 등재하면서 홈 판에 바로 올릴 때만 준다(CCC 25).
       🔴 함께 주거나 함께 비운다. 한쪽만 오면 여기서 막는다. */
    const col = typeof body.grid_col === 'number' ? body.grid_col : null
    const row = typeof body.grid_row === 'number' ? body.grid_row : null
    if ((col === null) !== (row === null)) {
      return NextResponse.json(
        { error: { code: 'VALIDATION_ERROR', message: 'grid_col 과 grid_row 는 함께 보냅니다.' } },
        { status: 422 },
      )
    }
    const squad = await getBackend().addSquadMember(token, teamId, {
      player_card_id: body.player_card_id,
      position_code: body.position_code,
      grid_col: col,
      grid_row: row,
    })
    return NextResponse.json(squad, { status: 201 })
  })
}
