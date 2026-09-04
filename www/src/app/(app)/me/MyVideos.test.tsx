import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { MyVideo } from '@/server/backend'
import { listPublished } from '@/lib/published'
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
