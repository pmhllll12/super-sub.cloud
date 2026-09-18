import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 팀 초대 — 계약 3-3절 「팀 초대」(CCC 49·53번), **주장만**.
 *
 * 🔴 **동의 없이 꽂지 않는다**(2026-09-10 박민호 결정). `POST /teams/{id}/members`
 * 로 바로 넣는 길은 **본인이 스스로 가입할 때만** 쓴다.
 */
export async function POST(
  req: NextRequest,
  ctx: { params: Promise<{ teamId: string }> },
) {
  const { teamId } = await ctx.params
  return withAuth(req, async (token) => {
    let body: { invited_user_id?: unknown; position_code?: unknown }
    try {
      body = await req.json()
    } catch {
      return NextResponse.json(
        { error: { code: 'BAD_REQUEST', message: '요청 형식이 잘못되었습니다.' } },
        { status: 400 },
      )
    }
    const invited = body.invited_user_id
    if (typeof invited !== 'string' || !invited) {
      return NextResponse.json(
        { error: { code: 'VALIDATION_ERROR', message: '초대할 사람이 필요합니다.' } },
        { status: 422 },
      )
    }
    /* 🔴 **자리는 선택이다** — 안 정한 초대(「우리 팀에 오세요」)가 정상이라
       빈 값을 실어 보내지 않는다. 없는 약칭이면 서버가 422 로 막는다. */
    const position =
      typeof body.position_code === 'string' && body.position_code
        ? body.position_code
        : undefined

    const made = await getBackend().inviteToTeam(token, teamId, {
      invited_user_id: invited,
      ...(position ? { position_code: position } : {}),
    })
    return NextResponse.json(made, { status: 201 })
  })
}

/**
 * 그 팀이 보낸 초대 **전부**(상태 무관), 최신순.
 *
 * 🔴 **판을 되살리는 값이다** — 앉힌 사람이 새로고침 뒤에도 그 자리에 있는
 * 것은 이 목록 덕이다.
 */
export async function GET(
  req: NextRequest,
  ctx: { params: Promise<{ teamId: string }> },
) {
  const { teamId } = await ctx.params
  return withAuth(req, async (token) =>
    NextResponse.json(await getBackend().listTeamInvitations(token, teamId)),
  )
}
