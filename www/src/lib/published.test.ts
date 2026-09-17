import type { MyVideo } from '@/server/backend'
import { isPublished, listPublished, publish, unpublish } from './published'

/**
 * **공개로 돌린 클립** — CCC 20, 미결 `paik` 5번.
 *
 * 🔴 2026-09-10 에 브라우저 저장소를 걷어냈다. 그전에는 그 브라우저에만
 * 남아서 **다른 기기에서도 남에게도 안 보였다** — 「공개」가 성립하지
 * 않는 상태였다. 그래서 이 시험들은 저장소가 아니라 **계약**을 붙든다.
 */
const video = (over: Partial<MyVideo> = {}): MyVideo => ({
  id: 'v3',
  sport_code: 'football',
  storage_key: 'videos/u1/abc.mp4',
  duration_ms: 15600,
  side: null,
  created_at: '2026-09-04T11:05:00Z',
  passed: true,
  reject_reason: null,
  analysis_job_id: null,
  analysis_status: null,
  is_featured: false,
  is_public: false,
  title: null,
  description: null,
  ...over,
})

function stub(res: Partial<Response> & { json: () => Promise<unknown> }) {
  const fn = vi.fn().mockResolvedValue({ ok: true, status: 200, ...res })
  vi.stubGlobal('fetch', fn)
  return fn
}

const bodyOf = (fn: ReturnType<typeof vi.fn>) => JSON.parse(String(fn.mock.calls.at(-1)![1].body))

describe('공개 여부 — 정본은 서버다', () => {
  afterEach(() => vi.unstubAllGlobals())

  /* 🔴 화면이 따로 기억하지 않는다 — 내 목록의 그 줄이 정본이다. */
  it('목록의 is_public 을 그대로 읽는다', () => {
    expect(isPublished(video())).toBe(false)
    expect(isPublished(video({ is_public: true }))).toBe(true)
  })

  /* 🔴 **한 번에 보낸다.** 「공개로 돌리고 → 제목을 단다」 두 번으로 나누면
     그 사이에 끊겼을 때 이름 없는 영상이 남에게 보인다. */
  it('공개는 제목·설명과 함께 한 번에 나간다', async () => {
    const fn = stub({ json: async () => video({ is_public: true, title: '첫 골' }) })
    await publish('v3', { title: '첫 골', description: '왼발 감아차기' })

    expect(fn.mock.calls.at(-1)![0]).toBe('/api/videos/v3')
    expect(fn.mock.calls.at(-1)![1].method).toBe('PATCH')
    expect(bodyOf(fn)).toEqual({
      is_public: true,
      title: '첫 골',
      description: '왼발 감아차기',
    })
  })

  /* 🔴 **제목을 같이 지우지 않는다.** 부분 수정이라 안 보낸 것은 그대로 남고,
     다시 공개할 때 적어 둔 이름이 살아 있다. */
  it('공개를 풀 때 제목을 건드리지 않는다', async () => {
    const fn = stub({ json: async () => video() })
    await unpublish('v3')
    expect(bodyOf(fn)).toEqual({ is_public: false })
  })

  /* 서버가 거절하면(길이 초과 422 등) 사유를 그대로 올린다 — 삼켜서 "됐다"로
     그리면 다음에 열었을 때 공개가 안 돼 있다. */
  it('실패하면 서버가 준 사유로 던진다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 422,
        json: async () => ({ error: { code: 'VALIDATION_ERROR', message: '제목이 깁니다.' } }),
      }),
    )
    await expect(publish('v3', { title: 'x'.repeat(200), description: '' })).rejects.toThrow(
      '제목이 깁니다.',
    )
  })
})

describe('공개 클립 목록 — 남의 것까지', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('계약 경로에서 받아 온다', async () => {
    const fn = stub({ json: async () => [{ id: 'v1' }] })
    expect(await listPublished()).toEqual([{ id: 'v1' }])
    expect(fn.mock.calls.at(-1)![0]).toBe('/api/videos/public')
  })

  /* 🔴 **못 받으면 빈 배열이다.** 영상 모음은 붙박이 목록이 뒤를 받쳐 주므로
     (`lib/feed.ts`) 목록을 못 받았다고 화면이 비면 안 된다. */
  it('실패해도 화면이 죽지 않게 빈 목록으로 둔다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))
    expect(await listPublished()).toEqual([])
  })

  it('네트워크가 끊겨도 빈 목록으로 둔다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    expect(await listPublished()).toEqual([])
  })

  // 배열이 아닌 것이 와도 빈 목록으로 본다 — 프록시가 HTML 을 주는 경우까지.
  it('배열이 아니면 빈 목록으로 본다', async () => {
    stub({ json: async () => ({ a: 1 }) })
    expect(await listPublished()).toEqual([])
  })
})
