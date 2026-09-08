import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { MyVideo } from '@/server/backend'
import { listPublished } from '@/lib/published'
import { reportFor, saveReport } from '@/lib/savedReports'
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

  it('공개로 켜면 제목과 한 줄 설명을 묻는다', async () => {
    const user = userEvent.setup()
    render(<MyVideos videos={[analyzed, uploaded]} />)
    await user.click(screen.getByRole('tab', { name: /업로드 영상/ }))
    await user.click(screen.getByRole('button', { name: /공개/ }))
    expect(screen.getByLabelText('제목')).toBeInTheDocument()
    expect(screen.getByLabelText('한 줄 설명')).toBeInTheDocument()
    // 아직 공개된 것은 아니다 — 적어야 올라간다.
    expect(listPublished()).toEqual([])
  })

  it('제목을 적고 저장하면 공개 목록에 들어간다', async () => {
    const user = userEvent.setup()
    render(<MyVideos videos={[analyzed, uploaded]} />)
    await user.click(screen.getByRole('tab', { name: /업로드 영상/ }))
    await user.click(screen.getByRole('button', { name: /공개/ }))
    await user.type(screen.getByLabelText('제목'), '농구 연습')
    await user.type(screen.getByLabelText('한 줄 설명'), '디딤발')
    await user.click(screen.getByRole('button', { name: '공개하기' }))
    await waitFor(() => expect(listPublished()).toHaveLength(1))
    expect(listPublished()[0]).toMatchObject({
      id: 'v3',
      title: '농구 연습',
      what: '디딤발',
      src: '/coach-c003.mp4',
    })
  })

  // 🔴 제목이 없으면 영상 모음에서 이름 없는 칸이 된다.
  it('제목이 비어 있으면 공개하지 못한다', async () => {
    const user = userEvent.setup()
    render(<MyVideos videos={[analyzed, uploaded]} />)
    await user.click(screen.getByRole('tab', { name: /업로드 영상/ }))
    await user.click(screen.getByRole('button', { name: /공개/ }))
    expect(screen.getByRole('button', { name: '공개하기' })).toBeDisabled()
  })

  it('공개한 것을 다시 누르면 내린다', async () => {
    const user = userEvent.setup()
    render(<MyVideos videos={[analyzed, uploaded]} />)
    await user.click(screen.getByRole('tab', { name: /업로드 영상/ }))
    await user.click(screen.getByRole('button', { name: /공개/ }))
    await user.type(screen.getByLabelText('제목'), '농구 연습')
    await user.click(screen.getByRole('button', { name: '공개하기' }))
    await waitFor(() => expect(listPublished()).toHaveLength(1))
    await user.click(screen.getByRole('button', { name: /공개/ }))
    await waitFor(() => expect(listPublished()).toEqual([]))
  })

  // ⚠️ 서버 저장이 아니라는 것을 화면이 말해야 한다 — 다른 기기에서 안 보인다.
  it('이 브라우저에만 남는다는 것을 적어 둔다', async () => {
    const user = userEvent.setup()
    render(<MyVideos videos={[analyzed, uploaded]} />)
    await user.click(screen.getByRole('tab', { name: /업로드 영상/ }))
    await user.click(screen.getByRole('button', { name: /공개/ }))
    expect(screen.getByText(/이 브라우저에만/)).toBeInTheDocument()
  })
})

