import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { MyVideo } from '@/server/backend'
import MyVideos from './MyVideos'

/**
 * 🔴 그물 밖으로 나가는 것(S3 · 우리 API)만 대역으로 세운다. 거르는 규칙
 * (`checkClip`)은 진짜를 쓴다 — 그게 이 화면이 지켜야 하는 것이다.
 */
const uploadClip = vi.hoisted(() => vi.fn())
vi.mock('@/lib/uploadClip', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/lib/uploadClip')>()),
  uploadClip,
}))

const analyzed: MyVideo = {
  id: 'v1',
  sport_code: 'football',
  storage_key: '/coach-c002.mp4',
  duration_ms: 13000,
  side: null,
  created_at: '2026-09-03T09:00:00Z',
  passed: true,
  reject_reason: null,
  analysis_job_id: 'j1',
  analysis_status: 'succeeded',
  is_featured: false,
  is_public: false,
  title: null,
  description: null,
}
const uploaded: MyVideo = {
  ...analyzed,
  id: 'v3',
  storage_key: '/coach-c003.mp4',
  analysis_job_id: null,
  analysis_status: null,
}

/** 파일을 고르고 크기를 잰 것까지 — jsdom 은 영상 메타를 스스로 안 읽는다. */
async function pick(file: File, size = { w: 1920, h: 1080, dur: 10.2 }) {
  const user = userEvent.setup()
  await user.upload(screen.getByLabelText('올릴 영상') as HTMLInputElement, file)
  const el = document.querySelector('video[data-picked]') as HTMLVideoElement | null
  if (el) {
    Object.defineProperty(el, 'videoWidth', { value: size.w, configurable: true })
    Object.defineProperty(el, 'videoHeight', { value: size.h, configurable: true })
    Object.defineProperty(el, 'duration', { value: size.dur, configurable: true })
    fireEvent.loadedMetadata(el)
  }
  return user
}

const mp4 = () => new File(['x'], 'clip.mp4', { type: 'video/mp4' })

beforeEach(() => {
  localStorage.clear()
  uploadClip.mockReset()
})

