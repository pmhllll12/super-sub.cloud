import { ApiCallError, apiPost } from './client'

describe('apiPost', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('성공하면 본문을 돌려준다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
    )
    await expect(apiPost('/api/auth/logout', {})).resolves.toEqual({ ok: true })
  })

  it('실패하면 code 를 담은 에러를 던진다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({ error: { code: 'INVALID_CREDENTIALS', message: '틀렸습니다.' } }),
            { status: 401 },
          ),
      ),
    )
    await expect(apiPost('/api/auth/login', {})).rejects.toMatchObject({
      code: 'INVALID_CREDENTIALS',
      status: 401,
    })
  })

  it('네트워크가 끊기면 NETWORK_ERROR 다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('failed to fetch')
      }),
    )
    await expect(apiPost('/api/auth/login', {})).rejects.toBeInstanceOf(ApiCallError)
  })
})
