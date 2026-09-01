import { NextResponse, type NextRequest } from 'next/server'
import { BackendError, errorResponseBody, getBackend } from '@/server/backend'

export async function POST(req: NextRequest) {
  let body: { email?: string; password?: string; nickname?: string }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json(
      { error: { code: 'BAD_REQUEST', message: '요청 형식이 잘못되었습니다.' } },
      { status: 400 },
    )
  }

  if (
    typeof body.email !== 'string' ||
    typeof body.password !== 'string' ||
    typeof body.nickname !== 'string'
  ) {
    return NextResponse.json(
      { error: { code: 'BAD_REQUEST', message: '이메일·비밀번호·닉네임이 필요합니다.' } },
      { status: 400 },
    )
  }

  try {
    const user = await getBackend().signup({
      email: body.email,
      password: body.password,
      nickname: body.nickname,
    })
    // 가입은 로그인이 아니다 — 세션을 심지 않는다. 화면이 로그인으로 보낸다.
    return NextResponse.json(user, { status: 201 })
  } catch (e) {
    if (e instanceof BackendError) {
      return NextResponse.json(errorResponseBody(e), { status: e.status })
    }
    throw e
  }
}
