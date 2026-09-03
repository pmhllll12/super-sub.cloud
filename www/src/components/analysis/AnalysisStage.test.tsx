import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AnalysisStage from './AnalysisStage'

/**
 * 🔴 검출기는 대역으로 세운다. 진짜를 부르면 jsdom 에서 WebGL 도 망도 없어
 * **로드가 실패하고 화면이 "따라가기 꺼짐" 으로 넘어간다** — 그러면 네모에
 * 관한 것은 하나도 시험할 수 없다. 무거운 tfjs 를 안 싣는 덤도 있다.
 */
vi.mock('@/lib/personDetector', () => ({
  warmUpDetector: () => Promise.resolve({}),
  warmUpRefine: () => Promise.resolve({}),
  detectPeople: () => Promise.resolve([{ box: { x: 0.3, y: 0.2, w: 0.25, h: 0.5 }, score: 0.9 }]),
  // 2단계는 없어도 되는 덤이다 — 못 하면 1단계 관절을 쓴다.
  refinePose: () => Promise.resolve(null),
}))

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

  // 🔴 기본값을 축구로 박아 두면 야구 영상이 축구 루브릭으로 조용히 채점된다.
  it('종목은 처음에 아무것도 골라져 있지 않다', () => {
    render(<AnalysisStage />)
    for (const name of ['축구', '야구', '농구']) {
      expect(screen.getByRole('button', { name })).toHaveAttribute('aria-pressed', 'false')
    }
  })

  // 창 틀 흉내로 뒀던 장식 점 둘은 없앴다(사용자 요청) — 누를 수 있는 것은
  // 하나뿐인데 셋이 나란히 있으면 나머지도 눌리는 것처럼 보인다.
  it('창 틀 머리줄의 점은 하나뿐이다', () => {
    const { container } = render(<AnalysisStage />)
    expect(container.querySelectorAll('.ss-shot-dot')).toHaveLength(1)
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

  // 🔴 에이전트가 종목을 알아야 세세하게 본다 — 루브릭이 종목마다 다르다.
  it('영상만 골라서는 시작할 수 없고, 종목까지 골라야 풀린다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)

    const startBtn = screen.getByRole('button', { name: '분석 시작하기' })
    expect(startBtn).toBeDisabled()
    // 왜 잠겼는지 화면에 적어 둔다 — 잠긴 버튼만 있으면 이유를 알 길이 없다.
    expect(screen.getByText('종목을 먼저 골라 주세요')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '야구' }))
    expect(screen.getByRole('button', { name: '야구' })).toHaveAttribute('aria-pressed', 'true')
    expect(startBtn).toBeEnabled()
  })

  // 돌고 있는 분석의 루브릭을 도중에 갈아끼우는 셈이 된다.
  it('시작한 뒤에는 종목을 바꿀 수 없다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: '농구' }))
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))

    // 고른 것은 그대로 보인다 — 무엇으로 보고 있는지가 분석 내내 남아야 한다.
    expect(screen.getByRole('button', { name: '농구' })).toHaveAttribute('aria-pressed', 'true')
    for (const name of ['축구', '야구', '농구']) {
      expect(screen.getByRole('button', { name })).toBeDisabled()
    }
  })

  // 같은 사람이 연달아 올리는 클립은 대개 같은 종목이다.
  it('영상을 물러도 고른 종목은 남는다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: '축구' }))
    await user.click(screen.getByRole('button', { name: '영상 닫기' }))

    await screen.findByLabelText('분석할 영상', {}, { timeout: 2000 })
    expect(screen.getByRole('button', { name: '축구' })).toHaveAttribute('aria-pressed', 'true')
  })

  // 🔴 시작 전에는 오른쪽 판이 아직 없다 — 여기서 못 무르면 잘못 고른 영상을
  // 되돌릴 길이 아예 없다.
  it('창 틀의 닫기 점으로 고른 영상을 무른다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    expect(screen.getByText('clip.mp4')).toBeInTheDocument()

    // 닫기는 2단계다 — 판이 줄고 사진이 돌아온 **뒤에야** 고르는 자리로 돌아온다.
    await user.click(screen.getByRole('button', { name: '영상 닫기' }))
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
    await user.click(screen.getByRole('button', { name: '축구' }))
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
    await user.click(screen.getByRole('button', { name: '축구' }))
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
    await user.click(screen.getByRole('button', { name: '축구' }))
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
    await user.click(screen.getByRole('button', { name: '축구' }))
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
    await user.click(screen.getByRole('button', { name: '축구' }))
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))
    await screen.findByRole('button', { name: '이 사람으로 분석' }, { timeout: 2500 })
    await drawSubject(user)
    expect(document.querySelector('.ss-shot-track')).not.toBeNull()

    await user.click(screen.getByRole('button', { name: '영상 닫기' }))
    // 판이 다 줄기를 기다리지 않는다 — 누른 즉시다.
    expect(document.querySelector('.ss-shot-track')).toBeNull()
  })

  // 🔴 이 자리에 있던 '다른 영상' 은 **저장**으로 바뀌었다(사용자 요청). 되돌리는
  // 길은 위 닫기 점 하나뿐이므로 그쪽 검사가 이 자리의 검사를 겸한다.
  it('리포트가 끝나기 전에는 저장이 잠겨 있다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: '축구' }))
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))
    await screen.findByRole('button', { name: '이 사람으로 분석' }, { timeout: 2500 })
    await drawSubject(user)

    expect(screen.getByRole('button', { name: '저장' })).toBeDisabled()
  })

  // 창 틀의 닫기 자리이므로 시작한 뒤에도 그대로 있어야 한다.
  it('시작한 뒤에도 닫기 점이 남아 있고, 누르면 고르기 전으로 돌아간다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    // 종목을 골라야 시작이 풀린다.
    await user.click(screen.getByRole('button', { name: '축구' }))
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))

    await user.click(screen.getByRole('button', { name: '영상 닫기' }))
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
    await user.click(screen.getByRole('button', { name: '축구' }))
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

    // 대상이 정해지면 그때부터 돈다.
    await user.click(screen.getByRole('button', { name: '자동으로 고르기' }))
    expect(await screen.findByLabelText('분석 진행')).toBeInTheDocument()
  })

  // 🔴 검출기는 사람을 여럿 찾아내고 지금은 **가장 큰 박스**를 자동으로 고른다
  // (pose.py 의 _largest_person_box) — 카메라에 가까운 사람일 뿐이다. 미결 8번의
  // 결론("continuity 는 처음 잡은 대상이 맞으면 이긴다")을 사람이 찍어 해소한다.
  it('다 자란 화면에서 분석할 사람을 먼저 묶는다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: '축구' }))
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
    await user.click(screen.getByRole('button', { name: '축구' }))
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
    await user.click(screen.getByRole('button', { name: '축구' }))
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
    await user.click(screen.getByRole('button', { name: '축구' }))
    await user.click(screen.getByRole('button', { name: '분석 시작하기' }))

    await user.click(
      await screen.findByRole('button', { name: '자동으로 고르기' }, { timeout: 2500 }),
    )

    expect(document.querySelector('.ss-shot-pick')).toBeNull()
    expect(await screen.findByLabelText('분석 진행')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '보고 있습니다' })).toBeInTheDocument()
  })
})
