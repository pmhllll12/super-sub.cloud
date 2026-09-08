import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AnalysisStage from './AnalysisStage'

/**
 * 🔴 검출기는 대역으로 세운다. 진짜를 부르면 jsdom 에서 WebGL 도 망도 없어
 * **로드가 실패하고 화면이 "따라가기 꺼짐" 으로 넘어간다** — 그러면 네모에
 * 관한 것은 하나도 시험할 수 없다. 무거운 tfjs 를 안 싣는 덤도 있다.
 */
/**
 * 🔴 **관절(keypoints)도 준다.** 진짜 MoveNet MultiPose 는 늘 함께 주는데
 * 대역이 상자만 주고 있었다 — 그 상태로는 「이 사람이 맞습니까?」 관문이
 * 영영 안 뜬다(관절이 붙은 것을 세는 관문이라서다). 17개를 다 만들 이유는
 * 없고 몸에 걸친 몇 점이면 된다.
 */
const KEYPOINTS = Array.from({ length: 17 }, (_, i) => ({
  x: 0.4 + (i % 3) * 0.02,
  y: 0.25 + i * 0.02,
  score: 0.8,
}))

vi.mock('@/lib/personDetector', () => ({
  warmUpDetector: () => Promise.resolve({}),
  warmUpRefine: () => Promise.resolve({}),
  detectPeople: () =>
    Promise.resolve([{ box: { x: 0.3, y: 0.2, w: 0.25, h: 0.5 }, score: 0.9, keypoints: KEYPOINTS }]),
  // 2단계는 없어도 되는 덤이다 — 못 하면 1단계 관절을 쓴다.
  refinePose: () => Promise.resolve(null),
}))

/**
 * 🔴 **영상이 실린 것으로 세운다.** jsdom 의 `<video>` 는 `readyState` 도
 * `videoWidth` 도 0 이라, 사람 따라가기 루프가 `readyState < 2` 에서 영영
 * 되돌아간다 — 그러면 관절이 안 붙어 「이 사람이 맞습니까?」 관문을 시험할 수
 * 없다.
 *
 * ⚠️ **전역(`vitest.setup.ts`)에 두지 않는다.** 다른 화면은 `videoWidth` 가
 * 0 인 것을 "아직 못 잼" 으로 쓴다(`MyVideos` 의 비율 계산) — 전역으로 속이면
 * 그쪽이 조용히 다른 길을 탄다. 이 파일에서만 세운다.
 */
function loadVideo() {
  for (const el of document.querySelectorAll('video')) {
    Object.defineProperty(el, 'readyState', { value: 4, configurable: true })
    Object.defineProperty(el, 'videoWidth', { value: 640, configurable: true })
    Object.defineProperty(el, 'videoHeight', { value: 360, configurable: true })
  }
}

/**
 * 관문을 지난다 — 「이 사람으로 분석」/「자동으로 고르기」 다음에 오는
 * 「이 사람이 맞습니까?」에 예라고 답한다. 여러 시험이 그 뒤를 보므로 함수로 뺀다.
 */
async function sayYes(user: ReturnType<typeof userEvent.setup>) {
  loadVideo()
  await user.click(await screen.findByRole('button', { name: '예' }, { timeout: 4000 }))
}

