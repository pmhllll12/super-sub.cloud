import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { PlayerCard, Squad } from '@/server/backend'
import SquadPanel from './SquadPanel'

/** 서버가 준 스쿼드 — MF 둘과 GK 하나가 등재돼 있다. */
const SQUAD: Squad = {
  id: 'sq1',
  team_id: 't1',
  public_slug: 'aB3xK9mQ2pL7vN4t',
  members: [
    {
      id: 'sm1',
      player_card_id: 'c9',
      card_public_slug: 'kim-4f2a',
      nickname: '김철수',
      position_code: 'MF',
      position_label: '미드필더',
    },
    {
      id: 'sm2',
      player_card_id: 'c8',
      card_public_slug: 'lee-1a2b',
      nickname: '이영희',
      position_code: 'GK',
      position_label: '골키퍼',
    },
  ],
}

const CARD: PlayerCard = {
  id: 'c1',
  public_slug: 'hong-gildong-4f2a',
  og_image_key: 'cards/7b4d.png',
  user: { id: 'u1', nickname: '홍길동' },
  titles: [],
}

describe('스쿼드 — 서버에서 읽기', () => {
  // 🔴 09-03 에 `GET /teams/{id}/squad` 가 생겼다. 이게 없으면 화면은 다시
  // 새로고침마다 빈 판이 된다.
  it('등재된 사람을 자리에 앉힌다', () => {
    render(<SquadPanel card={CARD} squad={SQUAD} />)
    expect(screen.getByText('김철수')).toBeInTheDocument()
    expect(screen.getByText('이영희')).toBeInTheDocument()
  })

  // 내 자리(FW)는 `card` 가 그린다 — 서버 목록에 내가 있어도 두 번 나오면 안 된다.
  it('스쿼드가 없으면 빈 판을 그린다', () => {
    render(<SquadPanel card={CARD} squad={null} />)
    expect(screen.queryByText('김철수')).toBeNull()
  })
})

