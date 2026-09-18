import { render, screen, waitFor, within } from '@testing-library/react'
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
    function openWithCancel(fail?: string) {
      const onClose = vi.fn()
      const onCancel = vi.fn(() =>
        fail ? Promise.reject(new Error(fail)) : Promise.resolve(),
      )
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

    /**
     * 🔴 **정정 (2026-09-17, 미결 `paik` 34번)**: 전에는 **내려보내고 나서**
     * 취소를 알렸다. 그때는 취소가 화면 안의 일이라 실패할 것이 없었는데,
     * 이제 서버로 나간다(`DELETE /matches/{id}`) — **먼저 내려보내면 실패해도
     * 판이 사라져서, 안 물러진 경기를 물러진 것으로 읽는다.** 그래서 순서를
     * 뒤집었다: 보내고 → 성공하면 내려가고 → 다 내려간 뒤 `onClose` 로 거둔다.
     */
    it('확인하면 먼저 보내고, 성공한 뒤에 내려간다', async () => {
      const user = userEvent.setup()
      const { onClose, onCancel } = openWithCancel()
      await user.click(screen.getByRole('button', { name: '경기 취소' }))
      await user.click(screen.getByRole('button', { name: '정말 취소합니다' }))

      await waitFor(() => expect(onCancel).toHaveBeenCalled())
      await waitFor(() =>
        expect(document.querySelector('.ss-mw')).toHaveAttribute('data-leaving', 'true'),
      )
      // 다 내려간 뒤에야 부모가 판을 거둔다.
      await waitFor(() => expect(onClose).toHaveBeenCalled())
    })

    /**
     * 🔴 **실패하면 판이 안 닫히고 이유를 그대로 적는다.** 지원자가 붙은 경기는
     * 서버가 `409 MATCH_HAS_APPLICATIONS` 로 막는다(행 삭제라 DB 가 못 지운다).
     * 화면이 미리 막지 않는다 — 지원이 몇인지는 서버만 안다.
     *
     * ⚠️ mock 에는 지원이라는 개념이 없어 그 갈래를 못 밟는다(`mock.ts` 의
     * `cancelMatch` 머리말) — 그래서 이 시험이 그 자리를 대신 붙든다.
     */
    it('무르지 못하면 판이 그대로 있고 서버가 준 이유를 적는다', async () => {
      const user = userEvent.setup()
      const { onClose } = openWithCancel('지원자가 있어 취소할 수 없습니다.')
      await user.click(screen.getByRole('button', { name: '경기 취소' }))
      await user.click(screen.getByRole('button', { name: '정말 취소합니다' }))

      expect(await screen.findByRole('alert')).toHaveTextContent(
        '지원자가 있어 취소할 수 없습니다.',
      )
      expect(document.querySelector('.ss-mw')).not.toHaveAttribute('data-leaving', 'true')
      expect(onClose).not.toHaveBeenCalled()
      // 다시 눌러 볼 수 있어야 한다 — 한 번 실패했다고 길이 막히면 안 된다.
      expect(screen.getByRole('button', { name: '정말 취소합니다' })).toBeEnabled()
    })

    /* 🔴 무를 길이 없으면 단추도 안 그린다 — 눌러도 아무 일이 없으면 안 된다. */
    it('무를 길이 없으면 단추를 안 낸다', () => {
      open()
      expect(screen.queryByRole('button', { name: '경기 취소' })).toBeNull()
    })
  })

  /**
   * 🔴 **「데모입니다」를 적지 않는다**(2026-09-17, 사용자 지적).
   *
   * 가짜 `applyToTeam` 이 1.4초 뒤 수락을 흉내내던 시절의 문장이다 — 그때는
   * 숨기지 않는 것이 옳았다. 지금은 수락이 **진짜로 서버에 나가고 경기가
   * 실제로 잡힌다**(계약 3-15절). 그대로 두면 그 문장이 **거짓**이고,
   * 조건 없이 박혀 있어서 `USE_MOCK` 으로도 안 꺼져 **실제 도메인에서도 떴다.**
   */
  it('데모라고 적지 않는다 — 이제 진짜로 잡힌다', () => {
    open()
    expect(screen.queryByText(/데모입니다/)).toBeNull()
  })
})

