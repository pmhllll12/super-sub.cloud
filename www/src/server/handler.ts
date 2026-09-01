import { NextResponse, type NextRequest } from 'next/server'
import { BackendError, errorResponseBody } from '@/server/backend'
import { readToken } from '@/server/session'

export function toErrorResponse(e: unknown): NextResponse {
  if (e instanceof BackendError) {
    return NextResponse.json(errorResponseBody(e), { status: e.status })
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