describe('영상 분석 화면', () => {
  // 🔴 버튼을 붙였다 뗐다 하면 그 순간 판의 키가 확 바뀌어 안쪽 것들이 툭
  // 떨어진다. 늘 두고 잠가 둔다.
  it('고른 영상이 없으면 시작 버튼이 잠겨 있다', () => {
    render(<AnalysisStage />)
    expect(screen.getByRole('button', { name: '분석 시작하기' })).toBeDisabled()
  })

  it('처음에는 영상을 떨구는 자리와 안내를 보여준다', () => {
    render(<AnalysisStage />)
    expect(screen.getByText('영상을 여기에 놓으세요')).toBeInTheDocument()
    expect(screen.getByLabelText('분석할 영상')).toBeInTheDocument()
    // 영상을 올리기 전에는 진행 단계도 리포트도 없다.
    expect(screen.queryByLabelText('분석 진행')).toBeNull()
    expect(screen.queryByText('리포트')).toBeNull()
  })

  // 🔴 카드에 수치를 그리지 않는 원칙과 같은 자리다. 계약도 report.summary 에
  // 총점·등급 숫자를 넣지 말라고 못박아 뒀다(3장 4). 수치는
  // analysis_metric_value 한 곳에만 있고 이 화면으로 나오지 않는다.
  it('점수 · 등급 · 별점을 그리지 않는다', () => {
    const { container } = render(<AnalysisStage />)
    const text = container.textContent ?? ''
    expect(text).not.toMatch(/\d+\s*점/)
    expect(text).not.toMatch(/등급/)
    expect(text).not.toMatch(/★/)
    expect(text).not.toMatch(/\d+\s*%/)
    expect(container.querySelector('progress')).toBeNull()
    expect(container.querySelector('meter')).toBeNull()
  })

  /* 🔴 **종목을 고르는 자리가 없다** — 축구 하나만 넣기로 했다(팀 결정,
     2026-09-08). 이 시험이 그 결정을 붙들고 있다: 종목을 다시 늘리면서
     `DEFAULT_SPORT` 만 바꾸고 고르는 자리를 안 되살리면 **여기가 먼저
     빨개진다.** 그러지 않으면 다른 종목 영상이 축구 루브릭으로 조용히
     채점되는 옛 위험이 그대로 돌아온다. */
  it('종목을 고르는 자리가 없다 — 축구 하나뿐이다', () => {
    render(<AnalysisStage />)
    for (const name of ['축구', '야구', '농구']) {
      expect(screen.queryByRole('button', { name })).toBeNull()
    }
  })

  /* 🔴 **빨간 점이 아니라 「닫기」라고 적힌 알약이다**(사용자 요청,
     2026-09-08: "다른 사람들이 아예 모르더라"). 창 틀 흉내로 둔 신호등 점이라
     누를 수 있다는 것도, 누르면 무엇이 되는지도 모양만으로는 안 읽혔다.

     영상이 없을 때도 **자리는 남는다** — 없애면 영상을 고르는 순간 머리줄의
     것들이 알약 하나만큼 옆으로 튄다. 그때는 접근성 트리에서 빠진다. */
  it('영상이 없으면 닫기가 자리만 지키고 눌리지 않는다', () => {
    const { container } = render(<AnalysisStage />)
    expect(screen.queryByRole('button', { name: '닫기' })).toBeNull()
    const ghost = container.querySelector('.ss-shot-close[data-ghost="true"]')
    expect(ghost).not.toBeNull()
    expect(ghost).toHaveTextContent('닫기')
  })


  // 🔴 올리기 전에 알아야 다시 안 찍는다. 셋 다 실제로 겪은 실패다 —
  // 카메라가 따라 움직이면 놓치고, 몸이 잘리면 볼 관절이 없고, 비슷한 옷을
  // 입은 사람이 옆에 있으면 헷갈린다.
  it('어떻게 찍어야 하는지 떨구는 자리에 적어 둔다', () => {
    render(<AnalysisStage />)
    expect(screen.getByText(/카메라는 고정/)).toBeInTheDocument()
    expect(screen.getByText(/온몸이 화면 안에/)).toBeInTheDocument()
    expect(screen.getByText(/혼자 나올수록/)).toBeInTheDocument()
  })

  it('영상을 고르면 찍는 법 안내는 자리를 비운다', async () => {
    URL.createObjectURL = vi.fn(() => 'blob:test')
    URL.revokeObjectURL = vi.fn()
    const user = userEvent.setup()
    render(<AnalysisStage />)
    await user.upload(
      screen.getByLabelText('분석할 영상') as HTMLInputElement,
      new File(['x'], 'clip.mp4', { type: 'video/mp4' }),
    )
    expect(screen.queryByText(/카메라는 고정/)).toBeNull()
  })

  it('영상을 고르기 전에도 무엇을 해 주는지 적어 둔다', () => {
    render(<AnalysisStage />)
    expect(screen.getByText(/하나의 점수로 매기지 않습니다/)).toBeInTheDocument()
  })
})

describe('영상 분석 — 대화', () => {
  // 가짜 타이머 + userEvent.type 조합이 멈춰서(입력 지연과 서로 기다린다)
  // 진짜 시간으로 간다. 답이 700ms 뒤에 오므로 findBy 의 기본 대기(1초)로 충분하다.
  const setup = () => userEvent.setup()

  it('묻기 전에는 무엇을 물으면 되는지 적어 둔다', () => {
    render(<AnalysisStage />)
    expect(screen.getByText(/궁금한 것을 물어보세요/)).toBeInTheDocument()
  })

  // 🔴 가짜여도 지연을 넣는다 — 즉시 답하면 "기다리는 동안의 표시"를 아예
  // 안 만들게 되고, API 를 붙이는 날 대화창을 다시 짠다(앱 mock 주석).
  it('물으면 기다리는 표시가 났다가 답이 온다', async () => {
    const user = setup()
    render(<AnalysisStage />)
    await user.type(screen.getByLabelText('질문'), '점수 몇 점인가요')
    await user.click(screen.getByRole('button', { name: '보내기' }))

    expect(screen.getByLabelText('답하는 중')).toBeInTheDocument()
    expect(await screen.findByText(/하나의 점수로 내지 않습니다/)).toBeInTheDocument()
    expect(screen.queryByLabelText('답하는 중')).toBeNull()
  })

  it('빈 질문은 보낼 수 없다', () => {
    render(<AnalysisStage />)
    expect(screen.getByRole('button', { name: '보내기' })).toBeDisabled()
  })

  it('근거를 못 찾은 질문에는 모른다고 답한다', async () => {
    const user = setup()
    render(<AnalysisStage />)
    await user.type(screen.getByLabelText('질문'), '내일 날씨')
    await user.click(screen.getByRole('button', { name: '보내기' }))
    expect(await screen.findByText(/답할 근거가 부족합니다/)).toBeInTheDocument()
  })
})