describe('내 영상 — 올리기', () => {
  it('올릴 자리가 있다', () => {
    render(<MyVideos videos={[analyzed, uploaded]} />)
    expect(screen.getByLabelText('올릴 영상')).toBeInTheDocument()
  })

  // 🔴 형식·용량은 upload-url 이 422 로 튕겨 아무 데도 안 남는다 — 미리 막는다.
  it('받지 않는 형식은 올리지 않고 사유를 보여준다', async () => {
    render(<MyVideos videos={[analyzed, uploaded]} />)
    await pick(new File(['x'], 'clip.webm', { type: 'video/webm' }))
    expect(await screen.findByText(/형식/)).toBeInTheDocument()
    expect(uploadClip).not.toHaveBeenCalled()
  })

  // 🔴 기본값을 축구로 박아 두면 야구 영상이 축구 루브릭으로 조용히 채점된다
  // (분석 화면과 같은 판단이다).
  it('종목을 고르기 전에는 올리지 않는다', async () => {
    render(<MyVideos videos={[analyzed, uploaded]} />)
    await pick(mp4())
    expect(screen.getByRole('group', { name: '종목' })).toBeInTheDocument()
    expect(uploadClip).not.toHaveBeenCalled()
  })

  it('종목을 고르면 분석을 안 걸고 올린다', async () => {
    uploadClip.mockResolvedValue({ ...uploaded, id: 'v9' })
    render(<MyVideos videos={[analyzed, uploaded]} />)
    const user = await pick(mp4())
    await user.click(screen.getByRole('button', { name: '축구' }))
    await waitFor(() => expect(uploadClip).toHaveBeenCalled())
    expect(uploadClip.mock.calls[0][0]).toMatchObject({
      sportCode: 'football',
      analyze: false,
      meta: { duration_ms: 10200, width: 1920, height: 1080 },
    })
  })

  /**
   * 🔴 계약이 아직 `analyze` 를 모른다. 백엔드가 그걸 무시하고 분석을 걸어
   * 버리면 **화면도 그렇게 말해야 한다** — 보낸 뜻이 아니라 돌아온 응답을 믿는다.
   */
  it('분석이 걸려 돌아오면 분석 영상 쪽에 넣는다', async () => {
    uploadClip.mockResolvedValue({ ...uploaded, id: 'v9', analysis_job_id: 'j9', analysis_status: 'queued' })
    render(<MyVideos videos={[analyzed, uploaded]} />)
    const user = await pick(mp4())
    await user.click(screen.getByRole('button', { name: '축구' }))
    // 알약에 편수를 안 적으므로(사용자 요청) 갈래가 갈렸는지는 **어느 알약이
    // 골라졌는지**와 영상 아래 `1 / N` 으로 본다.
    await waitFor(() =>
      expect(screen.getByRole('tab', { name: '분석 영상' })).toHaveAttribute(
        'aria-selected',
        'true',
      ),
    )
    expect(screen.getByText('1 / 2')).toBeInTheDocument()
  })

  it('올린 것은 업로드 영상 쪽에 늘어난다', async () => {
    uploadClip.mockResolvedValue({ ...uploaded, id: 'v9' })
    render(<MyVideos videos={[analyzed, uploaded]} />)
    const user = await pick(mp4())
    await user.click(screen.getByRole('button', { name: '축구' }))
    await waitFor(() =>
      expect(screen.getByRole('tab', { name: '업로드 영상' })).toHaveAttribute(
        'aria-selected',
        'true',
      ),
    )
    expect(screen.getByText('1 / 2')).toBeInTheDocument()
  })

  // 🔴 반려는 실패가 아니다(201). 사유가 화면에 남아야 SFR-001 이 성립한다.
  it('규격 반려면 사유를 보여준다', async () => {
    uploadClip.mockResolvedValue({
      ...uploaded,
      id: 'v9',
      passed: false,
      reject_reason: '길이가 상한을 넘습니다',
    })
    render(<MyVideos videos={[analyzed, uploaded]} />)
    const user = await pick(mp4())
    await user.click(screen.getByRole('button', { name: '축구' }))
    expect(await screen.findByText('길이가 상한을 넘습니다')).toBeInTheDocument()
  })
})

