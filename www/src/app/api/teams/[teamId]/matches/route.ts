import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

type NeedInput = { position_code?: unknown; head_count?: unknown }

/**
 * 경기를 새로 연다. 주장만 — 아니면 백엔드가 403 `FORBIDDEN`을 던진다
 * (api-contract.md 3-4절). `MatchBot`(챗봇 흐름 B)의 [등록] 버튼이 이걸 부른다 —
 * 실제 쓰기는 챗봇의 LLM 도구가 아니라 이 일반 API 콜이 한다(미결 `min` 7번).
 */
export async function POST(req: NextRequest, ctx: { params: Promise<{ teamId: string }> }) {
  const { teamId } = await ctx.params
  return withAuth(req, async (token) => {
    let body: { played_at?: unknown; place?: unknown; needs?: unknown }
    try {
      body = await req.json()
    } catch {
      return NextResponse.json(
        { error: { code: 'BAD_REQUEST', message: '요청 형식이 잘못되었습니다.' } },
        { status: 400 },
      )
    }
    if (
      typeof body.played_at !== 'string' ||
      typeof body.place !== 'string' ||
      !Array.isArray(body.needs) ||
      body.needs.length === 0
    ) {
      return NextResponse.json(
        {
          error: {
            code: 'VALIDATION_ERROR',
            message: 'played_at · place · needs(1개 이상)가 필요합니다.',
          },
        },
        { status: 422 },
      )
    }
    const needs = body.needs as NeedInput[]
    const valid = needs.every(
      (n) => typeof n.position_code === 'string' && typeof n.head_count === 'number',
    )
    if (!valid) {
      return NextResponse.json(
        {
          error: {
            code: 'VALIDATION_ERROR',
            message: 'needs의 각 항목은 position_code(문자열)·head_count(숫자)가 필요합니다.',
          },
        },
        { status: 422 },
      )
    }
    const match = await getBackend().createTeamMatch(token, teamId, {
      played_at: body.played_at,
      place: body.place,
      needs: needs as { position_code: string; head_count: number }[],
    })
    return NextResponse.json(match, { status: 201 })
  })
}
