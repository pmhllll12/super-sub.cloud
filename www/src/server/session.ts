import type { NextRequest, NextResponse } from 'next/server'

export const SESSION_COOKIE = 'supersub_token'

export function readToken(req: NextRequest): string | null {
  return req.cookies.get(SESSION_COOKIE)?.value ?? null
}

/**
 * 액세스 토큰을 httpOnly 쿠키에 심는다.
 *
 * 계약서상 refresh 토큰이 없어서 액세스 토큰 하나가 전부다. localStorage 에
 * 두면 XSS 한 번에 통째로 새고 만료 전까지 되돌릴 방법이 없다.
 */
export function setSession(res: NextResponse, token: string, maxAge: number): NextResponse {
  res.cookies.set(SESSION_COOKIE, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge,
  })
  return res
}

export function clearSession(res: NextResponse): NextResponse {
  res.cookies.set(SESSION_COOKIE, '', {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: 0,
  })
  return res
}
