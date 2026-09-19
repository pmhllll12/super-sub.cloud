import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LoginPage from './page'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}))

describe('로그인 화면', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('이메일과 비밀번호 입력칸이 있다', () => {
    render(<LoginPage />)
    expect(screen.getByLabelText('이메일')).toBeInTheDocument()
    expect(screen.getByLabelText('비밀번호')).toBeInTheDocument()
  })

  it('실패하면 서버가 준 message 를 보여준다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              error: { code: 'INVALID_CREDENTIALS', message: '이메일 또는 비밀번호가 올바르지 않습니다.' },
            }),
            { status: 401 },
          ),
      ),
    )
    render(<LoginPage />)
    await userEvent.type(screen.getByLabelText('이메일'), 'a@b.com')
    await userEvent.type(screen.getByLabelText('비밀번호'), 'supersub2026')
    await userEvent.click(screen.getByRole('button', { name: '로그인' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      '이메일 또는 비밀번호가 올바르지 않습니다.',
    )
  })

  /**
   * 🔴 **429 뒤에는 같은 요청이 다시 안 나간다** — 계약 1번(SEC-009),
   * 미결 `jin` 2번. 창이 지나기 전에 다시 보내면 계속 거부되고 서버 자원만
   * 쓴다. 기다릴 시간은 **서버가 준 `Retry-After`** 다.
   */
  describe('요청이 너무 잦을 때(429)', () => {
    function limited(retryAfter: string | null) {
      const fn = vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              error: { code: 'TOO_MANY_REQUESTS', message: '요청이 너무 잦습니다.' },
            }),
            {
              status: 429,
              ...(retryAfter === null ? {} : { headers: { 'Retry-After': retryAfter } }),
            },
          ),
      )
      vi.stubGlobal('fetch', fn)
      return fn
    }

    async function submit() {
      await userEvent.type(screen.getByLabelText('이메일'), 'a@b.com')
      await userEvent.type(screen.getByLabelText('비밀번호'), 'supersub2026')
      await userEvent.click(screen.getByRole('button', { name: '로그인' }))
    }

    it('서버가 준 남은 시간을 그대로 보여준다', async () => {
      limited('37')
      render(<LoginPage />)
      await submit()
      // 🔴 임의의 상수(무조건 60초)가 아니라 그 시점에 남은 시간이다.
      expect(await screen.findByRole('alert')).toHaveTextContent('37초')
    })

    it('잠긴 동안 다시 눌러도 요청이 안 나간다', async () => {
      const fn = limited('37')
      render(<LoginPage />)
      await submit()
      await screen.findByRole('alert')
      expect(fn).toHaveBeenCalledTimes(1)

      await userEvent.click(screen.getByRole('button', { name: '로그인' }))
      expect(fn).toHaveBeenCalledTimes(1)
      expect(screen.getByRole('button', { name: '로그인' })).toBeDisabled()
    })

    /* 🔴 헤더가 중간에서 사라지는 일이 실제로 있었다(그걸 고치는 것이 이
       항목이다). 그때 0 으로 읽어 곧바로 풀리면 제한을 못 지킨다. */
    it('서버가 시간을 안 줘도 곧바로 풀리지 않는다', async () => {
      const fn = limited(null)
      render(<LoginPage />)
      await submit()
      await screen.findByRole('alert')

      await userEvent.click(screen.getByRole('button', { name: '로그인' }))
      expect(fn).toHaveBeenCalledTimes(1)
    })
  })
})

/**
 * **심사위원용 로그인** (사용자 요청, 2026-09-17) — 누르기만 하면 들어간다.
 *
 * 🔴 **세션을 가짜로 심지 않는다.** 그러면 `/home` 은 열려도 그 뒤 모든
 * 호출이 401 이다(세션 쿠키에 담기는 것이 백엔드 접근 토큰이다) — 빈 화면만
 * 본다. 대신 **계정을 단추가 알아서 챙긴다**: 로그인해 보고, 없으면 그 자리에서
 * 가입시킨 뒤 다시 로그인한다.
 */
