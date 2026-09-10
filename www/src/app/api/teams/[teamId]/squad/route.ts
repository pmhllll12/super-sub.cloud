import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/** 팀의 스쿼드를 읽는다 — 소속이면 본다(api-contract.md 3-7절). */
export async function GET(req: NextRequest, ctx: { params: Promise<{ teamId: string }> }) {
  const { teamId } = await ctx.params
  return withAuth(req, async (token) => NextResponse.json(await getBackend().getSquad(token, teamId)))
}

/**
 * 스쿼드를 연다. **멱등이다** — 두 번 불러도 하나고 슬러그도 그대로다.
 * 그래서 재시도해도 공유 링크가 바뀌지 않는다(`POST /me/card` 와 같은 판단).
 */
export async function POST(req: NextRequest, ctx: { params: Promise<{ teamId: string }> }) {
  const { teamId } = await ctx.params
  return withAuth(req, async (token) =>
    NextResponse.json(await getBackend().createSquad(token, teamId), { status: 201 }),
  )
}

/**
 * 홈 스쿼드 판의 **판 크기**를 저장한다 — 계약 3-7절 (CCC 25). 주장만.
 *
 * 🔴 **값 집합을 여기서 좁히지 않는다.** 계약이 `"3:3"`·`"5:5"`·`"7:7"` 을
 * 강제하지 않고 길이만 보는 것은, 판 크기가 늘 때 마이그레이션이 없게 하려는
 * 판단이다 — BFF 가 더 좁게 굴면 서버가 이미 받는 값을 화면이 못 쓴다.
 */
export async function PATCH(req: NextRequest, ctx: { params: Promise<{ teamId: string }> }) {
  const { teamId } = await ctx.params
  return withAuth(req, async (token) => {
    let body: { formation?: unknown }
    try {
      body = await req.json()
    } catch {
      return NextResponse.json(
        { error: { code: 'BAD_REQUEST', message: '요청 형식이 잘못되었습니다.' } },
        { status: 400 },
      )
    }
    if (typeof body.formation !== 'string') {
      return NextResponse.json(
        { error: { code: 'VALIDATION_ERROR', message: 'formation 이 필요합니다.' } },
        { status: 422 },
      )
    }
    return NextResponse.json(await getBackend().setSquadFormation(token, teamId, body.formation))
  })
}