/**
 * **경기가 끝나면 마무리하고 리뷰를 남긴다** (사용자 요청, 2026-09-17).
 *
 * 🔴 **이미 한 경기를 「취소」하는 것은 말이 안 된다** — 시각이 지나면 그
 * 자리가 「경기 끝내기」가 되고, 누르면 리뷰로 넘어간다.
 */
describe('대기 화면 — 경기가 끝난 뒤', () => {
  afterEach(() => vi.useRealTimers())

  /** 경기 시각을 지나 있게 시계를 옮긴다. */
  function afterMatch() {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.setSystemTime(new Date('2026-09-19T12:00:00'))
  }

  it('경기 시각이 지나면 「경기 끝내기」다 — 「경기 취소」가 아니다', async () => {
    afterMatch()
    render(<MatchWaiting us={US} them={THEM} onClose={vi.fn()} onCancel={vi.fn()} />)

    expect(await screen.findByRole('button', { name: '경기 끝내기' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '경기 취소' })).toBeNull()
  })

  it('아직 안 지났으면 그대로 「경기 취소」다', () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.setSystemTime(new Date('2026-09-19T08:00:00'))
    render(<MatchWaiting us={US} them={THEM} onClose={vi.fn()} onCancel={vi.fn()} />)

    expect(screen.getByRole('button', { name: '경기 취소' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '경기 끝내기' })).toBeNull()
  })

  it('「경기 끝내기」를 누르면 우리 팀·상대 팀으로 나눠 리뷰를 받는다', async () => {
    afterMatch()
    const user = userEvent.setup()
    render(<MatchWaiting us={US} them={THEM} onClose={vi.fn()} onCancel={vi.fn()} />)

    await user.click(await screen.findByRole('button', { name: '경기 끝내기' }))

    const panel = screen.getByRole('dialog', { name: '경기 리뷰' })
    expect(panel).toHaveTextContent('우리 팀')
    expect(panel).toHaveTextContent('번개FC')
    // 양 팀 사람이 다 줄로 선다.
    expect(screen.getByRole('button', { name: /정우진/ })).toBeInTheDocument()
  })

  /* 🔴 **강제가 아니다**(사용자 요청) — 아무것도 안 고르면 저장이 안 눌린다. */
  it('아무것도 안 고르면 저장이 안 눌린다', async () => {
    afterMatch()
    const user = userEvent.setup()
    render(<MatchWaiting us={US} them={THEM} onClose={vi.fn()} onCancel={vi.fn()} />)
    await user.click(await screen.findByRole('button', { name: '경기 끝내기' }))

    expect(screen.getByRole('button', { name: '저장' })).toBeDisabled()
  })

  it('사람을 펴서 고르면 저장할 수 있다', async () => {
    afterMatch()
    const user = userEvent.setup()
    render(<MatchWaiting us={US} them={THEM} onClose={vi.fn()} onCancel={vi.fn()} />)
    await user.click(await screen.findByRole('button', { name: '경기 끝내기' }))

    await user.click(screen.getByRole('button', { name: /정우진/ }))
    /* 🔴 **별점이 아니라 고르는 것이다**(계약 3-9절) — 문구도 서버 시드 그대로다. */
    await user.click(screen.getByRole('button', { name: '시간을 잘 지켰다' }))

    const save = screen.getByRole('button', { name: '저장' })
    expect(save).toBeEnabled()
    await user.click(save)
    expect(screen.getByRole('status')).toHaveTextContent('남겼습니다')
  })

  /* 🔴 **닫으면 둘 다 내려간다**(사용자 설계) — 리뷰가 먼저, 이어서 대기 화면. */
  it('리뷰를 닫으면 대기 화면까지 닫힌다', async () => {
    afterMatch()
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(<MatchWaiting us={US} them={THEM} onClose={onClose} onCancel={vi.fn()} />)
    await user.click(await screen.findByRole('button', { name: '경기 끝내기' }))

    /* 🔴 대기 화면에도 「닫기」가 있다 — **리뷰 판 안의 것**으로 좁힌다. */
    const panel = screen.getByRole('dialog', { name: '경기 리뷰' })
    await user.click(within(panel).getByRole('button', { name: '닫기' }))

    expect(screen.queryByRole('dialog', { name: '경기 리뷰' })).toBeNull()
    await waitFor(() => expect(onClose).toHaveBeenCalled())
  })

  /**
   * 🔴 **판의 카드를 누르면 간단한 프로필**(사용자 요청, 2026-09-18:
   * "카드를 클릭하면 클릭한 대상의 프로필을 간단하게 볼수있으면 좋겠어.
   * 랭크라던가 별명같은거. 경기매칭된 상태는 유지 되어야해").
   */
  describe('판의 카드를 누르면 프로필이 뜬다', () => {
    const card = { user: { nickname: '정우진' }, titles: [], tagline: '주말엔 공 찬다' }
    const grade = { grade: 'A', provisional: true, notes: ['차는 다리를 끝까지 뻗습니다'] }

    const stubCards = () =>
      vi.stubGlobal(
        'fetch',
        vi.fn(async (url: string) => ({
          ok: true,
          status: 200,
          json: async () => (url.endsWith('/grade') ? grade : card),
        })),
      )

    const WITH_SLUG: MatchTeam = {
      ...THEM,
      squad: [{ nickname: '정우진', col: 1, row: 0, pos: 'FW', cardSlug: 'jung-4f2a' }],
    }

    it('이름 · 등급 · 한 줄을 보여 준다', async () => {
      stubCards()
      const user = userEvent.setup()
      render(<MatchWaiting us={US} them={WITH_SLUG} onClose={vi.fn()} />)
      await user.click(screen.getByRole('button', { name: '정우진 프로필 보기' }))

      const who = await screen.findByRole('complementary', { name: '정우진 프로필' })
      expect(within(who).getByText('A')).toBeInTheDocument()
      expect(within(who).getByText('주말엔 공 찬다')).toBeInTheDocument()
    })

    /* 🔴 계약이 못 박은 것 — 등급 문자만 떼어 쓰지 않는다. */
    it('검수 전이면 등급 옆에 그렇게 적는다', async () => {
      stubCards()
      const user = userEvent.setup()
      render(<MatchWaiting us={US} them={WITH_SLUG} onClose={vi.fn()} />)
      await user.click(screen.getByRole('button', { name: '정우진 프로필 보기' }))
      expect(await screen.findByText('검수 전')).toBeInTheDocument()
    })

    /* 🔴 **사용자가 못 박은 조건** — 프로필을 닫아도 경기 화면은 남는다. */
    it('프로필을 닫아도 경기 화면은 그대로다', async () => {
      stubCards()
      const user = userEvent.setup()
      const onClose = vi.fn()
      render(<MatchWaiting us={US} them={WITH_SLUG} onClose={onClose} />)
      await user.click(screen.getByRole('button', { name: '정우진 프로필 보기' }))

      const who = await screen.findByRole('complementary', { name: '정우진 프로필' })
      await user.click(within(who).getByRole('button', { name: '닫기' }))

      expect(screen.queryByRole('complementary', { name: '정우진 프로필' })).toBeNull()
      expect(onClose).not.toHaveBeenCalled()
      expect(screen.getByText('9월 19일 토요일 10:00')).toBeInTheDocument()
    })

    /* 🔴 등급이 없는 것은 고장이 아니다 — 대표 영상이 없거나 분석 전이다. */
    it('등급이 없으면 그렇다고 적는다', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(async (url: string) => ({
          ok: true,
          status: 200,
          json: async () =>
            url.endsWith('/grade') ? { grade: null, provisional: false, notes: null } : card,
        })),
      )
      const user = userEvent.setup()
      render(<MatchWaiting us={US} them={WITH_SLUG} onClose={vi.fn()} />)
      await user.click(screen.getByRole('button', { name: '정우진 프로필 보기' }))
      expect(await screen.findByText('아직 분석된 등급이 없습니다.')).toBeInTheDocument()
    })
  })
})
