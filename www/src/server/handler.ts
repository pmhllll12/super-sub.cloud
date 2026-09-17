import { NextResponse, type NextRequest } from 'next/server'
import { BackendError, errorResponseBody } from '@/server/backend'
import { readToken } from '@/server/session'

/**
 * 계약 형태(`{error: {code, message}}`)로 바꿔 돌려준다.
 *
 * 🔴 **429 면 `Retry-After` 를 다시 실어 준다**(계약 1번). 이 자리가 프록시라,
 * 여기서 안 실으면 백엔드가 보낸 헤더가 **브라우저에 영영 안 닿는다** — 화면은
 * 얼마나 기다려야 하는지 알 수 없어 임의의 상수를 쓰게 된다.
 */
export function toErrorResponse(e: unknown): NextResponse {
  if (e instanceof BackendError) {
    return NextResponse.json(errorResponseBody(e), {
      status: e.status,
      ...(e.retryAfter !== undefined ? { headers: { 'Retry-After': String(e.retryAfter) } } : {}),
    })
  }
  throw e
}

export async function withAuth(
  req: NextRequest,
  fn: (token: string) => Promise<NextResponse>,
): Promise<NextResponse> {
  const token = readToken(req)
  if (!token) {
    return NextResponse.json(
      { error: { code: 'UNAUTHORIZED', message: '로그인이 필요합니다.' } },
      { status: 401 },
    )
  }
  try {
    return await fn(token)
  } catch (e) {
    return toErrorResponse(e)
  }
}
