import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

export async function GET(req: NextRequest) {
  return withAuth(req, async (token) => NextResponse.json(await getBackend().getMe(token)))
}

export async function PATCH(req: NextRequest) {
  return withAuth(req, async (token) => {
    let body: { nickname?: unknown }
    try {
      body = await req.json()
    } catch {
      return NextResponse.json(
        { error: { code: 'BAD_REQUEST', message: '요청 형식이 잘못되었습니다.' } },
        { status: 400 },
      )
    }
    if (typeof body.nickname !== 'string') {
      return NextResponse.json(
        { error: { code: 'VALIDATION_ERROR', message: '요청 값이 올바르지 않습니다: nickname' } },
        { status: 422 },
      )
    }
    return NextResponse.json(await getBackend().updateMe(token, { nickname: body.nickname }))
  })
}