describe('내 영상 — 공개 여부', () => {
  // 분석을 건 영상은 공개 대상이 아니다 — 영상 모음은 올린 장면을 훑는 자리다.
  it('분석 영상에는 공개 토글이 없다', () => {
    render(<MyVideos videos={[analyzed, uploaded]} />)
    expect(screen.queryByRole('button', { name: /공개/ })).toBeNull()
  })

  it('업로드 영상에는 공개 토글이 있다', async () => {
    const user = userEvent.setup()
    render(<MyVideos videos={[analyzed, uploaded]} />)
    await user.click(screen.getByRole('tab', { name: /업로드 영상/ }))
    expect(screen.getByRole('button', { name: /공개/ })).toBeInTheDocument()
  })

  /**
   * 🔴 **공개는 2026-09-10 부터 서버가 쥔다**(CCC 20, 미결 `paik` 5번).
   * 그전에는 브라우저 저장소라 다른 기기에서도 남에게도 안 보였다 — 그래서
   * 여기서도 저장소가 아니라 **무엇이 PATCH 로 나갔는지**를 붙든다.
   */
  function server(over: Record<string, unknown> = {}) {
    const fn = vi.fn().mockImplementation((_url: string, init?: RequestInit) => {
      const body = init?.body ? JSON.parse(String(init.body)) : {}
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({ ...uploaded, ...body, ...over }),
      })
    })
    vi.stubGlobal('fetch', fn)
    return fn
  }
  const patches = (fn: ReturnType<typeof vi.fn>) =>
    fn.mock.calls.filter((c) => c[1]?.method === 'PATCH')

  it('공개로 켜면 제목과 한 줄 설명을 묻는다', async () => {
    const fn = server()
    const user = userEvent.setup()
    render(<MyVideos videos={[analyzed, uploaded]} />)
    await user.click(screen.getByRole('tab', { name: /업로드 영상/ }))
    await user.click(screen.getByRole('button', { name: /공개/ }))
    expect(screen.getByLabelText('제목')).toBeInTheDocument()
    expect(screen.getByLabelText('한 줄 설명')).toBeInTheDocument()
    // 아직 아무것도 안 나갔다 — 적어야 올라간다.
    expect(patches(fn)).toEqual([])
  })

  /* 🔴 **한 번에 보낸다.** 「공개로 돌리고 → 제목을 단다」 두 번으로 나누면
     그 사이에 끊겼을 때 이름 없는 영상이 남에게 보인다. */
  it('제목을 적고 저장하면 공개와 제목이 한 번에 나간다', async () => {
    const fn = server()
    const user = userEvent.setup()
    render(<MyVideos videos={[analyzed, uploaded]} />)
    await user.click(screen.getByRole('tab', { name: /업로드 영상/ }))
    await user.click(screen.getByRole('button', { name: /공개/ }))
    await user.type(screen.getByLabelText('제목'), '농구 연습')
    await user.type(screen.getByLabelText('한 줄 설명'), '디딤발')
    await user.click(screen.getByRole('button', { name: '공개하기' }))

    await waitFor(() => expect(patches(fn)).toHaveLength(1))
    const [url, init] = patches(fn)[0]
    expect(url).toBe('/api/videos/v3')
    expect(JSON.parse(init.body)).toEqual({
      is_public: true,
      title: '농구 연습',
      description: '디딤발',
    })
  })

  // 🔴 제목이 없으면 영상 모음에서 이름 없는 칸이 된다.
  it('제목이 비어 있으면 공개하지 못한다', async () => {
    server()
    const user = userEvent.setup()
    render(<MyVideos videos={[analyzed, uploaded]} />)
    await user.click(screen.getByRole('tab', { name: /업로드 영상/ }))
    await user.click(screen.getByRole('button', { name: /공개/ }))
    expect(screen.getByRole('button', { name: '공개하기' })).toBeDisabled()
  })

  /* 🔴 **제목을 같이 지우지 않는다** — 부분 수정이라 다시 공개할 때 적어 둔
     이름이 살아 있다. */
  it('다시 누르면 공개만 내린다', async () => {
    const fn = server()
    const user = userEvent.setup()
    render(<MyVideos videos={[analyzed, { ...uploaded, is_public: true }]} />)
    await user.click(screen.getByRole('tab', { name: /업로드 영상/ }))
    expect(screen.getByRole('button', { name: /공개 중/ })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /공개 중/ }))
    await waitFor(() => expect(patches(fn)).toHaveLength(1))
    expect(JSON.parse(patches(fn)[0][1].body)).toEqual({ is_public: false })
  })

  /* 🔴 **서버가 바꾼 뒤에야 화면을 바꾼다.** 먼저 내리고 나중에 부르면,
     실패했을 때 비공개로 보이는데 실제로는 남에게 계속 보인다. */
  it('서버가 거절하면 공개 중인 채로 남고 사유가 뜬다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ error: { code: 'VIDEO_NOT_FOUND', message: '없는 영상입니다.' } }),
      }),
    )
    const user = userEvent.setup()
    render(<MyVideos videos={[analyzed, { ...uploaded, is_public: true }]} />)
    await user.click(screen.getByRole('tab', { name: /업로드 영상/ }))
    await user.click(screen.getByRole('button', { name: /공개 중/ }))

    expect(await screen.findByText('없는 영상입니다.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /공개 중/ })).toBeInTheDocument()
  })

  /* 🔴 **정본은 서버의 `is_public` 이다** — 목록이 그렇다고 하면 열자마자
     공개 중으로 그린다. */
  it('서버가 공개라고 한 클립은 열자마자 공개 중이다', async () => {
    const user = userEvent.setup()
    render(<MyVideos videos={[analyzed, { ...uploaded, is_public: true }]} />)
    await user.click(screen.getByRole('tab', { name: /업로드 영상/ }))
    expect(screen.getByRole('button', { name: /공개 중/ })).toBeInTheDocument()
  })

  // 무엇이 일어나는지 누르기 전에 말한다 — 되돌릴 수 있지만 그 사이에 남이 본다.
  it('남에게 보인다는 것을 적어 둔다', async () => {
    server()
    const user = userEvent.setup()
    render(<MyVideos videos={[analyzed, uploaded]} />)
    await user.click(screen.getByRole('tab', { name: /업로드 영상/ }))
    await user.click(screen.getByRole('button', { name: /공개/ }))
    expect(screen.getByText(/다른 사람에게도 보입니다/)).toBeInTheDocument()
  })
})