describe('영상 분석 — 영상을 고른 뒤', () => {
  // jsdom 에는 objectURL 이 없다. 화면이 그 값을 그대로 src 에 쓸 뿐이라
  // 아무 문자열이면 된다.
  beforeEach(() => {
    URL.createObjectURL = vi.fn(() => 'blob:test')
    URL.revokeObjectURL = vi.fn()
  })

  /**
   * 영상 위에 네모를 끌어 그리고 확정한다.
   *
   * jsdom 은 상자 크기를 0 으로 답하고 포인터 붙잡기가 없어서, 그 둘만
   * 흉내 낸다 — 나머지는 진짜 코드가 돈다.
   */
  async function drawSubject(user: ReturnType<typeof userEvent.setup>) {
    const layer = document.querySelector('.ss-shot-pick') as HTMLElement
    const rect = vi
      .spyOn(HTMLElement.prototype, 'getBoundingClientRect')
      .mockReturnValue({ width: 400, height: 300, left: 0, top: 0 } as DOMRect)
    HTMLElement.prototype.setPointerCapture = () => {}
    await user.pointer([
      { keys: '[MouseLeft>]', target: layer, coords: { clientX: 120, clientY: 60 } },
      { target: layer, coords: { clientX: 220, clientY: 260 } },
      { keys: '[/MouseLeft]', target: layer, coords: { clientX: 220, clientY: 260 } },
    ])
    rect.mockRestore()
    await user.click(screen.getByRole('button', { name: '이 사람으로 분석' }))
  }

  function pick() {
    const view = render(<AnalysisStage />)
    const input = screen.getByLabelText('분석할 영상') as HTMLInputElement
    const file = new File(['x'], 'clip.mp4', { type: 'video/mp4' })
    return { view, input, file }
  }

  // 🔴 고르자마자 화면을 채우면 잘못 고른 영상을 되돌릴 자리가 없다.
  it('고르면 판 안에서 먼저 재생되고 시작 버튼이 나온다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)

    expect(screen.getByRole('button', { name: '분석 시작하기' })).toBeInTheDocument()
    // 판 안의 미리보기 하나뿐 — 아직 화면을 채우지 않는다.
    expect(document.querySelectorAll('video')).toHaveLength(1)
    expect(document.querySelector('.ss-shot-video')).toBeNull()
    // 진행 단계도 아직 없다.
    expect(screen.queryByLabelText('분석 진행')).toBeNull()
  })

  /* 🔴 **올리자마자 돈다**(사용자 요청, 2026-09-08). 전에는 `loop` 만 있고
     첫 프레임에서 멈춰 있었다.

     ⚠️ jsdom 은 재생을 흉내만 낸다 — `paused` 가 실제로 갈리지 않는다. 그래서
     여기서는 **틀에 무엇이 적혀 있는지**만 보고, 진짜로 도는지는 CDP 로 쟀다
     (2026-09-08: 2.42s → 4.02s → 되감김 4.73s → 0.31s). `muted` 가 빠지면
     브라우저 정책이 `play()` 를 거부해 **조용히 멈춰 있으므로** 함께 붙든다. */
  it('영상을 고르면 소리 없이 자동으로, 무한히 돈다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)

    const video = screen.getByLabelText(file.name) as HTMLVideoElement
    expect(video).toHaveAttribute('autoplay')
    expect(video).toHaveAttribute('loop')
    expect(video.muted).toBe(true)
  })

  /* 종목이 정해져 있으므로 **영상만 고르면 바로 시작할 수 있다.**
     ⚠️ 전에는 여기서 잠겨 있었고 「종목을 먼저 골라 주세요」가 떴다 — 고를
     자리가 없어진 지금 그 안내는 영영 안 나오므로 함께 걷어냈다. */
  it('영상만 고르면 바로 시작할 수 있다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)

    expect(screen.getByRole('button', { name: '분석 시작하기' })).toBeEnabled()
    expect(screen.queryByText('종목을 먼저 골라 주세요')).toBeNull()
  })
  it('영상을 고르면 닫기가 진짜 버튼이 된다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    expect(screen.getByRole('button', { name: '닫기' })).toBeInTheDocument()
    expect(document.querySelector('.ss-shot-close[data-ghost="true"]')).toBeNull()
  })

  // 🔴 시작 전에는 오른쪽 판이 아직 없다 — 여기서 못 무르면 잘못 고른 영상을
  // 되돌릴 길이 아예 없다.
  it('창 틀의 닫기 점으로 고른 영상을 무른다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    expect(screen.getByText('clip.mp4')).toBeInTheDocument()

    // 닫기는 2단계다 — 판이 줄고 사진이 돌아온 **뒤에야** 고르는 자리로 돌아온다.
    await user.click(screen.getByRole('button', { name: '닫기' }))
    expect(await screen.findByLabelText('분석할 영상', {}, { timeout: 2000 })).toBeInTheDocument()
    // 버튼은 늘 DOM 에 있고 접혀 있을 뿐이다 — 고른 영상이 없으면 잠긴다.
    expect(screen.getByRole('button', { name: '분석 시작하기' })).toBeDisabled()
  })

  // 🔴 시작을 누른 뒤 pause() 를 부르는데도 영상이 저 혼자 0초 → 3초로 흘러가
  // 있었다(사용자 지적). 어디서 다시 트는지 좁히는 대신 규칙을 못박았다 —
  // 묶는 동안 재생은 우리 재생 단추와 대상 확정, 그 둘에서만 시작한다.
  it('묶는 동안 우리가 시키지 않은 재생은 곧바로 도로 세운다', async () => {
    const pauseSpy = vi
      .spyOn(HTMLMediaElement.prototype, 'pause')
      .mockImplementation(() => {})
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))

    pauseSpy.mockClear()
    fireEvent.play(document.querySelector('video') as HTMLVideoElement)
    expect(pauseSpy).toHaveBeenCalled()
    pauseSpy.mockRestore()
  })

  it('사용자가 재생을 누른 것은 막지 않는다', async () => {
    const pauseSpy = vi
      .spyOn(HTMLMediaElement.prototype, 'pause')
      .mockImplementation(() => {})
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))

    await user.click(screen.getByRole('button', { name: '재생' }))
    pauseSpy.mockClear()
    fireEvent.play(document.querySelector('video') as HTMLVideoElement)
    expect(pauseSpy).not.toHaveBeenCalled()
    pauseSpy.mockRestore()
  })

  // 🔴 관절은 MoveNet 이 사람마다 이미 주고 있던 값이다 — 상자만 쓰고 버리던
  // 것을 그린다. 자세 분석 앱이라 관절이 덤이 아니라 본론이다.
  it('따라가는 사람 위에 관절 막대기를 그릴 자리를 둔다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))
    await screen.findByRole('button', { name: '이 사람으로 분석' }, { timeout: 2500 })
    await drawSubject(user)

    expect(document.querySelector('.ss-shot-pose')).not.toBeNull()
    expect(document.querySelector('.ss-shot-bone')).not.toBeNull()
    expect(document.querySelector('.ss-shot-joint')).not.toBeNull()
    // 🔴 화면의 나머지 사람들도 회색으로 그린다 — 초록 하나만 있으면 나머지가
    // 검출이 안 된 건지 그냥 안 그린 건지 알 수 없다.
    expect(document.querySelector('.ss-shot-bone-other')).not.toBeNull()
    expect(document.querySelector('.ss-shot-joint-other')).not.toBeNull()
  })

  // 🔴 회색이 먼저 와야 초록이 그 위에 그려진다 — 겹쳐 선 사람들 사이에서
  // 내 사람이 묻히면 안 된다.
  it('내 사람 막대기가 나머지 사람들 위에 온다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))
    await screen.findByRole('button', { name: '이 사람으로 분석' }, { timeout: 2500 })
    await drawSubject(user)

    const paths = [...document.querySelectorAll('.ss-shot-pose path')]
    const other = paths.findIndex((p) => p.classList.contains('ss-shot-bone-other'))
    const mine = paths.findIndex(
      (p) => p.classList.contains('ss-shot-bone') && !p.classList.contains('ss-shot-bone-other'),
    )
    expect(other).toBeLessThan(mine)
  })

  // 🔴 판이 줄어드는 0.8초 동안 네모만 남아 있으면 무엇을 가리키는지 알 수
  // 없다 — 닫기 점이든 '다른 영상' 이든 누른 그 순간 걷힌다(사용자 요청).
  it('닫기 점을 누르면 따라가는 네모가 곧바로 사라진다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))
    await screen.findByRole('button', { name: '이 사람으로 분석' }, { timeout: 2500 })
    await drawSubject(user)
    expect(document.querySelector('.ss-shot-track')).not.toBeNull()

    await user.click(screen.getByRole('button', { name: '닫기' }))
    // 판이 다 줄기를 기다리지 않는다 — 누른 즉시다.
    expect(document.querySelector('.ss-shot-track')).toBeNull()
  })

  // 🔴 이 자리에 있던 '다른 영상' 은 **저장**으로 바뀌었다(사용자 요청). 되돌리는
  // 길은 위 닫기 점 하나뿐이므로 그쪽 검사가 이 자리의 검사를 겸한다.
  it('리포트가 끝나기 전에는 저장이 잠겨 있다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))
    await screen.findByRole('button', { name: '이 사람으로 분석' }, { timeout: 2500 })
    await drawSubject(user)

    expect(screen.getByRole('button', { name: '내 프로필에 리포트 저장' })).toBeDisabled()
  })

  // 창 틀의 닫기 자리이므로 시작한 뒤에도 그대로 있어야 한다.
  it('시작한 뒤에도 닫기 점이 남아 있고, 누르면 고르기 전으로 돌아간다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    // 종목을 골라야 시작이 풀린다.
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))

    await user.click(screen.getByRole('button', { name: '닫기' }))
    // 1단계 — 자란 것부터 줄어든다. 아직 영상은 창 틀 안에 있다.
    expect(document.querySelector('.ss-shot')).not.toHaveAttribute('data-grown')
    // 2단계 — 다 줄면 고르는 자리로 돌아온다.
    expect(await screen.findByLabelText('분석할 영상', {}, { timeout: 2000 })).toBeInTheDocument()
    expect(document.querySelector('.ss-shot')).not.toHaveAttribute('data-video')
  })

  it('창 틀에 고른 영상의 이름이 뜬다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    expect(screen.getByText('고른 영상이 없습니다')).toBeInTheDocument()
    await user.upload(input, file)
    expect(screen.getByText('clip.mp4')).toBeInTheDocument()
  })

  // 🔴 시작하면 **판이 자란다** — 전체 화면 영상을 따로 띄우지 않는다.
  // 판의 폭 하나가 자람과 밀려남을 같이 정하므로(--ss-shot-panel-w), 그 신호인
  // data-video 가 켜졌는지로 본다.
  it('시작을 누르면 판이 자라고 단계가 돈다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))

    const stage = document.querySelector('.ss-shot')
    // 1단계 — 나갈 것들이 먼저 빠진다. 아직 자라지 않았다.
    expect(stage).toHaveAttribute('data-video', 'true')
    expect(stage).not.toHaveAttribute('data-grown')
    // 영상은 창 틀 안의 그것 하나뿐이다 — 두 군데서 재생되지 않는다.
    expect(document.querySelectorAll('video')).toHaveLength(1)

    // 2단계 — 다 빠지면 자란다. 그때 시작 버튼도 자리를 뜬다.
    await waitFor(() => expect(stage).toHaveAttribute('data-grown', 'true'), { timeout: 1500 })
    // 버튼은 DOM 에 남되 **잠긴다** — 붙였다 뗐다 하면 판의 키가 확 바뀌어
    // 안쪽 것들이 툭 떨어진다. 접히는 것은 CSS 가 한다.
    expect(screen.getByRole('button', { name: '분석 시작하기' })).toBeDisabled()

    // 🔴 오른쪽 판이 떠도 **아직 단계는 안 돈다** — 누구를 볼지부터 정한다.
    await screen.findByRole('button', { name: '자동으로 고르기' }, { timeout: 2500 })
    expect(screen.queryByLabelText('분석 진행')).toBeNull()

    // 🔴 대상을 정해도 **아직 안 돈다**(2026-09-08) — 관절이 붙는 것을 먼저
    //    보여주고 「이 사람이 맞습니까?」를 묻는다.
    await user.click(screen.getByRole('button', { name: '자동으로 고르기' }))
    expect(screen.queryByLabelText('분석 진행')).toBeNull()
    loadVideo()
    expect(await screen.findByText('이 사람이 맞습니까?', {}, { timeout: 4000 })).toBeInTheDocument()

    // 「예」가 그 방아쇠다.
    await sayYes(user)
    expect(await screen.findByLabelText('분석 진행')).toBeInTheDocument()
  })

  /* ── 무엇을 볼지 고르기 (2026-09-08) ─────────────────────────────── */

  /* 🔴 목록은 **에이전트가 실제로 채점하는 항목**이다 — 지어낸 것이 아니라
     `agent/rubrics/basketball_jump_shot.yaml` 의 `criteria[].name` 이다.
     이 시험이 그 사본(`lib/rubricFocus.ts`)이 어긋나는 것을 잡는다. */
  it('그 종목이 채점하는 항목이 선택지로 나온다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))
    await screen.findByRole('button', { name: '자동으로 고르기' }, { timeout: 2500 })

    for (const label of [
      '디딤발 무릎 굴곡',
      '차는 다리 무릎 신전',
      '상체 기울기',
      '골반 회전',
      '팔로스루',
      '디딤발 위치',
    ]) {
      expect(screen.getByRole('button', { name: label })).toBeInTheDocument()
    }
    // 열린 동작 이름도 적는다 — 무엇에 대한 항목인지 알아야 고를 수 있다.
    expect(screen.getByText('인스텝 슈팅')).toBeInTheDocument()
  })

  /* 🔴 루브릭 파일이 정한 규칙이다 — *"status: 사용자 선택지에 올릴지 여부 —
     active만 오른다"*. draft 는 아직 열지 않은 동작이라 없는 기능을 보여주는
     것이 된다. */
  it('아직 안 열린 동작(draft)은 선택지에 없다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))
    await screen.findByRole('button', { name: '자동으로 고르기' }, { timeout: 2500 })

    // 축구의 draft 는 인사이드 패스다. 미룬 항목(deferred)도 마찬가지로 없다.
    expect(screen.queryByText(/인사이드 패스/)).toBeNull()
    expect(screen.queryByRole('button', { name: '임팩트 지점' })).toBeNull()
  })

  /* 🔴 **아무것도 안 고른 것이 「전체적으로」다.** 상태를 따로 두면 "전체인데
     팔로스루도 고른" 앞뒤 안 맞는 경우가 생긴다. */
  it('처음에는 전체적으로가 골라져 있고, 항목을 고르면 풀린다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))
    await screen.findByRole('button', { name: '자동으로 고르기' }, { timeout: 2500 })

    const all = screen.getByRole('button', { name: '전체적으로' })
    expect(all).toHaveAttribute('aria-pressed', 'true')

    await user.click(screen.getByRole('button', { name: '팔로스루' }))
    expect(screen.getByRole('button', { name: '팔로스루' })).toHaveAttribute('aria-pressed', 'true')
    expect(all).toHaveAttribute('aria-pressed', 'false')

    // 여러 개를 고를 수 있다 — 하나를 고르면 앞의 것이 풀리는 라디오가 아니다.
    await user.click(screen.getByRole('button', { name: '골반 회전' }))
    expect(screen.getByRole('button', { name: '팔로스루' })).toHaveAttribute('aria-pressed', 'true')

    // 「전체적으로」를 누르면 고른 것이 다 풀린다.
    await user.click(all)
    expect(screen.getByRole('button', { name: '팔로스루' })).toHaveAttribute('aria-pressed', 'false')
    expect(all).toHaveAttribute('aria-pressed', 'true')
  })

  // 확인하는 자리에 확인할 것이 다 있어야 한다 — 앞 화면으로 돌아가 기억해
  // 낼 일을 만들지 않는다.
  it('관문에서 무엇을 보기로 했는지 다시 말한다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))
    await screen.findByRole('button', { name: '자동으로 고르기' }, { timeout: 2500 })
    await user.click(screen.getByRole('button', { name: '팔로스루' }))
    await user.click(screen.getByRole('button', { name: '자동으로 고르기' }))

    loadVideo()
    await screen.findByText('이 사람이 맞습니까?', {}, { timeout: 4000 })
    expect(document.querySelector('.ss-shot-confirm-focus')?.textContent).toContain('팔로스루')
  })

  /* 🔴 **관문이 곧 S3 방아쇠다**(사용자 요청, 2026-09-08). 관절이 안 붙은
     영상이 올라가면 서버도 누구를 보고 리포트를 쓸지 모른다 — 여기서 막으면
     그런 영상은 올라가지도 않는다. */
  it('묻기 전에는 아무것도 안 올라간다', async () => {
    const fetchMock = vi.fn(async () => new Response('{}', { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))
    await user.click(
      await screen.findByRole('button', { name: '자동으로 고르기' }, { timeout: 2500 }),
    )
    loadVideo()
    await screen.findByText('이 사람이 맞습니까?', {}, { timeout: 4000 })

    expect(fetchMock).not.toHaveBeenCalled()
    vi.unstubAllGlobals()
  })

  // 「아니요」가 하는 일은 `다시 묶기` 와 같다 — 묶는 판으로 돌아간다.
  it('아니요를 누르면 묶는 판으로 돌아간다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))
    await user.click(
      await screen.findByRole('button', { name: '자동으로 고르기' }, { timeout: 2500 }),
    )
    loadVideo()
    await screen.findByText('이 사람이 맞습니까?', {}, { timeout: 4000 })

    await user.click(screen.getByRole('button', { name: '아니요' }))
    expect(screen.queryByText('이 사람이 맞습니까?')).toBeNull()
    expect(screen.getByRole('button', { name: '자동으로 고르기' })).toBeInTheDocument()
  })

  // 🔴 검출기는 사람을 여럿 찾아내고 지금은 **가장 큰 박스**를 자동으로 고른다
  // (pose.py 의 _largest_person_box) — 카메라에 가까운 사람일 뿐이다. 미결 8번의
  // 결론("continuity 는 처음 잡은 대상이 맞으면 이긴다")을 사람이 찍어 해소한다.
  it('다 자란 화면에서 분석할 사람을 먼저 묶는다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))

    // 영상 위에 묶는 판이 뜨고, 무엇을 하라는 것인지 거기에도 적혀 있다.
    expect(document.querySelector('.ss-shot-pick')).not.toBeNull()
    expect(screen.getByText('분석할 사람을 끌어서 네모로 묶어 주세요')).toBeInTheDocument()

    // 아직 아무것도 안 그렸으니 '이 사람으로 분석' 은 잠겨 있다.
    await screen.findByRole('button', { name: '이 사람으로 분석' }, { timeout: 2500 })
    expect(screen.getByRole('button', { name: '이 사람으로 분석' })).toBeDisabled()
    // 오른쪽 판 머리도 아직 '보고 있습니다' 가 아니다.
    expect(screen.getByRole('heading', { name: '분석할 사람' })).toBeInTheDocument()
  })

  // 🔴 첫 프레임에 그 사람이 안 나올 수 있다 — 돌려 보고 세운 뒤 묶어야 한다.
  it('묶는 동안 영상을 돌려 보고 세울 수 있다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))

    expect(screen.getByRole('button', { name: '재생' })).toBeInTheDocument()
    expect(screen.getByLabelText('영상 위치')).toBeInTheDocument()
    // 기본 컨트롤은 꺼 둔다 — 묶는 판에 덮여 못 누르는데 보이기만 하면
    // 우리 컨트롤과 둘로 읽힌다.
    expect(document.querySelector('video')).not.toHaveAttribute('controls')
  })

  // 🔴 막대를 끄는 pointerdown 이 묶는 판으로 올라가면 그 순간 네모가 그려진다.
  it('재생 막대를 만져도 네모가 그려지지 않는다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))

    await user.pointer({ target: screen.getByLabelText('영상 위치'), keys: '[MouseLeft]' })
    expect(document.querySelector('.ss-shot-pick-box')).toBeNull()
    await screen.findByRole('button', { name: '이 사람으로 분석' }, { timeout: 2500 })
    expect(screen.getByRole('button', { name: '이 사람으로 분석' })).toBeDisabled()
  })

  // 대상을 정하고 나면 묶는 판이 걷히고 그 사람을 따라간다.
  it('대상을 정하면 묶는 판이 걷히고 진행이 시작된다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))

    await user.click(
      await screen.findByRole('button', { name: '자동으로 고르기' }, { timeout: 2500 }),
    )

    expect(document.querySelector('.ss-shot-pick')).toBeNull()
    expect(screen.getByRole('heading', { name: '보고 있습니다' })).toBeInTheDocument()
    // 관문을 지나야 진행이 시작된다(2026-09-08).
    await sayYes(user)
    expect(await screen.findByLabelText('분석 진행')).toBeInTheDocument()
  })

  /* 🔴 **「예」가 올린다**(2026-09-08). 예전에는 오른쪽 위 `저장` 이 불러서
     가짜 리포트가 다 나온 뒤에야 영상이 올라갔다 — 미결 「누구를 분석 대상으로
     고를지」의 현황표가 *"`이 사람으로 분석` → S3 저장은 다른 버튼이다"* 로
     지적한 자리다. 세 호출의 순서·본문이 계약과 맞는지가 이 시험의 본론이다. */
  it('예를 누르면 업로드 자리를 받고, S3 에 올리고, 등록한다', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
      const url = String(input)
      if (url === '/api/videos/upload-url') {
        return new Response(
          JSON.stringify({
            storage_key: 'videos/u1/abc.mp4',
            upload_url: 'https://bucket.s3.example.com/abc.mp4?sig=1',
            expires_in: 900,
          }),
          { status: 200 },
        )
      }
      if (url.startsWith('https://bucket.s3.example.com/')) {
        return new Response(null, { status: 200 })
      }
      if (url === '/api/videos') {
        return new Response(
          JSON.stringify({
            id: 'v1',
            sport_code: 'football',
            storage_key: 'videos/u1/abc.mp4',
            duration_ms: 0,
            side: null,
            created_at: '2026-09-03T00:00:00Z',
            passed: true,
            reject_reason: null,
            analysis_job_id: 'job1',
            analysis_status: 'queued',
          }),
          { status: 201 },
        )
      }
      throw new Error(`예상하지 못한 요청: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))
    await user.click(
      await screen.findByRole('button', { name: '자동으로 고르기' }, { timeout: 2500 }),
    )

    // 🔴 관문의 「예」가 방아쇠다 — 리포트를 기다리지 않는다.
    await sayYes(user)
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3), { timeout: 3000 })

    const [uploadUrlCall, s3Call, registerCall] = fetchMock.mock.calls

    expect(uploadUrlCall![0]).toBe('/api/videos/upload-url')
    expect(JSON.parse(uploadUrlCall![1]!.body as string)).toEqual({
      content_type: 'video/mp4',
      size_bytes: 1,
    })

    expect(String(s3Call![0])).toBe('https://bucket.s3.example.com/abc.mp4?sig=1')
    expect(s3Call![1]!.method).toBe('PUT')
    expect((s3Call![1]!.headers as Record<string, string>)['Content-Type']).toBe('video/mp4')

    expect(registerCall![0]).toBe('/api/videos')
    const registerBody = JSON.parse(registerCall![1]!.body as string)
    // 화면 종목 키(soccer)가 아니라 백엔드 sport 코드(football)로 나가야 한다.
    expect(registerBody.sport_code).toBe('football')
    expect(registerBody.storage_key).toBe('videos/u1/abc.mp4')
    expect(typeof registerBody.duration_ms).toBe('number')
    expect(typeof registerBody.width).toBe('number')
    expect(typeof registerBody.height).toBe('number')

    /* 🔴 `저장` 은 이제 **리포트를 내 프로필에 남기는** 단추다 — 영상을 다시
       올리지 않는다(호출 수가 그대로여야 한다). 리포트가 다 나와야 풀린다. */
    await waitFor(() => expect(screen.getByRole('button', { name: '내 프로필에 리포트 저장' })).toBeEnabled(), {
      timeout: 8000,
    })
    await user.click(screen.getByRole('button', { name: '내 프로필에 리포트 저장' }))
    expect(await screen.findByRole('button', { name: '내 프로필에 저장됨' })).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(3)
    // ⚠️ 어디에 남았는지 밝힌다 — 숨기면 다른 기기에서 안 보일 때 고장으로 읽힌다.
    expect(screen.getByText(/이 브라우저에만/)).toBeInTheDocument()

    vi.unstubAllGlobals()
  }, 15000)

  it('반려되면 사유를 보여준다', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
      const url = String(input)
      if (url === '/api/videos/upload-url') {
        return new Response(
          JSON.stringify({
            storage_key: 'videos/u1/abc.mp4',
            upload_url: 'https://bucket.s3.example.com/abc.mp4?sig=1',
            expires_in: 900,
          }),
          { status: 200 },
        )
      }
      if (url.startsWith('https://bucket.s3.example.com/')) {
        return new Response(null, { status: 200 })
      }
      return new Response(
        JSON.stringify({
          id: 'v1',
          sport_code: 'football',
          storage_key: 'videos/u1/abc.mp4',
          duration_ms: 0,
          side: null,
          created_at: '2026-09-03T00:00:00Z',
          passed: false,
          reject_reason: '길이가 상한을 넘습니다: 90초 (상한 60초)',
          analysis_job_id: null,
          analysis_status: null,
        }),
        { status: 201 },
      )
    })
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))
    await user.click(
      await screen.findByRole('button', { name: '자동으로 고르기' }, { timeout: 2500 }),
    )
    await sayYes(user)

    expect(await screen.findByText(/길이가 상한을 넘습니다/, {}, { timeout: 3000 })).toBeInTheDocument()
    /* 🔴 반려면 **첫 칸에서 멈춘다.** 서버가 안 보는 영상이라 리포트가 나올 수
       없는데 단계가 계속 돌면 없는 결과를 기다리게 된다. */
    expect(screen.getByRole('button', { name: '내 프로필에 리포트 저장' })).toBeDisabled()

    vi.unstubAllGlobals()
  }, 10000)

/**
 * 🔴 **저장 없이 떠나면 그 영상을 지운다**(미결 `jin` 24번, 사용자 결정
 * 2026-09-08). 「예」에서 이미 S3 에 올라가 있어서, 안 지우면 분석만 해 보고
 * 마음에 안 든 영상이 영구히 쌓인다.
 *
 * 🔴 되돌릴 수 없는 일이라 **반대쪽이 더 중요하다** — 저장한 영상은 지우면 안
 * 된다. 두 방향을 다 붙든다.
 */
describe('영상 분석 — 저장 안 한 영상은 떠날 때 지운다', () => {
  /** 「예」까지 몰아서 서버에 영상이 올라간 상태(`videoId`)를 만든다. */
  async function uploadedFetch() {
    const fn = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url === '/api/videos/upload-url') {
        return new Response(
          JSON.stringify({
            storage_key: 'videos/u1/abc.mp4',
            upload_url: 'https://bucket.s3.example.com/abc.mp4?sig=1',
            expires_in: 900,
          }),
          { status: 200 },
        )
      }
      if (url.startsWith('https://bucket.s3.example.com/')) return new Response(null, { status: 200 })
      if (url === '/api/videos') {
        return new Response(
          JSON.stringify({
            id: 'v1',
            sport_code: 'football',
            storage_key: 'videos/u1/abc.mp4',
            duration_ms: 0,
            side: null,
            created_at: '2026-09-03T00:00:00Z',
            passed: true,
            reject_reason: null,
            analysis_job_id: 'job1',
            analysis_status: 'queued',
          }),
          { status: 201 },
        )
      }
      return new Response(null, { status: 204 })
    })
    vi.stubGlobal('fetch', fn)
    return fn
  }

  const deletes = (fn: ReturnType<typeof vi.fn>) =>
    fn.mock.calls.filter((c) => (c[1] as { method?: string } | undefined)?.method === 'DELETE')

  async function upload() {
    const fn = await uploadedFetch()
    const user = userEvent.setup()
    // 🔴 `pick()` 이 이미 그린다 — 따로 또 그리면 화면이 둘이 되어 조회가
    //    "여러 개를 찾았다"로 죽는다.
    const { view, input, file } = pick()
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))
    await user.click(
      await screen.findByRole('button', { name: '자동으로 고르기' }, { timeout: 2500 }),
    )
    await sayYes(user)
    await waitFor(() => expect(fn.mock.calls.some((c) => String(c[0]) === '/api/videos')).toBe(true), {
      timeout: 3000,
    })
    return { fn, user, view }
  }

  afterEach(() => vi.unstubAllGlobals())

  it('올린 것이 없으면 떠나도 아무것도 안 지운다', () => {
    const fn = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fn)
    pick().view.unmount()
    expect(deletes(fn)).toHaveLength(0)
  })

  it('저장 안 하고 떠나면 그 영상을 지운다', async () => {
    const { fn, view } = await upload()
    view.unmount()
    const calls = deletes(fn)
    expect(calls).toHaveLength(1)
    expect(String(calls[0]![0])).toBe('/api/videos/v1')
    // 🔴 문서가 사라져도 요청이 끝까지 가야 한다 — beacon 은 DELETE 를 못 보낸다.
    expect((calls[0]![1] as RequestInit).keepalive).toBe(true)
  })

  it('창을 닫을 때(pagehide)도 지운다', async () => {
    const { fn } = await upload()
    await act(async () => {
      window.dispatchEvent(new Event('pagehide'))
    })
    expect(deletes(fn)).toHaveLength(1)
  })

  // 🔴 반대쪽 — 저장한 영상을 지우면 그 사람의 리포트가 통째로 사라진다.
  it('저장했으면 떠나도 안 지운다', async () => {
    const { fn, user, view } = await upload()
    // 리포트가 다 나와야 풀린다 — 위 업로드 시험과 같은 여유를 준다.
    await waitFor(
      () => expect(screen.getByRole('button', { name: '내 프로필에 리포트 저장' })).toBeEnabled(),
      { timeout: 8000 },
    )
    await user.click(screen.getByRole('button', { name: '내 프로필에 리포트 저장' }))
    view.unmount()
    expect(deletes(fn)).toHaveLength(0)
    // 리포트가 다 나올 때까지 기다리는 시험이라 기본 5초로는 모자란다
    // (위 업로드 시험과 같은 값).
  }, 15000)

  // 한 번 지운 것을 또 지우려 들면 안 된다 — 두 길(닫기 · 떠나기)이 겹친다.
  it('두 번 지우지 않는다', async () => {
    const { fn, view } = await upload()
    await act(async () => {
      window.dispatchEvent(new Event('pagehide'))
    })
    view.unmount()
    expect(deletes(fn)).toHaveLength(1)
  })
})
})
