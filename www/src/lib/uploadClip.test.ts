import { uploadClip, checkClip, LIMITS } from './uploadClip'

/**
 * 계약 3-6절(클립 업로드)을 화면 쪽에서 지키는지 본다.
 *
 * 🔴 미리 거르는 것은 **형식과 용량뿐**이다. 그 둘은 `upload-url` 이 422 로
 * 튕겨서 **아무 데도 안 남는다.** 길이·해상도는 반대로 서버가 `reject_reason`
 * 으로 남기는 것이고(SFR-001), 화면이 가로채면 그 사유가 사라진다.
 */
describe('checkClip — 올리기 전에 거르는 것', () => {
  const ok = { type: 'video/mp4', size: 1024 }

  it('상한 안의 mp4 는 통과한다', () => {
    expect(checkClip(ok)).toBeNull()
  })

  it('quicktime 도 통과한다', () => {
    expect(checkClip({ type: 'video/quicktime', size: 1024 })).toBeNull()
  })

  it('받지 않는 형식은 사유를 돌려준다', () => {
    expect(checkClip({ type: 'video/webm', size: 1024 })).toMatch(/형식/)
  })

  it('용량 상한을 넘으면 사유를 돌려준다', () => {
    expect(checkClip({ ...ok, size: LIMITS.bytes + 1 })).toMatch(/용량/)
  })

  // 🔴 길이·해상도는 여기서 안 본다 — 서버가 반려 사유로 남겨야 하는 것이다.
  it('긴 영상이라도 형식·용량이 맞으면 통과시킨다', () => {
    expect(checkClip(ok)).toBeNull()
  })
})

describe('uploadClip — 세 단계', () => {
  const file = new File(['x'], 'clip.mp4', { type: 'video/mp4' })
  const meta = { duration_ms: 10200, width: 1920, height: 1080 }

  function stubFetch(register: unknown) {
    const calls: { url: string; init?: RequestInit }[] = []
    const fetchStub = vi.fn(async (url: string, init?: RequestInit) => {
      calls.push({ url, init })
      if (url === '/api/videos/upload-url') {
        return new Response(
          JSON.stringify({ storage_key: 'videos/u/abc.mp4', upload_url: 'https://s3/put' }),
          { status: 200 },
        )
      }
      if (url === 'https://s3/put') return new Response(null, { status: 200 })
      return new Response(JSON.stringify(register), { status: 201 })
    })
    vi.stubGlobal('fetch', fetchStub)
    return calls
  }

  afterEach(() => vi.unstubAllGlobals())

  const passed = {
    id: 'v9',
    storage_key: 'videos/u/abc.mp4',
    passed: true,
    reject_reason: null,
    analysis_job_id: null,
    analysis_status: null,
  }

  it('자리를 받고 · S3 에 올리고 · 등록한다', async () => {
    const calls = stubFetch(passed)
    await uploadClip({ file, sportCode: 'football', meta })
    expect(calls.map((c) => c.url)).toEqual([
      '/api/videos/upload-url',
      'https://s3/put',
      '/api/videos',
    ])
  })

  // 🔴 서명에 Content-Type 이 들어 있어서 다르면 S3 가 거절한다(계약 3-6절).
  it('S3 에 PUT 할 때 요청한 Content-Type 을 그대로 보낸다', async () => {
    const calls = stubFetch(passed)
    await uploadClip({ file, sportCode: 'football', meta })
    const put = calls[1]
    expect(put.init?.method).toBe('PUT')
    expect((put.init?.headers as Record<string, string>)['Content-Type']).toBe('video/mp4')
  })

  it('등록 본문에 종목과 잰 값을 싣는다', async () => {
    const calls = stubFetch(passed)
    await uploadClip({ file, sportCode: 'football', meta })
    expect(JSON.parse(calls[2].init?.body as string)).toMatchObject({
      sport_code: 'football',
      storage_key: 'videos/u/abc.mp4',
      duration_ms: 10200,
      width: 1920,
      height: 1080,
    })
  })

  // 🔴 분석을 안 걸고 올리는 길. 계약이 아직 이 필드를 모르므로 **응답을
  // 그대로 믿는다** — 백엔드가 무시하고 분석을 걸면 analysis_job_id 가 채워져
  // 오고, 화면은 그걸 보고 「분석 영상」으로 넣는다.
  it('analyze: false 면 등록 본문에 실어 보낸다', async () => {
    const calls = stubFetch(passed)
    await uploadClip({ file, sportCode: 'football', meta, analyze: false })
    expect(JSON.parse(calls[2].init?.body as string).analyze).toBe(false)
  })

  // 🔴 반려는 실패가 아니라 201 이다(계약 3-6절). 예외로 만들면 사유가 화면까지
  // 못 온다 — 클라이언트는 status 가 아니라 passed 로 분기해야 한다.
  it('규격 반려를 예외로 만들지 않고 그대로 돌려준다', async () => {
    stubFetch({ ...passed, passed: false, reject_reason: '해상도가 상한을 넘습니다' })
    const result = await uploadClip({ file, sportCode: 'football', meta })
    expect(result.passed).toBe(false)
    expect(result.reject_reason).toBe('해상도가 상한을 넘습니다')
  })

  it('자리를 못 받으면 그 사유로 실패한다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(JSON.stringify({ error: { message: '용량이 너무 큽니다.' } }), {
            status: 422,
          }),
      ),
    )
    await expect(uploadClip({ file, sportCode: 'football', meta })).rejects.toThrow(
      '용량이 너무 큽니다.',
    )
  })
})