describe('내 영상 — 나를 보여주는 대표 영상', () => {
  const btn = () => screen.getByRole('button', { name: /나를 보여주는 대표 영상/ })
  /** PATCH 한 그대로 돌려주는 서버 대역 — 계약이 「바뀐 한 줄」을 준다. */
  function server() {
    const fn = vi.fn().mockImplementation((_url: string, init?: RequestInit) => {
      const body = init?.body ? JSON.parse(String(init.body)) : {}
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({ ...analyzed, is_featured: body.is_featured }),
      })
    })
    vi.stubGlobal('fetch', fn)
    return fn
  }

  afterEach(() => vi.unstubAllGlobals())

  it('세우면 계약대로 PATCH 하고 눌린 상태로 남는다', async () => {
    const fn = server()
    const user = userEvent.setup()
    render(<MyVideos videos={[analyzed]} />)
    expect(btn()).toHaveAttribute('aria-pressed', 'false')

    await user.click(btn())
    await waitFor(() => expect(btn()).toHaveAttribute('aria-pressed', 'true'))
    const [url, init] = fn.mock.calls.at(-1)!
    expect(url).toBe('/api/videos/v1')
    expect(init.method).toBe('PATCH')
    expect(JSON.parse(init.body)).toEqual({ is_featured: true })
  })

  // 🔴 대표가 둘이면 어느 것이 나를 보여주는지 정해지지 않는다.
  it('같은 영상을 다시 누르면 풀린다', async () => {
    const fn = server()
    const user = userEvent.setup()
    render(<MyVideos videos={[analyzed]} />)
    await user.click(btn())
    await waitFor(() => expect(btn()).toHaveAttribute('aria-pressed', 'true'))
    await user.click(btn())
    await waitFor(() => expect(btn()).toHaveAttribute('aria-pressed', 'false'))
    expect(JSON.parse(fn.mock.calls.at(-1)![1].body)).toEqual({ is_featured: false })
  })

  /* 🔴 **정본은 서버의 `is_featured` 다.** 브라우저에 남은 것을 읽던 때와
     갈리는 자리라, 목록이 그렇다고 하면 세워진 채로 열려야 한다. */
  it('서버가 대표라고 한 클립은 열자마자 눌려 있다', async () => {
    render(<MyVideos videos={[{ ...analyzed, is_featured: true }]} />)
    expect(btn()).toHaveAttribute('aria-pressed', 'true')
  })

  /* 🔴 **서버가 바꾼 뒤에야 화면이 바뀐다.** 반려된 클립을 세우려 하면
     422 `CANNOT_FEATURE` 인데, 먼저 눌러 두면 세워진 것처럼 보인다. */
  it('서버가 거절하면 안 눌리고 사유가 뜬다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 422,
        json: async () => ({ error: { code: 'CANNOT_FEATURE', message: '반려된 클립입니다.' } }),
      }),
    )
    const user = userEvent.setup()
    render(<MyVideos videos={[analyzed]} />)
    await user.click(btn())
    expect(await screen.findByText('반려된 클립입니다.')).toBeInTheDocument()
    expect(btn()).toHaveAttribute('aria-pressed', 'false')
  })

  // ⚠️ 반려된 클립은 서버가 안 보는 영상이라 대표가 될 수 없다.
  it('반려된 클립에는 안 낸다', () => {
    render(<MyVideos videos={[{ ...analyzed, passed: false, reject_reason: '길이 초과' }]} />)
    expect(screen.queryByRole('button', { name: /나를 보여주는 대표 영상/ })).toBeNull()
  })
})

