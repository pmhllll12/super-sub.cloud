import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { MatchTeam } from '@/lib/teamMatch'
import MatchWaiting from './MatchWaiting'

/**
 * **경기가 잡혔다** — 화면을 덮는 팝업(사용자 요청, 2026-09-10).
 * 가운데는 언제 · 어디서 · 누구와, 양옆은 두 팀의 판.
 */
const THEM: MatchTeam = {
  id: 'mt-1',
  name: '번개FC',
  region: '서울 강남구',
  size: '5',
  playedAt: '2026-09-19T10:00:00',
  place: '강남 풋살장 2구장',
  why: ['같은 지역'],
  squad: [
    { nickname: '정우진', col: 1, row: 0, pos: 'FW' },
    { nickname: '배준영', col: 1, row: 3, pos: 'GK' },
  ],
}
const US = {
  name: '우리 팀',
  squad: [
    { nickname: '홍길동', col: 1, row: 0, pos: 'FW' as const },
    { nickname: '이영희', col: 1, row: 3, pos: 'GK' as const },
  ],
}

describe('경기 대기 팝업', () => {
  const open = (onClose = vi.fn()) => {
    render(<MatchWaiting us={US} them={THEM} onClose={onClose} />)
    return onClose
  }

  it('언제 · 어디서 · 누구와를 가운데에 적는다', () => {
    open()
    expect(screen.getByText('9월 19일 토요일 10:00')).toBeInTheDocument()
    expect(screen.getByText('강남 풋살장 2구장')).toBeInTheDocument()
    expect(screen.getByText('VS')).toBeInTheDocument()
  })

  /* 🔴 **양옆에 두 팀의 판**이 선다 — 이름과 포지션을 둘 다 적는다(사용자 결정). */
  it('양옆에 두 팀의 판을 이름 · 포지션과 함께 그린다', () => {
    open()
    expect(screen.getByLabelText('우리 팀 스쿼드')).toBeInTheDocument()
    expect(screen.getByLabelText('번개FC 스쿼드')).toBeInTheDocument()
    expect(screen.getByText('홍길동')).toBeInTheDocument()
    expect(screen.getByText('정우진')).toBeInTheDocument()
    expect(screen.getAllByText('GK')).toHaveLength(2)
  })

  /* 🔴 **골키퍼 줄 양옆은 아예 안 그린다** — 빈 칸으로 그리면 판이 "여기도
     설 수 있다"고 말하는 셈이다(`lib/pitchGrid.ts` 의 규칙). 3×4 에서 둘이 빠져
     한 판에 10칸이다. */
  /* 🔴 **홈의 판과 같은 모양이어야 한다**(사용자 지적, 2026-09-10). 처음에는
     네모 칸에 이름만 찍었는데 그건 스쿼드 판이 아니라 표였다 — 경기장 선과
     선수 카드를 홈과 **같은 클래스**로 그린다. */
  it('홈의 스쿼드 판과 같은 것으로 그린다', () => {
    open()
    /* 🔴 `container` 가 아니라 문서에서 찾는다 — 이 판은 `document.body` 로
       내보내진다(portal). 안 그러면 헤더 · 로그아웃이 위로 비쳐 나온다. */
    expect(document.querySelectorAll('.ss-squad-pitch')).toHaveLength(2)
    expect(document.querySelectorAll('.ss-squad-board')).toHaveLength(2)
    // 사람이 있는 자리만 그린다 — 여기는 짜는 자리가 아니라 보여 주는 자리다.
    expect(document.querySelectorAll('.ss-squad-seat')).toHaveLength(4)
    expect(document.querySelectorAll('.ss-pcard')).toHaveLength(4)
  })

  /* 🔴 **쌓임 맥락 밖에 선다.** 스쿼드 판 안에 남으면 `.ss-home-stage`
     (`z-index: 10`)에 갇혀 헤더(`z-20`)를 못 넘는다 — 실제로 그랬다. */
  it('스쿼드 판이 아니라 body 에 붙는다', () => {
    const { container } = render(<MatchWaiting us={US} them={THEM} onClose={vi.fn()} />)
    expect(container.querySelector('.ss-mw')).toBeNull()
    expect(document.body.querySelector('.ss-mw')).toBeInTheDocument()
  })

  /**
   * 🔴 **내려가는 것을 다 보여 준 뒤에 알린다**(사용자 요청, 2026-09-10).
   * 누르자마자 부모가 지우면 내려가는 연출을 아무도 못 본다 — 추천 판이
   * 같은 이유로 같은 것을 한다.
   */
  it('× 를 누르면 내려간 뒤에 닫는다', async () => {
    const user = userEvent.setup()
    const onClose = open()
    await user.click(screen.getByRole('button', { name: '닫기' }))

    // 아직 DOM 에 있고, 내려가는 중이라고 표시된다.
    expect(document.querySelector('.ss-mw')).toHaveAttribute('data-leaving', 'true')
    await waitFor(() => expect(onClose).toHaveBeenCalled())
  })

  /* 내려가는 동안에는 아무것도 못 누른다 — 두 번 눌러도 한 번만 닫힌다. */
  it('두 번 눌러도 한 번만 닫는다', async () => {
    const user = userEvent.setup()
    const onClose = open()
    const x = screen.getByRole('button', { name: '닫기' })
    await user.click(x)
    await user.click(x)
    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1))
  })

  /* 🔴 × 하나뿐이면 자판만 쓰는 사람이 화면에 갇힌다. */
  it('Esc 로도 닫힌다', async () => {
    const user = userEvent.setup()
    const onClose = open()
    await user.keyboard('{Escape}')
    await waitFor(() => expect(onClose).toHaveBeenCalled())
  })

  it('앞에 선 판이라는 것을 낭독기에 알린다', () => {
    open()
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true')
  })

  /**
   * 🔴 **취소는 닫기(×)와 다른 일이다** — ×는 판을 접는 것이고 이것은 잡힌
   * 경기를 무르는 것이다. 되돌릴 수 없어서 그 자리에서 한 번 더 묻는다
   * (`window.confirm` 은 안 쓴다 — 이 사이트는 제 판을 그려 왔다).
   */
  describe('경기 취소', () => {
    /** 취소까지 붙은 판 — 무를 길이 있어야 단추가 나온다. */
    function openWithCancel() {
      const onClose = vi.fn()
      const onCancel = vi.fn()
      render(<MatchWaiting us={US} them={THEM} onClose={onClose} onCancel={onCancel} />)
      return { onClose, onCancel }
    }

    it('곧바로 취소하지 않고 한 번 더 묻는다', async () => {
      const user = userEvent.setup()
      const { onCancel } = openWithCancel()
      await user.click(screen.getByRole('button', { name: '경기 취소' }))

      expect(screen.getByRole('button', { name: '정말 취소합니다' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: '되돌리기' })).toBeInTheDocument()
      // 아직 아무 일도 안 일어났다 — 묻기만 한 것이다.
      expect(onCancel).not.toHaveBeenCalled()
    })

    it('되돌리면 아무 일도 없다', async () => {
      const user = userEvent.setup()
      const { onClose, onCancel } = openWithCancel()
      await user.click(screen.getByRole('button', { name: '경기 취소' }))
      await user.click(screen.getByRole('button', { name: '되돌리기' }))

      expect(screen.getByRole('button', { name: '경기 취소' })).toBeInTheDocument()
      expect(onCancel).not.toHaveBeenCalled()
      expect(onClose).not.toHaveBeenCalled()
    })

    /* 🔴 **닫기와 다른 것을 부른다** — 취소는 경기를 무르는 일이라 부모가
       「내 경기」에서도 빼야 한다. `onClose` 로 나가면 잡힌 채로 남는다. */
    it('확인하면 내려간 뒤에 취소를 알린다', async () => {
      const user = userEvent.setup()
      const { onClose, onCancel } = openWithCancel()
      await user.click(screen.getByRole('button', { name: '경기 취소' }))
      await user.click(screen.getByRole('button', { name: '정말 취소합니다' }))

      expect(document.querySelector('.ss-mw')).toHaveAttribute('data-leaving', 'true')
      await waitFor(() => expect(onCancel).toHaveBeenCalled())
      expect(onClose).not.toHaveBeenCalled()
    })

    /* 🔴 무를 길이 없으면 단추도 안 그린다 — 눌러도 아무 일이 없으면 안 된다. */
    it('무를 길이 없으면 단추를 안 낸다', () => {
      open()
      expect(screen.queryByRole('button', { name: '경기 취소' })).toBeNull()
    })
  })

  // ⚠️ 지어낸 수락이라는 것을 숨기지 않는다.
  it('데모라는 것을 적어 둔다', () => {
    open()
    expect(screen.getByText(/데모입니다/)).toBeInTheDocument()
  })
})
