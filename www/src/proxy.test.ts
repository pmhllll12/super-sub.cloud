import type { NextRequest } from 'next/server'
import { config, proxy } from './proxy'
import { SESSION_COOKIE } from './server/session'

/** proxy 가 실제로 읽는 것만 갖춘 최소 NextRequest — nextUrl 과 cookies.get. */
function request(pathname: string, { token }: { token?: string } = {}) {
  return {
    nextUrl: new URL(`https://supersub-ai.com${pathname}`),
    cookies: {
      get: (name: string) =>
        name === SESSION_COOKIE && token ? { name, value: token } : undefined,
    },
  } as unknown as NextRequest
}

/** matcher 정규식이 이 경로에 걸리는가 — 걸리지 않으면 proxy 자체가 안 돈다. */
function matches(pathname: string) {
  return new RegExp(`^${config.matcher[0]}$`).test(pathname)
}

describe('proxy — 로그인 안 하면 아무 데도 못 들어간다', () => {
  it.each(['/', '/me', '/me/card', '/analysis', '/c/abc123'])(
    '쿠키가 없으면 %s 를 로그인 화면으로 보낸다',
    (path) => {
      const res = proxy(request(path))
      expect(res.status).toBe(307)
      expect(new URL(res.headers.get('location')!).pathname).toBe('/login')
    },
  )

  it('공유 링크(/c/{slug})도 예외가 아니다 — 쿼리를 달고 와도 로그인으로 보낸다', () => {
    const res = proxy(request('/c/abc123?from=kakao'))
    const location = new URL(res.headers.get('location')!)
    expect(location.pathname).toBe('/login')
    // 로그인 화면에 원래 쿼리를 끌고 가지 않는다.
    expect(location.search).toBe('')
  })

  it.each(['/login', '/signup'])('%s 는 로그인 없이 열린다 — 아니면 들어올 길이 없다', (path) => {
    expect(proxy(request(path)).headers.get('location')).toBeNull()
  })

  it('쿠키가 있으면 통과시킨다 — 토큰이 진짜 유효한지는 각 화면의 requireUser() 가 본다', () => {
    expect(proxy(request('/', { token: 'tok' })).headers.get('location')).toBeNull()
    expect(proxy(request('/c/abc123', { token: 'tok' })).headers.get('location')).toBeNull()
  })

  describe('matcher', () => {
    it.each(['/', '/me', '/c/abc123'])('%s 에는 걸린다', (path) => {
      expect(matches(path)).toBe(true)
    })

    // 여기 걸리면 로그인 화면 자신의 배경 사진이 로그인으로 리다이렉트되어
    // 안 뜬다. API 는 리다이렉트되면 fetch 가 로그인 HTML 을 받아 들고 깨진다.
    it.each([
      '/api/auth/login',
      '/api/me',
      '/_next/static/chunks/main.js',
      '/login_figure.jpg',
      '/home_figure.jpg',
      '/ink_field.png',
      '/favicon.ico',
    ])('%s 는 넘긴다', (path) => {
      expect(matches(path)).toBe(false)
    })
  })
})