describe('내 영상 — 분석 리포트', () => {
  /**
   * 🔴 **리포트는 2026-09-10 부터 서버가 쥔다**(CCC 31, 미결 `paik` 7번 ·
   * `jin` 27번). 그전에는 화면이 만든 자리 표시를 `localStorage` 에 둔 것이라
   * 다른 기기에서는 안 보였고 애초에 진짜 분석 결과가 아니었다 — 그래서 여기
   * 시험도 저장소가 아니라 **서버 응답**을 세운다.
   */
  const SERVER_REPORT = {
    video_id: 'v1',
    analyzed_at: '2026-09-03T09:00:00Z',
    summary: '디딤발이 공보다 앞서 있습니다.',
    provisional: true,
    breakdown: [
      {
        criterion_id: 'plant_foot_position',
        name: '디딤발 위치',
        grade: 2,
        title: '첫 리포트',
        evidence: '측면으로 벌리는 움직임이 많습니다',
        metric_ref: 'plant_foot_offset',
        skipped: false,
      },
    ],
    scenes: [{ metric_code: 'plant_frame', label: '디딤발 착지', at_seconds: 4 }],
    previews: null,
    keypoint_quality: null,
  }

  afterEach(() => vi.unstubAllGlobals())

  /** `/report` 만 골라 답한다 — 다른 호출(재생 주소 등)은 그대로 통과시킨다. */
  function stubReport(res: { ok: boolean; body?: unknown; status?: number }) {
    const fn = vi.fn().mockImplementation((url: string) =>
      Promise.resolve(
        String(url).endsWith('/report')
          ? { ok: res.ok, status: res.status ?? (res.ok ? 200 : 404), json: async () => res.body }
          : { ok: true, status: 200, json: async () => ({}) },
      ),
    )
    vi.stubGlobal('fetch', fn)
    return fn
  }

  it('서버가 준 리포트를 영상 목록 아래에 그린다', async () => {
    stubReport({ ok: true, body: SERVER_REPORT })
    render(<MyVideos videos={[analyzed]} />)

    expect(await screen.findByRole('region', { name: '분석 리포트' })).toBeInTheDocument()
    expect(screen.getByText(/디딤발이 공보다 앞서/)).toBeInTheDocument()
    expect(screen.getByText('디딤발 착지')).toBeInTheDocument()
    // 분석한 날은 서버의 `analyzed_at` 이다 — 「남긴 날」이 아니다.
    expect(screen.getByText(/2026-09-03 에 분석했습니다/)).toBeInTheDocument()
  })

  /* 🔴 **「아직」과 「없다」는 다르다**(미결 `paik` 7번의 「하지 말 것」) —
     분석 중인 클립에 빈 자리를 보이면 결과가 없는 것으로 읽힌다. */
  it('아직 적재 전이면 분석 중이라고 말한다', async () => {
    stubReport({ ok: false, body: { error: { code: 'REPORT_NOT_READY', message: '아직입니다.' } } })
    render(<MyVideos videos={[analyzed]} />)

    expect(await screen.findByText(/분석 중입니다/)).toBeInTheDocument()
    expect(screen.queryByText(/디딤발이 공보다 앞서/)).toBeNull()
  })

  // 🔴 그냥 올린 영상에는 리포트가 없다 — 갈래가 다르다.
  it('업로드 갈래에서는 안 그린다', async () => {
    stubReport({ ok: true, body: SERVER_REPORT })
    const user = userEvent.setup()
    render(<MyVideos videos={[analyzed, uploaded]} />)
    await user.click(screen.getByRole('tab', { name: '업로드 영상' }))
    expect(screen.queryByRole('region', { name: '분석 리포트' })).toBeNull()
  })

  // 🔴 수치를 그리지 않는 원칙은 이 자리에서도 같다(부록 D.5 · 계약 3장 4).
  it('점수 · 등급 · 별점을 그리지 않는다', async () => {
    stubReport({ ok: true, body: SERVER_REPORT })
    const { container } = render(<MyVideos videos={[analyzed]} />)
    await screen.findByRole('region', { name: '분석 리포트' })
    const text = container.textContent ?? ''
    expect(text).not.toMatch(/\d+\s*점/)
    expect(text).not.toMatch(/등급/)
    expect(text).not.toMatch(/★/)
    expect(container.querySelector('progress')).toBeNull()
    expect(container.querySelector('meter')).toBeNull()
  })
})

