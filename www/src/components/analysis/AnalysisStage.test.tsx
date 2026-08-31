import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AnalysisStage from './AnalysisStage'

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

  // 창 틀의 닫기 자리이므로 시작한 뒤에도 그대로 있어야 한다.
  it('시작한 뒤에도 닫기 점이 남아 있고, 누르면 고르기 전으로 돌아간다', async () => {
    const user = userEvent.setup()
    const { input, file } = pick()
    await user.upload(input, file)
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
    // 오른쪽 판이 뜬 뒤부터 단계가 돈다.
    expect(await screen.findByLabelText('분석 진행', {}, { timeout: 2500 })).toBeInTheDocument()
  })
})
