import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'
import { clearSession } from '@/server/session'

/**
 * 비밀번호 변경 — `PATCH /api/v1/me/password` (api-contract.md 2장).
 *
 * 🔴 **성공하면 기존 토큰이 전부 무효가 된다**(SEC-004). 지금 쓰던 토큰도
 * 포함이라, 화면은 204 를 받으면 다시 로그인시켜야 한다. 여기서 세션 쿠키까지
 * 함께 지운다 — 안 지우면 브라우저에 죽은 토큰이 남아, 다음 요청마다 401 을
 * 받고서야 로그인으로 밀려난다.
 *
 * 현재 비밀번호를 함께 받는 이유는 토큰만으로 바꿀 수 있으면 토큰을 훔친 쪽이
 * 주인을 밀어낼 수 있어서다(계약 2장).
 */
export async function PATCH(req: NextRequest) {
  return withAuth(req, async (token) => {
    let body: { current_password?: unknown; new_password?: unknown }
    try {
      body = await req.json()
    } catch {
      return NextResponse.json(
        { error: { code: 'BAD_REQUEST', message: '요청 형식이 잘못되었습니다.' } },
        { status: 400 },
      )
    }
    if (typeof body.current_password !== 'string' || typeof body.new_password !== 'string') {
      return NextResponse.json(
        {
          error: {
            code: 'VALIDATION_ERROR',
            message: '현재 비밀번호와 새 비밀번호가 필요합니다.',
          },
        },
        { status: 422 },
      )
    }

    await getBackend().changePassword(token, {
      current_password: body.current_password,
      new_password: body.new_password,
    })

    return clearSession(new NextResponse(null, { status: 204 }))
  })
}