describe('내 영상 — 지우기', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    globalThis.localStorage?.clear()
  })

  function stubFetch(res: { ok: boolean; body?: unknown; status?: number }) {
    const fn = vi.fn().mockResolvedValue({
      ok: res.ok,
      status: res.status ?? (res.ok ? 204 : 404),
      json: async () => res.body ?? null,
    })
    vi.stubGlobal('fetch', fn)
    return fn
  }

  /**
   * 🔴 **리포트 읽기는 셈에서 뺀다.** 화면은 영상을 고를 때마다
   * `GET /videos/{id}/report` 를 부른다(2026-09-10, CCC 31) — 「지우기를
   * 안 불렀다」를 보려는 시험이 그것까지 세면 늘 실패한다.
   */
  const notReport = (fn: ReturnType<typeof vi.fn>) =>
    fn.mock.calls.filter((c) => !String(c[0]).endsWith('/report'))

  it('곧바로 안 지운다 — 한 번 더 묻는다', async () => {
    const user = userEvent.setup()
    const fn = stubFetch({ ok: true })
    render(<MyVideos videos={[analyzed]} />)

    await user.click(screen.getByRole('button', { name: /삭제/ }))
    expect(notReport(fn)).toHaveLength(0)
    expect(screen.getByRole('button', { name: '정말 지웁니다' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '취소' })).toBeInTheDocument()
  })

  it('취소하면 아무 일도 없다', async () => {
    const user = userEvent.setup()
    const fn = stubFetch({ ok: true })
    render(<MyVideos videos={[analyzed]} />)

    await user.click(screen.getByRole('button', { name: /삭제/ }))
    await user.click(screen.getByRole('button', { name: '취소' }))
    expect(notReport(fn)).toHaveLength(0)
    expect(screen.getByRole('button', { name: /삭제/ })).toBeInTheDocument()
  })

  it('확인하면 그 영상만 지우도록 부르고 목록에서 뺀다', async () => {
    const user = userEvent.setup()
    const fn = stubFetch({ ok: true })
    render(<MyVideos videos={[analyzed]} />)

    await user.click(screen.getByRole('button', { name: /삭제/ }))
    await user.click(screen.getByRole('button', { name: '정말 지웁니다' }))

    await waitFor(() => expect(notReport(fn)).toHaveLength(1))
    /* 🔴 **지운 영상에 PATCH 를 더 쏘지 않는다.** 대표·공개는 클립의 성질이라
       클립이 사라지면서 같이 없어진다 — 따로 내리려 하면 404 다(CCC 20 · 27). */
    expect(notReport(fn)[0][0]).toBe('/api/videos/v1')
    expect(notReport(fn)[0][1]).toMatchObject({ method: 'DELETE' })
    await waitFor(() =>
      expect(screen.getByText('아직 분석한 영상이 없습니다.')).toBeInTheDocument(),
    )
  })

  it('서버가 못 지우면 사유를 띄우고 영상은 그대로 둔다', async () => {
    const user = userEvent.setup()
    stubFetch({
      ok: false,
      status: 404,
      body: { error: { code: 'VIDEO_NOT_FOUND', message: '그 영상을 찾을 수 없습니다.' } },
    })
    render(<MyVideos videos={[analyzed]} />)

    await user.click(screen.getByRole('button', { name: /삭제/ }))
    await user.click(screen.getByRole('button', { name: '정말 지웁니다' }))

    await waitFor(() =>
      expect(screen.getByText('그 영상을 찾을 수 없습니다.')).toBeInTheDocument(),
    )
    // 🔴 사라진 것처럼 보이면 안 된다 — 서버에는 아직 있다.
    expect(screen.queryByText('아직 분석한 영상이 없습니다.')).not.toBeInTheDocument()
  })

  /* 🔴 **리포트를 따로 거두던 시험이 여기 있었다.** 2026-09-10 에 리포트가
     서버로 옮겨 가면서(CCC 31) 화면이 지울 것이 없어졌다 — 영상이 사라지면
     리포트도 함께 사라진다. 되살리지 않는다. */
})