describe('스쿼드', () => {
  it('판 위에 카드 다섯 장을 포지션 자리대로 앉힌다', () => {
    const { container } = render(<SquadPanel card={CARD} />)
    expect(container.querySelectorAll('.ss-pcard')).toHaveLength(5)
    expect(screen.getAllByRole('button', { name: /자리에 선수 넣기/ })).toHaveLength(4)
    expect(['FW', 'MF', 'DF', 'GK'].every((p) => screen.getAllByText(p).length > 0)).toBe(true)
    expect(screen.getByText('THREE LUNGS')).toBeInTheDocument()
  })

  // + 만 눌리면 카드를 눌렀는데 아무 일도 안 일어나는 순간이 생긴다.
  it('카드 전체가 버튼이다 — + 는 장식일 뿐이다', () => {
    const { container } = render(<SquadPanel card={CARD} />)
    const seat = screen.getByRole('button', { name: 'GK 자리에 선수 넣기' })
    // 버튼 안에 카드가 통째로 들어 있고, 그 안에 또 버튼이 있지 않다.
    expect(seat.querySelector('.ss-pcard')).not.toBeNull()
    expect(seat.querySelector('button')).toBeNull()
    expect(container.querySelector('.ss-squad-plus')).toHaveAttribute('aria-hidden', 'true')
  })

  it('빈 카드에도 같은 머리글이 있다 — 눌러 보기 전에 무슨 자리인지 안다', () => {
    render(<SquadPanel card={CARD} />)
    expect(screen.getAllByText('PLAYER CARD')).toHaveLength(5)
  })

  it('가만히 두면 추천 판이 없다', () => {
    render(<SquadPanel card={CARD} />)
    expect(screen.queryByRole('complementary')).toBeNull()
  })

  // 이름을 직접 적는 게 아니라 추천에서 고른다.
  it('빈 자리를 누르면 그 포지션의 추천 판이 나온다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel card={CARD} />)
    await user.click(screen.getByRole('button', { name: 'GK 자리에 선수 넣기' }))
    expect(screen.getByRole('complementary', { name: 'GK 추천 선수' })).toBeInTheDocument()
    // 제목이 곧 몇 명이 왔는지다 — 자리마다 추천 수가 다르다.
    expect(screen.getByRole('heading', { name: 'AI 추천 GK 2명' })).toBeInTheDocument()
    // 이름을 적는 칸은 없다.
    expect(screen.queryByRole('textbox')).toBeNull()
  })

  it('자리마다 다른 추천이, 다른 수만큼 나온다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel card={CARD} />)
    await user.click(screen.getAllByRole('button', { name: 'MF 자리에 선수 넣기' })[0])
    expect(screen.getByRole('heading', { name: 'AI 추천 MF 3명' })).toBeInTheDocument()
    expect(screen.getAllByRole('listitem')).toHaveLength(3)
  })

  it('추천에서 고르면 그 자리에 앉고 판이 닫힌다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel card={CARD} />)
    await user.click(screen.getByRole('button', { name: 'DF 자리에 선수 넣기' }))
    await user.click(screen.getByRole('button', { name: /박도현/ }))
    expect(screen.getByRole('button', { name: '박도현 빼기' })).toBeInTheDocument()
    await waitFor(() => expect(screen.queryByRole('complementary')).toBeNull())
  })

  it('닫기 버튼과 Esc 로 닫는다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel card={CARD} />)
    await user.click(screen.getByRole('button', { name: 'GK 자리에 선수 넣기' }))
    await user.click(screen.getByRole('button', { name: '추천 닫기' }))
    await waitFor(() => expect(screen.queryByRole('complementary')).toBeNull())

    await user.click(screen.getByRole('button', { name: 'GK 자리에 선수 넣기' }))
    await user.keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByRole('complementary')).toBeNull())
  })

  it('넣은 선수를 눌러 뺀다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel card={CARD} />)
    await user.click(screen.getByRole('button', { name: 'DF 자리에 선수 넣기' }))
    await user.click(screen.getByRole('button', { name: /박도현/ }))
    await user.click(screen.getByRole('button', { name: '박도현 빼기' }))
    expect(screen.getByRole('button', { name: 'DF 자리에 선수 넣기' })).toBeInTheDocument()
  })

  it('내 카드가 없으면 그 자리에 그렇게 적는다', () => {
    const { container } = render(<SquadPanel card={null} />)
    expect(container.querySelectorAll('.ss-pcard')).toHaveLength(5)
    expect(screen.getByText('아직 카드가 없습니다')).toBeInTheDocument()
  })
})

describe('스쿼드 — 판 크기 3:3 · 5:5 · 7:7', () => {
  const seats = () => screen.getAllByText(/^(GK|DF|MF|FW)$/).length

  // 처음 여는 크기는 풋살 5인이다(사용자 요청).
  it('처음에는 5:5 다', () => {
    render(<SquadPanel card={CARD} />)
    expect(screen.getByRole('radio', { name: '5 : 5' })).toBeChecked()
    expect(seats()).toBe(5)
  })

  it('3:3 을 누르면 자리가 셋으로 줄고 7:7 은 일곱이 된다', async () => {
    const user = userEvent.setup()
    const { container } = render(<SquadPanel card={CARD} />)

    await user.click(screen.getByRole('radio', { name: '3 : 3' }))
    expect(seats()).toBe(3)
    // 배치는 CSS 가 data-size 로 고른다 — 자리 이름이 두 곳에 살지 않게.
    expect(container.querySelector('.ss-squad-board')).toHaveAttribute('data-size', '3')

    await user.click(screen.getByRole('radio', { name: '7 : 7' }))
    expect(seats()).toBe(7)
    expect(container.querySelector('.ss-squad-board')).toHaveAttribute('data-size', '7')
  })

  /* 🔴 줄였다 되돌리면 **그대로 앉아 있어야 한다**(사용자 요청) — 실수로
     눌렀을 때 잃는 것이 없어야 한다. 자리 이름이 역할+번호인 이유다. */
  it('줄일 때 없어진 자리의 사람은 되돌리면 돌아온다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel card={CARD} squad={SQUAD} />)
    // 서버가 준 스쿼드에 MF 김철수가 있다.
    expect(screen.getByRole('button', { name: '김철수 빼기' })).toBeInTheDocument()

    await user.click(screen.getByRole('radio', { name: '3 : 3' }))
    // 3인에는 MF 가 하나뿐이라 둘째 MF 는 판에서 빠진다.
    expect(seats()).toBe(3)

    await user.click(screen.getByRole('radio', { name: '5 : 5' }))
    expect(screen.getByRole('button', { name: '김철수 빼기' })).toBeInTheDocument()
  })

  // 포지션 코드는 계약이 정한 축구 넷뿐이다 — 새 코드를 만들지 않는다.
  it('어느 크기에서도 GK · DF · MF · FW 만 쓴다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel card={CARD} />)
    for (const s of ['3 : 3', '5 : 5', '7 : 7']) {
      await user.click(screen.getByRole('radio', { name: s }))
      // ⚠️ 판 오른쪽 변의 `AI` 단추도 두 글자라 여기 걸린다 — 자리 이름표
      //    (.ss-squad-pos)만 본다.
      for (const el of document.querySelectorAll('.ss-squad-pos')) {
        expect(['GK', 'DF', 'MF', 'FW']).toContain(el.textContent)
      }
    }
  })
})