describe('내 영상 — 나를 보여주는 대표 영상', () => {
  const btn = () => screen.getByRole('button', { name: /나를 보여주는 대표 영상/ })

  it('영상마다 세울 수 있고, 세우면 눌린 상태로 남는다', async () => {
    const user = userEvent.setup()
    render(<MyVideos videos={[analyzed]} />)
    expect(btn()).toHaveAttribute('aria-pressed', 'false')

    await user.click(btn())
    expect(btn()).toHaveAttribute('aria-pressed', 'true')
    expect(JSON.parse(globalThis.localStorage.getItem('supersub.featured.v1')!).videoId).toBe('v1')
    // ⚠️ 어디에 남는지 밝힌다 — 계약에 자리가 없다.
    expect(screen.getByText(/이 브라우저에만/)).toBeInTheDocument()
  })

  // 🔴 대표가 둘이면 어느 것이 나를 보여주는지 정해지지 않는다.
  it('같은 영상을 다시 누르면 풀린다', async () => {
    const user = userEvent.setup()
    render(<MyVideos videos={[analyzed]} />)
    await user.click(btn())
    await user.click(btn())
    expect(btn()).toHaveAttribute('aria-pressed', 'false')
    expect(globalThis.localStorage.getItem('supersub.featured.v1')).toBeNull()
  })

  it('새로 그려도 세워 둔 것이 그대로다', async () => {
    const user = userEvent.setup()
    const { unmount } = render(<MyVideos videos={[analyzed]} />)
    await user.click(btn())
    unmount()

    render(<MyVideos videos={[analyzed]} />)
    expect(await screen.findByRole('button', { name: /나를 보여주는 대표 영상/ })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })

  // ⚠️ 반려된 클립은 서버가 안 보는 영상이라 대표가 될 수 없다.
  it('반려된 클립에는 안 낸다', () => {
    render(<MyVideos videos={[{ ...analyzed, passed: false, reject_reason: '길이 초과' }]} />)
    expect(screen.queryByRole('button', { name: /나를 보여주는 대표 영상/ })).toBeNull()
  })
})

describe('내 영상 — 분석 리포트', () => {
  const REPORT = {
    summary: '디딤발이 공보다 앞서 있습니다.',
    traits: ['측면으로 벌리는 움직임이 많습니다'],
    titles: ['첫 리포트'],
    scenes: [{ at: '0:04', what: '디딤발 착지' }],
  }

  beforeEach(() => globalThis.localStorage?.clear())

  it('저장해 둔 리포트가 있으면 영상 목록 아래에 그린다', async () => {
    saveReport('v1', REPORT)
    render(<MyVideos videos={[analyzed]} />)

    expect(await screen.findByRole('region', { name: '분석 리포트' })).toBeInTheDocument()
    expect(screen.getByText(/디딤발이 공보다 앞서/)).toBeInTheDocument()
    expect(screen.getByText('디딤발 착지')).toBeInTheDocument()
    // ⚠️ 어디에 남았는지 밝힌다 — 숨기면 다른 기기에서 안 보일 때 고장으로 읽힌다.
    expect(screen.getByText(/이 브라우저에만/)).toBeInTheDocument()
  })

  it('저장해 둔 것이 없으면 아무것도 안 그린다', () => {
    render(<MyVideos videos={[analyzed]} />)
    expect(screen.queryByRole('region', { name: '분석 리포트' })).toBeNull()
  })

  // 🔴 그냥 올린 영상에는 리포트가 없다 — 갈래가 다르다.
  it('업로드 갈래에서는 안 그린다', async () => {
    saveReport('v3', REPORT)
    const user = userEvent.setup()
    render(<MyVideos videos={[analyzed, uploaded]} />)
    await user.click(screen.getByRole('tab', { name: '업로드 영상' }))
    expect(screen.queryByRole('region', { name: '분석 리포트' })).toBeNull()
  })

  // 🔴 수치를 그리지 않는 원칙은 이 자리에서도 같다(부록 D.5 · 계약 3장 4).
  it('점수 · 등급 · 별점을 그리지 않는다', async () => {
    saveReport('v1', REPORT)
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

/**
 * 🔴 **지우기는 되돌릴 수 없다.** 그래서 이 넷이 다 지켜져야 한다:
 * 한 번 더 묻는가 · 서버가 지운 **뒤에야** 화면에서 빠지는가 · 실패하면
 * 남아 있는가 · 브라우저에만 있던 것(리포트 · 공개)까지 거두는가.
 */
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

  it('곧바로 안 지운다 — 한 번 더 묻는다', async () => {
    const user = userEvent.setup()
    const fn = stubFetch({ ok: true })
    render(<MyVideos videos={[analyzed]} />)

    await user.click(screen.getByRole('button', { name: /삭제/ }))
    expect(fn).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: '정말 지웁니다' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '취소' })).toBeInTheDocument()
  })

  it('취소하면 아무 일도 없다', async () => {
    const user = userEvent.setup()
    const fn = stubFetch({ ok: true })
    render(<MyVideos videos={[analyzed]} />)

    await user.click(screen.getByRole('button', { name: /삭제/ }))
    await user.click(screen.getByRole('button', { name: '취소' }))
    expect(fn).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: /삭제/ })).toBeInTheDocument()
  })

  it('확인하면 그 영상만 지우도록 부르고 목록에서 뺀다', async () => {
    const user = userEvent.setup()
    const fn = stubFetch({ ok: true })
    render(<MyVideos videos={[analyzed]} />)

    await user.click(screen.getByRole('button', { name: /삭제/ }))
    await user.click(screen.getByRole('button', { name: '정말 지웁니다' }))

    await waitFor(() => expect(fn).toHaveBeenCalledTimes(1))
    expect(fn.mock.calls[0][0]).toBe('/api/videos/v1')
    expect(fn.mock.calls[0][1]).toMatchObject({ method: 'DELETE' })
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

  it('브라우저에만 있던 리포트도 함께 거둔다', async () => {
    const user = userEvent.setup()
    stubFetch({ ok: true })
    saveReport('v1', { summary: '요약', traits: [], titles: [], scenes: [] })
    render(<MyVideos videos={[analyzed]} />)

    await user.click(screen.getByRole('button', { name: /삭제/ }))
    await user.click(screen.getByRole('button', { name: '정말 지웁니다' }))

    await waitFor(() => expect(reportFor('v1')).toBeNull())
  })
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
    expect(fn).not.toHaveBeenCalled()
  })
})