/**
 * 🔴 **저장 키는 재생 주소가 아니다.** 계약이 주는 것은 `videos/<user_id>/…`
 * 라 그대로 `<video src>` 에 넣으면 403 이고, 그래서 배포에서 플레이어가 아예
 * 안 그려졌다(미결 paik 12번). 이제 `GET /videos/{id}/playback-url` 로 사전
 * 서명 주소를 따로 받는다.
 *
 * ⚠️ **mock 은 이 경로를 안 탄다** — `public/` 안의 진짜 파일을 저장 키로 주기
 * 때문에 `/` 로 시작하고, 그건 이미 주소다. 그래서 실물과 같은 모양의 클립을
 * 여기서 만들어 그 갈래를 붙든다.
 */
describe('내 영상 — 재생 주소', () => {
  const onServer: MyVideo = { ...analyzed, id: 'sv1', storage_key: 'videos/u1/abc.mp4' }

  afterEach(() => vi.unstubAllGlobals())

  it('저장 키가 서버 것이면 재생 주소를 받아서 튼다', async () => {
    const fn = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ url: 'https://s3.example.com/abc.mp4?sig=1', expires_in: 900 }),
    })
    vi.stubGlobal('fetch', fn)
    render(<MyVideos videos={[onServer]} />)

    await waitFor(() => expect(fn).toHaveBeenCalledWith('/api/videos/sv1/playback-url'))
    await waitFor(() =>
      expect(document.querySelector('.ss-profile-video-player')).toHaveAttribute(
        'src',
        'https://s3.example.com/abc.mp4?sig=1',
      ),
    )
  })

  /* 🔴 못 받아도 화면은 돌아야 한다 — 그 클립만 플레이어 없이 그려진다.
     예전처럼 판이 통째로 무너지면 안 된다. */
  it('주소를 못 받으면 플레이어만 없고 화면은 산다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => null }))
    render(<MyVideos videos={[onServer]} />)

    await waitFor(() => expect(screen.getByRole('button', { name: /삭제/ })).toBeInTheDocument())
    expect(document.querySelector('.ss-profile-video-player')).toBeNull()
  })

  // `/` 로 시작하는 키(mock)는 이미 주소다 — 그물 밖으로 나가면 안 된다.
  it('목업 키는 그대로 쓰고 서버를 안 부른다', async () => {
    const fn = vi.fn()
    vi.stubGlobal('fetch', fn)
    render(<MyVideos videos={[analyzed]} />)

    await waitFor(() =>
      expect(document.querySelector('.ss-profile-video-player')).toHaveAttribute(
        'src',
        '/coach-c002.mp4',
      ),
    )
    // 리포트 읽기는 별개다 — 재생 주소를 안 불렀다는 것만 본다.
    expect(fn.mock.calls.filter((c) => !String(c[0]).endsWith('/report'))).toHaveLength(0)
  })
})

