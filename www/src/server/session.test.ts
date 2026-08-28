import { NextRequest, NextResponse } from 'next/server'
import { SESSION_COOKIE, clearSession, readToken, setSession } from './session'

describe('세션 쿠키', () => {
  it('요청에서 토큰을 읽는다', () => {
    const req = new NextRequest('https://supersub-ai.com/api/me')
    req.cookies.set(SESSION_COOKIE, 'tok-1')
    expect(readToken(req)).toBe('tok-1')
  })

  it('쿠키가 없으면 null 이다', () => {
    const req = new NextRequest('https://supersub-ai.com/api/me')
    expect(readToken(req)).toBeNull()
  })

  it('httpOnly 로 심는다 — JS 가 읽지 못해야 한다', () => {
    const res = setSession(NextResponse.json({ ok: true }), 'tok-1', 604800)
    const c = res.cookies.get(SESSION_COOKIE)
    expect(c?.value).toBe('tok-1')
    expect(c?.httpOnly).toBe(true)
    expect(c?.sameSite).toBe('lax')
    expect(c?.maxAge).toBe(604800)
  })

  it('로그아웃하면 만료시킨다', () => {
    const res = clearSession(NextResponse.json({ ok: true }))
    expect(res.cookies.get(SESSION_COOKIE)?.maxAge).toBe(0)
  })
})