describe('스쿼드 — 판 위에서 자유롭게 옮긴다', () => {
  /** 그 자리의 지금 이름표. */
  const posOf = (name: string) =>
    screen
      .getByRole('button', { name: new RegExp(name) })
      .closest('.ss-squad-seat')!
      .querySelector('.ss-squad-pos')!.textContent

  /** 격자 칸을 실제 좌표로 세운다 — jsdom 은 크기를 안 재 준다. */
  function layout() {
    for (const el of document.querySelectorAll<HTMLElement>('.ss-squad-cell')) {
      const col = Number(el.dataset.col)
      const row = Number(el.dataset.row)
      el.getBoundingClientRect = () =>
        ({ left: col * 100, top: row * 150, width: 100, height: 150 }) as DOMRect
    }
  }

  /** 카드를 끌어 그 칸에 놓는다. */
  async function drag(seat: HTMLElement, col: number, row: number) {
    layout()
    const to = { clientX: col * 100 + 50, clientY: row * 150 + 75 }
    fireEvent.pointerDown(seat, { button: 0, clientX: 0, clientY: 0, pointerId: 1 })
    fireEvent.pointerMove(seat, { clientX: 40, clientY: 40, pointerId: 1 })
    fireEvent.pointerUp(seat, { ...to, pointerId: 1 })
  }

  const seatOf = (name: string) =>
    screen.getByRole('button', { name: new RegExp(name) }).closest('.ss-squad-seat') as HTMLElement

  // 🔴 행이 포지션을 정한다 — 위가 공격이다.
  it('위로 옮기면 이름표가 FW 로 바뀐다', async () => {
    render(<SquadPanel card={CARD} squad={SQUAD} />)
    // 서버가 준 김철수는 MF 자리(행 1)에 앉는다.
    expect(posOf('김철수')).toBe('MF')

    await drag(seatOf('김철수'), 0, 0)
    expect(posOf('김철수')).toBe('FW')
  })

  /* 🔴 이게 이 기능의 요점이다(사용자 요청) — 3:3 이 골키퍼 1 · 수비 1 ·
     공격 1 로 못박혀 있지 않고 「올 공격」이 될 수 있어야 한다. */
  it('셋을 다 윗줄로 올리면 전원 FW 가 된다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel card={CARD} />)
    await user.click(screen.getByRole('radio', { name: '3 : 3' }))

    for (const [i, seat] of [...document.querySelectorAll('.ss-squad-seat')].entries()) {
      await drag(seat as HTMLElement, i, 0)
    }
    for (const el of document.querySelectorAll('.ss-squad-pos')) {
      expect(el.textContent).toBe('FW')
    }
  })

  // 사람이 있는 칸에 놓으면 밀어내지 않고 서로 바꾼다.
  it('찬 칸에 놓으면 자리를 맞바꾼다', async () => {
    render(<SquadPanel card={CARD} squad={SQUAD} />)
    // 김철수는 MF(행 1), 이영희는 GK(행 3)다.
    expect(posOf('김철수')).toBe('MF')
    expect(posOf('이영희')).toBe('GK')

    const gk = seatOf('이영희')
    const gkCol = Number(
      [...document.querySelectorAll<HTMLElement>('.ss-squad-cell')].find(
        (c) => c.dataset.row === '3',
      )!.dataset.col,
    )
    await drag(seatOf('김철수'), gkCol, 3)
    expect(posOf('김철수')).toBe('GK')
    expect(gk).toBeInTheDocument()
  })

  // 끌 수 없는 입력 장치의 길 — 방향키로도 옮긴다.
  it('방향키로도 옮긴다', () => {
    render(<SquadPanel card={CARD} squad={SQUAD} />)
    expect(posOf('김철수')).toBe('MF')
    fireEvent.keyDown(seatOf('김철수'), { key: 'ArrowUp' })
    expect(posOf('김철수')).toBe('FW')
    // 판 밖으로는 못 나간다 — 한 번 더 눌러도 그대로다.
    fireEvent.keyDown(seatOf('김철수'), { key: 'ArrowUp' })
    expect(posOf('김철수')).toBe('FW')
  })

  /* 🔴 끄는 것과 누르는 것을 갈라 둔다 — 놓자마자 그 사람이 빠지면 안 된다.
     (앉은 카드를 누르는 것은 여전히 「빼기」다) */
  it('끌어 놓은 뒤에 따라오는 누르기는 삼킨다', async () => {
    render(<SquadPanel card={CARD} squad={SQUAD} />)
    const seat = seatOf('김철수')
    await drag(seat, 0, 0)
    fireEvent.click(seat.querySelector('button')!)
    expect(screen.getByRole('button', { name: /김철수/ })).toBeInTheDocument()
  })

  // 사용자가 정한 포지션은 옮겨도 안 바뀐다(사용자 요청).
  it('이름표를 누르면 직접 정하고, 그 뒤로는 옮겨도 안 바뀐다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel card={CARD} squad={SQUAD} />)
    const label = () =>
      seatOf('김철수').querySelector('.ss-squad-pos') as HTMLButtonElement

    expect(label().textContent).toBe('MF')
    await user.click(label()) // 자동(MF) → FW
    expect(label().textContent).toBe('FW')
    expect(label()).toHaveAttribute('data-set', 'true')

    // 아래로 옮겨도 손으로 정한 값이 이긴다.
    await drag(seatOf('김철수'), 0, 3)
    expect(label().textContent).toBe('FW')

    // 한 바퀴 돌면 「자동」으로 돌아오고, 그때는 자리를 따른다.
    for (let i = 0; i < 4; i++) await user.click(label())
    expect(label()).not.toHaveAttribute('data-set')
    expect(label().textContent).toBe('GK')
  })
  /* 🔴 **골키퍼 줄은 가운데 한 칸뿐이다**(사용자 요청, 2026-09-08). 축구에서
     골키퍼는 하나이고 골대 앞 가운데에 선다 — 양옆 칸을 두면 판이 "골키퍼가
     셋일 수도 있다"고 말하는 셈이 된다. */
  it('골키퍼 줄에는 칸이 가운데 하나뿐이다', () => {
    render(<SquadPanel card={CARD} squad={SQUAD} />)
    const gkCells = [...document.querySelectorAll<HTMLElement>('.ss-squad-cell')].filter(
      (c) => c.dataset.row === '3',
    )
    expect(gkCells).toHaveLength(1)
    expect(gkCells[0].dataset.col).toBe('1')
  })

  it('골키퍼는 옆으로 못 간다', async () => {
    render(<SquadPanel card={CARD} squad={SQUAD} />)
    expect(posOf('이영희')).toBe('GK')
    // 골키퍼 줄의 왼쪽 끝으로 끌어 본다 — 그 칸이 없으므로 제자리다.
    await drag(seatOf('이영희'), 0, 3)
    expect(posOf('이영희')).toBe('GK')
    expect(seatOf('이영희').style.gridColumn).toBe('2')
  })

  /* ⚠️ **위아래는 막지 않는다**(사용자 결정). 자리를 통째로 잠그면 3:3 에서
     셋 다 윗줄로 올리는 「전원 FW」가 불가능해진다 — 같은 날 아침에 요청받아
     만든 동작이라 그쪽을 살렸다. 위 「셋을 다 윗줄로…」 시험이 그것을 잡는다. */
  it('골키퍼도 위로는 올라간다', async () => {
    render(<SquadPanel card={CARD} squad={SQUAD} />)
    expect(posOf('이영희')).toBe('GK')
    await drag(seatOf('이영희'), 1, 0)
    expect(posOf('이영희')).toBe('FW')
  })
})

