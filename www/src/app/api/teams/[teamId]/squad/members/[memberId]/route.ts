import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/** 등재를 뺀다. **카드는 지워지지 않는다** — 스쿼드에서 빠질 뿐이다. */
export async function DELETE(
  req: NextRequest,
  ctx: { params: Promise<{ teamId: string; memberId: string }> },
) {
  const { teamId, memberId } = await ctx.params
  return withAuth(req, async (token) =>
    NextResponse.json(await getBackend().removeSquadMember(token, teamId, memberId)),
  )
}

/**
 * 등재 하나의 **포지션 · 판 배치**를 바꾼다 — 계약 3-7절 (CCC 25). 주장만.
 *
 * 전에는 포지션을 바꾸려면 빼고 다시 넣어야 했다(계약의 「아직 없는 것」).
 * 그 사이에 끊기면 등재가 사라진 채로 남는 자리였다.
 *
 * 🔴 `grid_col`·`grid_row` 는 **함께 주거나 함께 비운다.** 한쪽만 오면 여기서
 * 막는다 — 서버까지 보내도 422 지만, 조용히 채워 보내면 판에 없어야 할
 * 카드가 0번 칸에 선다.
 * 🔴 **포지션을 칸에서 역산하지 않는다** — 손으로 정한 값이라 자리와 다를 수 있다.
 */
export async function PATCH(
  req: NextRequest,
  ctx: { params: Promise<{ teamId: string; memberId: string }> },
) {
  const { teamId, memberId } = await ctx.params
  return withAuth(req, async (token) => {
    let body: { position_code?: unknown; grid_col?: unknown; grid_row?: unknown }
    try {
      body = await req.json()
    } catch {
      return NextResponse.json(
        { error: { code: 'BAD_REQUEST', message: '요청 형식이 잘못되었습니다.' } },
        { status: 400 },
      )
    }
    // 🔴 등재는 포지션 없이 존재하지 않는다 — 칸만 옮길 때도 지금 코드를 싣는다.
    if (typeof body.position_code !== 'string') {
      return NextResponse.json(
        { error: { code: 'VALIDATION_ERROR', message: 'position_code 가 필요합니다.' } },
        { status: 422 },
      )
    }
    const col = typeof body.grid_col === 'number' ? body.grid_col : null
    const row = typeof body.grid_row === 'number' ? body.grid_row : null
    if ((col === null) !== (row === null)) {
      return NextResponse.json(
        {
          error: {
            code: 'VALIDATION_ERROR',
            message: 'grid_col 과 grid_row 는 함께 보냅니다.',
          },
        },
        { status: 422 },
      )
    }
    return NextResponse.json(
      await getBackend().updateSquadMember(token, teamId, memberId, {
        position_code: body.position_code,
        grid_col: col,
        grid_row: row,
      }),
    )
  })
}
