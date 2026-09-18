import { uploadCardPhoto } from './cardPhoto'

/**
 * **카드 사진 올리기** (2026-09-18, 사용자 요청: "다른 이미지로 교체할 때
 * 실제로 저장하면 교체되어서 저장되게").
 *
 * 🔴 **두 단계**다 — 우리 서버에서 사전 서명 주소만 받고, 파일은 브라우저가
 * S3 에 직접 PUT 한다(PER-002). 사진이 우리 서버를 지나면 그 원칙이 깨진다.
 */
describe('카드 사진 올리기', () => {
  const file = new File([new Uint8Array([1, 2, 3])], 'me.png', { type: 'image/png' })

  function serve(putOk = true) {
    const calls: { url: string; method: string; contentType?: string }[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        const headers = (init?.headers ?? {}) as Record<string, string>
        calls.push({
          url,
          method: init?.method ?? 'GET',
          contentType: headers['Content-Type'],
        })
        if (url === '/api/me/card/photo-upload-url') {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              upload_url: 'https://s3.invalid/put/abc',
              storage_key: 'cards/photos/u1/c1-9f.png',
              expires_in: 900,
            }),
          })
        }
        return Promise.resolve({ ok: putOk })
      }),
    )
    return calls
  }

  beforeEach(() => {
    vi.stubGlobal('URL', { ...URL, createObjectURL: () => 'blob:preview' })
  })
  afterEach(() => vi.unstubAllGlobals())

  it('사전 서명 주소를 받아 S3 로 직접 올린다', async () => {
    const calls = serve()
    const made = await uploadCardPhoto(file)

    expect(calls[0].url).toBe('/api/me/card/photo-upload-url')
    expect(calls[1].url).toBe('https://s3.invalid/put/abc')
    expect(calls[1].method).toBe('PUT')
    expect(made.storageKey).toBe('cards/photos/u1/c1-9f.png')
  })

  /**
   * 🔴 **`Content-Type` 이 서명에 들어간다** — 자리를 받을 때 말한 값과
   * PUT 헤더가 **같아야** 하고, 다르면 S3 가 403 을 준다. 두 자리가 갈리기
   * 쉬워서 시험이 붙든다.
   */
  it('자리를 받을 때와 올릴 때의 형식이 같다', async () => {
    const calls = serve()
    await uploadCardPhoto(file)
    expect(calls[1].contentType).toBe('image/png')
  })

  /* 🔴 **투명한 그림은 PNG 로 둔다** — 「사람만 오려서」는 배경 없는 PNG 가
     요점이라, JPEG 로 바꾸면 투명한 자리가 검게 칠해진다. */
  it('PNG 를 JPEG 로 바꾸지 않는다', async () => {
    const calls = serve()
    await uploadCardPhoto(file)
    expect(calls[1].contentType).not.toBe('image/jpeg')
  })

  /* 🔴 **실패를 삼키지 않는다** — 조용히 넘어가면 사람은 사진이 바뀐 줄 알고
     저장까지 하는데 실제로는 옛 사진이 남는다. */
  it('S3 가 거절하면 던진다', async () => {
    serve(false)
    await expect(uploadCardPhoto(file)).rejects.toThrow()
  })

  it('자리를 못 받아도 던진다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }))
    await expect(uploadCardPhoto(file)).rejects.toThrow()
  })
})