describe('스쿼드 — 나갔다 와도 그대로다', () => {
  /* 🔴 **다른 화면에 갔다 오거나 창을 닫았다 와도 판이 그대로여야 한다**
     (사용자 요청, 2026-09-08). 판 크기 · 카드가 선 칸 · 앉은 사람 · 손으로
     정한 포지션 — 넷 다 서버에 자리가 없어 브라우저에 남긴다.
     ⚠️ `SquadPanel` 이 "브라우저 저장은 일부러 안 넣었다"고 적어 두었던 것을
     이번에 뒤집었다(lib/squadBoard.ts 첫머리에 이유를 적었다). */
  it('크기를 바꾸고 다시 그리면 그 크기로 열린다', async () => {
    const user = userEvent.setup()
    const { unmount } = render(<SquadPanel card={CARD} />)
    await user.click(screen.getByRole('radio', { name: '7 : 7' }))
    unmount()

    render(<SquadPanel card={CARD} />)
    expect(await screen.findByRole('radio', { name: '7 : 7' })).toBeChecked()
    expect(document.querySelectorAll('.ss-squad-pos')).toHaveLength(7)
  })

  it('옮긴 자리와 뺀 사람이 그대로다', async () => {
    const user = userEvent.setup()
    const { unmount } = render(<SquadPanel card={CARD} squad={SQUAD} />)

    // 김철수를 맨 윗줄로 올리고, 이영희는 뺀다.
    const seat = screen
      .getByRole('button', { name: /김철수/ })
      .closest('.ss-squad-seat') as HTMLElement
    for (const el of document.querySelectorAll<HTMLElement>('.ss-squad-cell')) {
      const col = Number(el.dataset.col)
      const row = Number(el.dataset.row)
      el.getBoundingClientRect = () =>
        ({ left: col * 100, top: row * 150, width: 100, height: 150 }) as DOMRect
    }
    fireEvent.pointerDown(seat, { button: 0, clientX: 0, clientY: 0, pointerId: 1 })
    fireEvent.pointerMove(seat, { clientX: 40, clientY: 40, pointerId: 1 })
    fireEvent.pointerUp(seat, { clientX: 50, clientY: 75, pointerId: 1 })
    await user.click(screen.getByRole('button', { name: '이영희 빼기' }))
    unmount()

    render(<SquadPanel card={CARD} squad={SQUAD} />)
    // 옮긴 자리(맨 윗줄 = FW)가 그대로다.
    expect(
      (await screen.findByRole('button', { name: /김철수/ }))
        .closest('.ss-squad-seat')!
        .querySelector('.ss-squad-pos')!.textContent,
    ).toBe('FW')
    // 🔴 뺀 사람이 되살아나면 안 된다 — 서버가 준 스쿼드에는 아직 들어 있다.
    expect(screen.queryByRole('button', { name: /이영희/ })).toBeNull()
  })

  // 저장본이 깨져 있어도 판은 그려져야 한다.
  it('저장본이 깨져 있으면 없는 것으로 치고 기본 판을 연다', async () => {
    globalThis.localStorage.setItem('supersub.squad.v1', '{"size":')
    render(<SquadPanel card={CARD} />)
    expect(screen.getByRole('radio', { name: '5 : 5' })).toBeChecked()
  })
})

