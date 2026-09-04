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