describe('로그인 화면 — 심사위원용', () => {
  afterEach(() => vi.unstubAllGlobals())

  /** 보낸 요청을 모으고, `login` 이 실패할지 정한다. */
  function stub({ loginFails = 0 } = {}) {
    const calls: { url: string; body: unknown }[] = []
    let failsLeft = loginFails
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        const u = String(url)
        calls.push({ url: u, body: init?.body ? JSON.parse(String(init.body)) : null })
        if (u.endsWith('/api/auth/login') && failsLeft > 0) {
          failsLeft -= 1
          return new Response(
            JSON.stringify({ error: { code: 'INVALID_CREDENTIALS', message: '없는 계정' } }),
            { status: 401 },
          )
        }
        return new Response(JSON.stringify({ ok: true }), { status: 200 })
      }),
    )
    return calls
  }

  it('회원가입 아래에 단추가 있다', () => {
    render(<LoginPage />)
    expect(screen.getByRole('button', { name: '원티드 테스트용 로그인' })).toBeInTheDocument()
  })

  /* 계정이 이미 있으면 **가입을 안 부른다** — 한 번으로 끝난다. */
  it('계정이 있으면 바로 로그인한다', async () => {
    const calls = stub()
    render(<LoginPage />)

    await userEvent.click(screen.getByRole('button', { name: '원티드 테스트용 로그인' }))

    expect(calls.filter((c) => c.url.endsWith('/api/auth/login'))).toHaveLength(1)
    expect(calls.some((c) => c.url.endsWith('/api/auth/signup'))).toBe(false)
  })

  /**
   * 🔴 **이게 「누르기만 하면 된다」의 전부다.** 실서버에 누가 미리 계정을
   * 만들어 둘 필요가 없다 — 없으면 단추가 그 자리에서 만든다.
   */
  it('계정이 없으면 가입시키고 다시 로그인한다', async () => {
    const calls = stub({ loginFails: 1 })
    render(<LoginPage />)

    await userEvent.click(screen.getByRole('button', { name: '원티드 테스트용 로그인' }))

    expect(calls.some((c) => c.url.endsWith('/api/auth/signup'))).toBe(true)
    expect(calls.filter((c) => c.url.endsWith('/api/auth/login'))).toHaveLength(2)
  })

  /**
   * 🔴 **여느 로그인과 같은 경로로 나간다.** 우회용 경로를 새로 뚫으면 그것이
   * 곧 보안 구멍이다 — 이 단추가 하는 일은 값을 대신 적어 주는 것뿐이다.
   */
  it('여느 로그인과 같은 경로를 쓴다 — 우회 경로를 뚫지 않는다', async () => {
    const calls = stub()
    render(<LoginPage />)

    await userEvent.click(screen.getByRole('button', { name: '원티드 테스트용 로그인' }))

    const sent = calls.find((c) => c.url.endsWith('/api/auth/login'))!
    const body = sent.body as { email?: string; password?: string }
    expect(body.email).toBeTruthy()
    expect(body.password).toBeTruthy()
    /* 세션을 직접 심는 길이 없어야 한다. */
    expect(calls.some((c) => /session|token|bypass/i.test(c.url))).toBe(false)
  })

  /* 🔴 **실패를 숨기지 않는다** — 가입까지 막히면 여느 실패처럼 말한다. */
  it('가입도 로그인도 안 되면 이유를 적는다', async () => {
    stub({ loginFails: 99 })
    render(<LoginPage />)

    await userEvent.click(screen.getByRole('button', { name: '원티드 테스트용 로그인' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('없는 계정')
  })

  /**
   * **로고 위 한 줄** (사용자 요청, 2026-09-18).
   *
   * 🔴 **아래 것들은 안 건드린다** — 로고·안내 문구·입력칸·단추의 크기도
   * 간격도 그대로다. 로고 위가 원래 비어 있던 자리라 거기만 채운다.
   */
  it('로고 위에 한 줄이 붙는다', () => {
    render(<LoginPage />)
    expect(screen.getByText('AI가 완성하는 스포츠 라이프')).toBeInTheDocument()
  })

  /* 🔴 **한 줄에 못 박지 않는다** — 375px 에서 카드를 넘긴다. 한글 줄바꿈
     둘(`break-keep`·`text-pretty`)로 어절 단위로 접는다. */
  it('좁은 화면에서 넘치지 않게 줄바꿈을 허용한다', () => {
    render(<LoginPage />)
    const line = screen.getByText('AI가 완성하는 스포츠 라이프')
    expect(line.className).not.toContain('whitespace-nowrap')
    expect(line.className).toContain('break-keep')
  })
})