describe('스쿼드 — 용병 찾기(추천 + 지인)', () => {
  function openFriends() {
    return render(<SquadPanel card={CARD} scouting />)
  }

  it('켜면 판 옆에 검색창과 지인 목록이 나온다', () => {
    openFriends()
    expect(screen.getByRole('complementary', { name: '지인 찾기' })).toBeInTheDocument()
    expect(screen.getByLabelText('지인 닉네임')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /홍길동/ })).toBeInTheDocument()
  })

  // 🔴 단추 하나가 **둘을 같이** 연다(2026-09-08). 전에는 '용병 찾기'와
  //    '지인 찾기'가 알약 둘이었고 두 판이 한 자리를 다퉜다.
  it('추천 판과 지인 판이 같이 열린다', () => {
    openFriends()
    expect(screen.getByRole('complementary', { name: /추천 선수/ })).toBeInTheDocument()
    expect(screen.getByRole('complementary', { name: '지인 찾기' })).toBeInTheDocument()
  })

  // 판 위에서 위에서 아래로 읽히는 순서가 곧 "지금 가장 급한 자리"다.
  // 내 자리(FW)는 건너뛰므로 빈 판에서는 MF 가 첫 자리다.
  it('추천은 빈 자리 중 첫 번째(MF)의 것이다', () => {
    openFriends()
    expect(screen.getByRole('heading', { name: /AI 추천 MF/ })).toBeInTheDocument()
  })

  it('닉네임을 치면 그 사람만 남는다', async () => {
    const user = userEvent.setup()
    openFriends()
    await user.type(screen.getByLabelText('지인 닉네임'), '김철')
    expect(screen.getByRole('button', { name: /김철수/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /홍길동/ })).toBeNull()
  })

  it('찾는 사람이 없으면 그렇게 적는다', async () => {
    const user = userEvent.setup()
    openFriends()
    await user.type(screen.getByLabelText('지인 닉네임'), '없는사람')
    expect(screen.getByText('찾는 지인이 없습니다')).toBeInTheDocument()
  })

  // 🔴 자리는 **왼쪽 진짜 판**에서 고른다 — 작은 스쿼드 판을 여기 하나 더
  // 그리면 판이 둘이 되고, MF 가 둘이라 포지션 이름만으로는 못 고른다.
  it('지인을 고르면 빈 자리 버튼이 넣기 버튼으로 바뀐다', async () => {
    const user = userEvent.setup()
    openFriends()
    expect(screen.getAllByRole('button', { name: /자리에 선수 넣기/ })).toHaveLength(4)

    await user.click(screen.getByRole('button', { name: /김철수/ }))
    expect(screen.getAllByRole('button', { name: /자리에 김철수 넣기/ })).toHaveLength(4)
    expect(screen.queryByRole('button', { name: /자리에 선수 넣기/ })).toBeNull()
  })

  it('빈 자리를 누르면 그 자리에 앉는다', async () => {
    const user = userEvent.setup()
    openFriends()
    await user.click(screen.getByRole('button', { name: /김철수/ }))
    await user.click(screen.getByRole('button', { name: 'GK 자리에 김철수 넣기' }))

    expect(screen.getByRole('button', { name: '김철수 빼기' })).toBeInTheDocument()
    // 여러 명을 이어 넣는 게 보통이라 판은 열어 둔다.
    expect(screen.getByRole('complementary', { name: '지인 찾기' })).toBeInTheDocument()
  })

  it('고른 사람을 한 번 더 누르면 고르기가 풀린다', async () => {
    const user = userEvent.setup()
    openFriends()
    const row = screen.getByRole('button', { name: /김철수/ })
    await user.click(row)
    await user.click(row)
    expect(screen.getAllByRole('button', { name: /자리에 선수 넣기/ })).toHaveLength(4)
  })

  /* 🔴 예전 규칙("지인이 열려 있으면 추천을 안 연다")을 **일부러 뒤집었다** —
     두 판이 같은 좌표에 서 있어서 둘 중 하나만 그릴 수밖에 없었던 것이고,
     이제는 칸이 갈렸다. 되돌리지 말 것. */
  it('열려 있는 동안 다른 빈 자리를 누르면 그 자리의 추천으로 바뀐다', async () => {
    const user = userEvent.setup()
    openFriends()
    await user.click(screen.getByRole('button', { name: 'GK 자리에 선수 넣기' }))
    expect(screen.getByRole('heading', { name: /AI 추천 GK/ })).toBeInTheDocument()
    expect(screen.getByRole('complementary', { name: '지인 찾기' })).toBeInTheDocument()
  })

  // 🔴 표식이 없으면 방금 넣은 사람이 평범한 줄로 남아 또 고르게 된다.
  it('이미 넣은 사람은 목록에서 자리 이름과 함께 잠긴다', async () => {
    const user = userEvent.setup()
    openFriends()
    await user.click(screen.getByRole('button', { name: /김철수/ }))
    await user.click(screen.getByRole('button', { name: 'GK 자리에 김철수 넣기' }))

    const row = screen.getByRole('button', { name: /김철수.*GK/ })
    expect(row).toBeDisabled()
    // 다른 사람은 그대로 고를 수 있다.
    expect(screen.getByRole('button', { name: /홍길동/ })).toBeEnabled()
  })

  it('빼면 목록에서 다시 고를 수 있다', async () => {
    const user = userEvent.setup()
    openFriends()
    await user.click(screen.getByRole('button', { name: /김철수/ }))
    await user.click(screen.getByRole('button', { name: 'GK 자리에 김철수 넣기' }))
    await user.click(screen.getByRole('button', { name: '김철수 빼기' }))

    expect(screen.getByRole('button', { name: /김철수/ })).toBeEnabled()
  })

  // 카드 전체가 이미 '빼기' 버튼이다 — 표식은 장식이라 버튼이 아니어야 한다.
  it('넣은 자리에는 빼기 표식이 붙는다', async () => {
    const user = userEvent.setup()
    const { container } = openFriends()
    expect(container.querySelector('.ss-squad-remove')).toBeNull()

    await user.click(screen.getByRole('button', { name: /김철수/ }))
    await user.click(screen.getByRole('button', { name: 'GK 자리에 김철수 넣기' }))

    const badge = container.querySelector('.ss-squad-remove')
    expect(badge).not.toBeNull()
    expect(badge).toHaveAttribute('aria-hidden', 'true')
    expect(badge?.closest('button')).toBe(screen.getByRole('button', { name: '김철수 빼기' }))
  })

  /* 🔴 첫째 칸은 하나만 쓴다 — 빈 자리로 연 추천도 챗봇이 닫아야 한다.
     ⚠️ 그 추천은 `scouting` 이 아니라 판이 제 상태로 들고 있어서, 알약으로
     연 경우만 닫히고 **빈 자리로 연 경우에는 AI 판이 뒤에 나왔다**(실제로
     겪었다). 되돌리지 말 것. */
  it('빈 자리로 연 추천도 챗봇이 켜지면 닫힌다', async () => {
    const user = userEvent.setup()
    const { rerender } = render(<SquadPanel card={CARD} />)
    await user.click(screen.getByRole('button', { name: 'GK 자리에 선수 넣기' }))
    expect(screen.getByRole('complementary', { name: /추천 선수/ })).toHaveAttribute(
      'data-state',
      'open',
    )

    rerender(<SquadPanel card={CARD} bot />)
    // 판은 물러나는 동안 DOM 에 남는다 — 사라진 것을 세지 말고 접혔는지 본다.
    expect(screen.getByRole('complementary', { name: /추천 선수/ })).toHaveAttribute(
      'data-state',
      'closing',
    )
  })

  it('닫기를 누르면 부모에게 알린다', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(<SquadPanel card={CARD} scouting onCloseScouting={onClose} />)
    await user.click(screen.getByRole('button', { name: '지인 찾기 닫기' }))
    expect(onClose).toHaveBeenCalled()
  })

  // 🔴 한 단추가 연 한 벌이라 어느 쪽 ×를 눌러도 짝으로 접힌다. 추천만 닫고
  //    지인을 남기면 알약은 켜진 채라 다시 눌러도 안 열린다.
  it('추천 판의 닫기를 눌러도 같은 곳에 알린다', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(<SquadPanel card={CARD} scouting onCloseScouting={onClose} />)
    await user.click(screen.getByRole('button', { name: '추천 닫기' }))
    expect(onClose).toHaveBeenCalled()
  })

})
