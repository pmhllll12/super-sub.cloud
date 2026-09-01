import { NextResponse, type NextRequest } from 'next/server'
import { BackendError, errorResponseBody, getBackend } from '@/server/backend'
import { setSession } from '@/server/session'

export async function POST(req: NextRequest) {
  let body: { email?: string; password?: string }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json(
      { error: { code: 'BAD_REQUEST', message: '요청 형식이 잘못되었습니다.' } },
      { status: 400 },
    )
  }

  if (typeof body.email !== 'string' || typeof body.password !== 'string') {
    return NextResponse.json(
      { error: { code: 'BAD_REQUEST', message: '이메일과 비밀번호가 필요합니다.' } },
      { status: 400 },
    )
  }

  try {
    const token = await getBackend().login({ email: body.email, password: body.password })
    // 토큰은 본문에 담지 않는다. 쿠키로만 나간다.
    return setSession(NextResponse.json({ ok: true }), token.access_token, token.expires_in)
  } catch (e) {
    if (e instanceof BackendError) {
      return NextResponse.json(errorResponseBody(e), { status: e.status })
    }
    throw e
  }
}
