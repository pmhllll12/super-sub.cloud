import { useState } from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { PlayerCard, Squad } from '@/server/backend'
import SquadPanel from './SquadPanel'

/** 서버가 준 스쿼드 — MF 둘과 GK 하나가 등재돼 있다. */
const SQUAD: Squad = {
  id: 'sq1',
  team_id: 't1',
  public_slug: 'aB3xK9mQ2pL7vN4t',
  formation: null,
  members: [
    {
      id: 'sm1',
      player_card_id: 'c9',
      card_public_slug: 'kim-4f2a',
      nickname: '김철수',
      position_code: 'MF',
      position_label: '미드필더',
      grid_col: null,
      grid_row: null,
    },
    {
      id: 'sm2',
      player_card_id: 'c8',
      card_public_slug: 'lee-1a2b',
      nickname: '이영희',
      position_code: 'GK',
      position_label: '골키퍼',
      grid_col: null,
      grid_row: null,
    },
  ],
}

const CARD: PlayerCard = {
  id: 'c1',
  public_slug: 'hong-gildong-4f2a',
  og_image_key: 'cards/7b4d.png',
  user: { id: 'u1', nickname: '홍길동' },
  titles: [],
  tagline: null,
  style: null,
}

/**
 * 🔴 **내 등재**(2026-09-16, 사용자 설계). 전에는 포메이션 상수의 FW 한 칸에
 * `mine: true` 가 박혀 있어 **아무 등재가 없어도** 내 카드가 판에 서 있었다.
 * 이제 내 카드가 서는 조건은 둘뿐이다:
 *
 *   1) 서버 스쿼드에 **내 카드 슬러그**의 등재가 있고 **칸(grid_col/row)이
 *      저장돼 있다** — 그 칸의 자리에 `mine` 이 붙는다
 *   2) 빈 자리의 「나」 표식을 눌러 내가 앉힌다
 *
 * 그래서 「내 자리가 있어야 뜻이 서는」 시험들은 이 등재를 세워 둔다.
 */
const meAt = (col: number, row: number, position_code = 'FW'): Squad['members'][number] => ({
  id: 'sm-me',
  player_card_id: CARD.id,
  card_public_slug: CARD.public_slug,
  nickname: '홍길동',
  position_code,
  position_label: position_code,
  grid_col: col,
  grid_row: row,
})

/** 나만 선 판 — 내 카드가 FW 자리(1,0)에 서 있고 나머지 넷은 빈 자리다. */
const SQUAD_WITH_ME: Squad = { ...SQUAD, members: [meAt(1, 0)] }

/**
 * 추천 후보 — **서버에서 온다**(2026-09-16, 계약 3-16절). 전에는
 * `SquadSuggest.tsx` 안의 붙박이라 시험이 아무것도 안 세워도 됐다.
 *
 * 🔴 여기서 세우는 것은 **계약이 정한 응답 모양**이다. `provisional` 이
 * 섞여 있어야 「검수 전」 배지 갈래를 밟는다(정상호 조건).
 */
const MY_TEAM_ID = 'team-mine'

const CANDIDATES: Record<string, unknown[]> = {
  GK: [
    { user_id: 'u1', nickname: '김선우', card_public_slug: 'a', grade: 'A', provisional: true },
    { user_id: 'u2', nickname: '오재현', card_public_slug: 'b', grade: 'C', provisional: true },
  ],
  MF: [
    { user_id: 'u3', nickname: '최유진', card_public_slug: 'c', grade: 'A', provisional: true },
    { user_id: 'u4', nickname: '강태원', card_public_slug: 'd', grade: 'B', provisional: false },
    { user_id: 'u5', nickname: '윤서준', card_public_slug: 'e', grade: 'C', provisional: true },
  ],
  DF: [
    { user_id: 'u6', nickname: '박도현', card_public_slug: 'f', grade: 'S', provisional: false },
  ],
  FW: [
    { user_id: 'u7', nickname: '조현우', card_public_slug: 'g', grade: 'F', provisional: false },
  ],
}

/** 후보 경로만 세운다 — 나머지 요청은 빈 것으로 답한다. */
function stubCandidates() {
  vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
    const url = String(input)
    const json = (b: unknown) => Promise.resolve(new Response(JSON.stringify(b), { status: 200 }))
    if (url.includes('/squad/candidates')) {
      const q = new URL(url, 'http://t').searchParams
      const pos = q.get('position_code') ?? ''
      const grade = q.get('grade')
      const rows = (CANDIDATES[pos] ?? []) as { grade: string }[]
      return json(grade ? rows.filter((r) => r.grade === grade) : rows)
    }
    if (url.startsWith('/api/me/contacts/requests')) return json([])
    if (url.startsWith('/api/me/contacts')) return json({ items: [] })
    return json([])
  })
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
  /* 🔴 정정 (2026-09-16, 사용자 설계): 전에는 포메이션 상수에 `mine: true` 가
     박혀 있어 **아무것도 안 해도** 내 카드가 FW 자리에 서 있었고, 그래서 이
     시험이 `card` 만 넘겨도 다섯 장(내 카드 + 빈 카드 넷)이 나왔다. 이제는
     **칸이 저장된 내 등재**가 있어야 서므로 그것을 세워 두고 본다 — 세는 것
     (다섯 장 · 빈 자리 넷)은 그대로다. 아무도 안 선 처음 판은 아래
     「내 카드는 내가 앉힌다」 describe 가 따로 잡는다. */
  it('판 위에 카드 다섯 장을 포지션 자리대로 앉힌다', () => {
    const { container } = render(
      <SquadPanel card={CARD} squad={SQUAD_WITH_ME} myCardId={CARD.id} />,
    )
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
    stubCandidates()
    render(<SquadPanel card={CARD} myTeamId={MY_TEAM_ID} />)
    await user.click(screen.getByRole('button', { name: 'GK 자리에 선수 넣기' }))
    expect(screen.getByRole('complementary', { name: 'GK 추천 선수' })).toBeInTheDocument()
    // 제목이 곧 몇 명이 왔는지다 — 자리마다 추천 수가 다르다.
    expect(screen.getByRole('heading', { name: 'AI 추천 GK 2명' })).toBeInTheDocument()
    // 이름을 적는 칸은 없다.
    expect(screen.queryByRole('textbox')).toBeNull()
  })

  it('자리마다 다른 추천이, 다른 수만큼 나온다', async () => {
    const user = userEvent.setup()
    stubCandidates()
    render(<SquadPanel card={CARD} myTeamId={MY_TEAM_ID} />)
    await user.click(screen.getAllByRole('button', { name: 'MF 자리에 선수 넣기' })[0])
    expect(screen.getByRole('heading', { name: 'AI 추천 MF 3명' })).toBeInTheDocument()
    expect(screen.getAllByRole('listitem')).toHaveLength(3)
  })

  it('추천에서 고르면 그 자리에 앉고 판이 닫힌다', async () => {
    const user = userEvent.setup()
    stubCandidates()
    render(<SquadPanel card={CARD} myTeamId={MY_TEAM_ID} />)
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
    stubCandidates()
    render(<SquadPanel card={CARD} myTeamId={MY_TEAM_ID} />)
    await user.click(screen.getByRole('button', { name: 'DF 자리에 선수 넣기' }))
    await user.click(screen.getByRole('button', { name: /박도현/ }))
    await user.click(screen.getByRole('button', { name: '박도현 빼기' }))
    expect(screen.getByRole('button', { name: 'DF 자리에 선수 넣기' })).toBeInTheDocument()
  })

  /* 🔴 **정정 (2026-09-17, 사용자 판단)**: 09-16 에는 「나」 표식을 눌러야
     내 자리가 섰지만, 이제 **팀장은 FW 에 저절로 앉는다** — 그래서 아무것도
     안 눌러도 그 자리가 잡히고, 카드가 없으면 그 자리에 「아직 카드가
     없습니다」가 적힌다는 것이 이 시험의 뜻이다. */
  it('내 카드가 없으면 그 자리에 그렇게 적는다', async () => {
    const { container } = render(<SquadPanel card={null} myCardId="c1" />)

    await waitFor(() =>
      expect(screen.getByText('아직 카드가 없습니다')).toBeInTheDocument(),
    )
    expect(container.querySelectorAll('.ss-pcard')).toHaveLength(5)
  })
})

/**
 * 🔴 **팀장은 FW 에 먼저 앉는다**(사용자 판단, 2026-09-17).
 *
 * **정정**: 하루 전(09-16)에는 「내 카드는 내가 앉힌다」였다 — 처음 판이 비어
 * 있고 빈 자리를 눌러 뜨는 **「나」 표식**을 눌러야 섰다. 그 표식을 **없앴다.**
 * 팀을 만든 사람은 **뛴다고 보고 일단 FW 에 앉혀 놓고 시작한다** — 옮기든 빼든
 * 그건 그다음 일이다.
 *
 * 여기 시험들이 그 새 규칙을 하나씩 붙든다.
 */
describe('스쿼드 — 팀장은 FW 에 먼저 앉는다', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  /** 무엇이 어디로 나갔는지만 보는 서버 대역. */
  function server() {
    const fn = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => SQUAD })
    vi.stubGlobal('fetch', fn)
    return fn
  }
  const sent = (fn: ReturnType<typeof vi.fn>, method: string) =>
    fn.mock.calls
      .filter((c) => c[1]?.method === method)
      .map((c) => ({ url: c[0] as string, body: c[1].body ? JSON.parse(String(c[1].body)) : null }))

  // ① 아무것도 안 눌러도 내 카드가 FW 에 서 있다 — 이번 결정의 출발점이다.
  it('처음 판에 내 카드가 FW 에 서 있다', async () => {
    const { container } = render(<SquadPanel card={CARD} myCardId={CARD.id} />)
    await waitFor(() =>
      expect(container.querySelectorAll('[data-mine="true"]')).toHaveLength(1),
    )
    const mine = container.querySelector('[data-mine="true"]') as HTMLElement
    expect(mine.querySelector('.ss-squad-pos')!.textContent).toBe('FW')
    // 내 카드가 그려졌다 — 이름표가 선 「남이 앉은 카드」가 아니다.
    expect(screen.getByText('THREE LUNGS')).toBeInTheDocument()
  })

  /* 🔴 **「나」 표식은 이제 없다.** 빈 자리를 눌러도 안 뜬다 — 한 번 있었던
     것이라 시험으로 막는다. */
  it('「나」 표식은 어디에도 없다', async () => {
    const user = userEvent.setup()
    const { container } = render(<SquadPanel card={CARD} myCardId={CARD.id} />)
    await waitFor(() => expect(container.querySelector('[data-mine="true"]')).toBeTruthy())

    await user.click(screen.getByRole('button', { name: 'GK 자리에 선수 넣기' }))
    expect(container.querySelector('.ss-squad-me')).toBeNull()
    expect(screen.queryByRole('button', { name: /내 카드 넣기/ })).toBeNull()
  })

  // ② 자동으로 앉은 것도 **서버에 남는다** — 새로고침하면 사라지면 안 된다.
  it('자동으로 앉은 자리도 서버에 등재한다', async () => {
    const fn = server()
    render(<SquadPanel card={CARD} squad={SQUAD} myCardId={CARD.id} />)

    await waitFor(() =>
      expect(sent(fn, 'POST')).toContainEqual({
        url: '/api/teams/t1/squad/members',
        body: { player_card_id: 'c1', position_code: 'FW', grid_col: 1, grid_row: 0 },
      }),
    )
  })

  /**
   * 🔴 **내 카드에는 ⊗ 가 없다**(사용자 판단, 2026-09-17). 팀을 만든 사람은
   * **뛴다는 가정**이라 판에서 빠질 일이 없다 — 뺄 수 있게 두면 「안 뛴다」가
   * 표현되는데, 그것을 담을 자리가 서버에도 없다. 남의 카드는 그대로 ⊗ 로 뺀다.
   */
  it('내 카드에는 빼기 단추가 없다', async () => {
    const { container } = render(
      <SquadPanel card={CARD} squad={SQUAD_WITH_ME} myCardId={CARD.id} />,
    )
    expect(container.querySelector('[data-mine="true"]')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '나를 판에서 빼기' })).toBeNull()
  })

  // ③ 크기를 바꿔도 내 자리는 남는다(사용자 지적: "x 누르지 않는 이상 계속 유지").
  it('판 크기를 바꿔도 내 자리는 남는다', async () => {
    const user = userEvent.setup()
    const { container } = render(<SquadPanel card={CARD} myCardId={CARD.id} />)
    await waitFor(() => expect(container.querySelector('[data-mine="true"]')).toBeTruthy())

    for (const s of ['3 : 3', '7 : 7', '5 : 5']) {
      await user.click(screen.getByRole('radio', { name: s }))
      expect(container.querySelectorAll('[data-mine="true"]')).toHaveLength(1)
      // 내 카드가 그대로 그려진다 — 이름표가 선 「남이 앉은 카드」가 아니다.
      expect(screen.getByText('THREE LUNGS')).toBeInTheDocument()
    }
  })

  /* 🔴 **남을 앉히면 「수락 대기중」이다**(사용자 설계) — 추천·지인에서 고른
     사람은 팀 밖 사람이라 바로 뛰는 것이 아니다. 내 카드에는 안 붙는다:
     나는 수락을 기다릴 상대가 아니다. */
  it('남을 앉히면 그 카드 위에 「수락 대기중」이 뜬다', async () => {
    const user = userEvent.setup()
    stubCandidates()
    const { container } = render(
      <SquadPanel card={CARD} squad={SQUAD_WITH_ME} myCardId={CARD.id} myTeamId={MY_TEAM_ID} />,
    )
    expect(container.querySelector('.ss-squad-pending')).toBeNull()

    await user.click(screen.getByRole('button', { name: 'DF 자리에 선수 넣기' }))
    await user.click(screen.getByRole('button', { name: /박도현/ }))

    const badge = screen.getByText('수락 대기중')
    expect(badge.closest('.ss-squad-seat')).toBe(
      screen.getByRole('button', { name: '박도현 빼기' }).closest('.ss-squad-seat'),
    )
    // 내 카드는 기다릴 것이 없다 — 표식이 하나뿐이다.
    expect(container.querySelectorAll('.ss-squad-pending')).toHaveLength(1)
  })

  /**
   * 🔴 **앉은 사람도 제 카드가 뜬다** (2026-09-17, 사용자 지적 — 「그 사람을
   * 추가하면 그 사람 카드가 같이 실제로 떠야 하잖아」).
   *
   * 전에는 이름만 적은 **빈 카드**였다. 이제 등재의 `card_public_slug` 로
   * `GET /cards/{slug}` 를 읽어 그 사람 카드를 그린다.
   */
  it('앉은 사람의 진짜 카드를 그린다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((url: string) =>
        Promise.resolve(
          String(url).startsWith('/api/cards/')
            ? {
                ok: true,
                status: 200,
                json: async () => ({
                  public_slug: 'kim-4f2a',
                  og_image_key: 'k.png',
                  user: { id: 'u9', nickname: '김철수' },
                  titles: [],
                  tagline: '피자보다 축구',
                  style: null,
                }),
              }
            : { ok: true, status: 200, json: async () => SQUAD },
        ),
      ),
    )
    render(<SquadPanel card={CARD} squad={SQUAD} myCardId={CARD.id} />)

    /* 카드에만 있는 글(별칭)이 보이면 진짜 카드가 그려진 것이다.
       ⚠️ 대역이 슬러그와 무관하게 같은 카드를 주므로 **앉은 사람 수만큼** 나온다
       — `findAllByText` 로 받는다(하나로 받으면 「여럿 찾음」으로 튕긴다). */
    expect((await screen.findAllByText('피자보다 축구')).length).toBeGreaterThan(0)
    // 빈 카드에 이름만 찍히던 자리가 아니다.
    expect(document.querySelectorAll('.ss-pcard-alias').length).toBeGreaterThan(0)
  })

  /* 🔴 **못 알아보는 응답이면 이름표로 남는다** — 엉뚱한 것을 카드 자리에
     넣으면 판이 통째로 안 그려진다. 못 그리는 것보다 이름이라도 남는 쪽이다. */
  it('카드를 못 읽으면 이름표로 남는다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((url: string) =>
        Promise.resolve(
          String(url).startsWith('/api/cards/')
            ? { ok: false, status: 404, json: async () => ({}) }
            : { ok: true, status: 200, json: async () => SQUAD },
        ),
      ),
    )
    render(<SquadPanel card={CARD} squad={SQUAD} myCardId={CARD.id} />)
    expect(await screen.findByText('김철수')).toBeInTheDocument()
  })

  /* 🔴 **「준비 완료」는 없앴다**(사용자 판단, 2026-09-17). 이 표시는 「아직
     수락 안 했다」를 말하는 자리지 다 된 것을 자랑하는 자리가 아니다 —
     기다리는 것만 말하고 된 것은 조용히 둔다. */
  it('수락된 사람에게는 아무 표식도 안 붙는다', () => {
    const { container } = render(
      <SquadPanel card={CARD} squad={SQUAD} myCardId={CARD.id} />,
    )
    // SQUAD 의 사람들은 이미 등재된 팀원이라 기다릴 것이 없다.
    expect(screen.queryByText('준비 완료')).toBeNull()
    expect(container.querySelector('.ss-squad-pending')).toBeNull()
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

/**
 * 🔴 **판 배치는 2026-09-10 부터 서버가 쥔다**(CCC 25, 미결 `paik` 9번).
 *
 * 09-08 에는 `localStorage` 뿐이라 **다른 기기에서는 늘 처음 판**이었다.
 * 이제 판 크기 · 칸 · 포지션 셋이 계약에 자리가 있어서, 이 시험들도 저장소
 * 왕복이 아니라 **계약(`PATCH …/squad` · `PATCH …/squad/members/{id}`)** 을
 * 붙든다.
 */
/**
 * 🔴 **2026-09-10 회귀** — 서버 칸으로 자리를 놓기 시작하면서 홈 첫 화면의
 * 판이 깨졌다. 카드 한 장이 사라지고 **내 카드도 안 보였다**(사용자 지적).
 *
 * 원인 둘:
 *   1) `mine` 자리를 「찬 칸」으로 안 셌다 — 내 카드 위로 남의 카드를 옮겼다
 *   2) 그 칸에 있는 자리를 안 쓰고 **아무 빈 자리나** 끌어다 옮겼다 —
 *      자리들이 뒤엉키며 원래 그 칸에 있던 것이 밀려나 겹쳤다
 */
/**
 * **팀 매칭 단추** — 판이 다 차면 켜지고 깜빡인다(사용자 요청, 2026-09-10).
 *
 * 🔴 **크기와 무관하다**(사용자 결정) — 3:3 으로 할지 7:7 로 할지는 팀장이
 * 정하는 것이라, **고른 크기가** 다 차면 켜진다.
 */
describe('스쿼드 — 팀 매칭 단추', () => {
  const btn = () => screen.getByRole('button', { name: '팀 매칭' })
  /**
   * 자리 다섯을 채운 5:5 스쿼드.
   *
   * 🔴 정정 (2026-09-16, 사용자 설계): 전에는 내 자리가 포메이션에 박혀 있어
   * **넷만 등재해도 다섯 자리가 찼다.** 이제 내 카드는 등재(+칸)가 있어야
   * 서므로 **나도 한 줄로 등재한다**(`meAt`) — 「다 찼다」를 세는 시험이니
   * 내가 판에 서 있는 쪽이 이 시험의 뜻에 맞는다.
   */
  const member = (id: string, nickname: string, pos: string, col: number, row: number) => ({
    id,
    player_card_id: `c-${id}`,
    card_public_slug: `slug-${id}`,
    nickname,
    position_code: pos,
    position_label: pos,
    grid_col: col,
    grid_row: row,
  })
  const FULL5 = {
    ...SQUAD,
    formation: '5:5',
    members: [
      // 내 자리(FW, 1행 0열) — 이것이 있어야 다섯 자리가 다 찬다.
      meAt(1, 0),
      member('a', '김철수', 'MF', 0, 1),
      member('b', '이영희', 'MF', 2, 1),
      member('c', '박민수', 'DF', 1, 2),
      member('d', '최지훈', 'GK', 1, 3),
    ],
  }

  /* 🔴 **자리를 늘 잡아 둔다** — 안 그리면 마지막 자리를 채우는 순간 크기
     단추가 옆으로 튄다. 그래서 「없다」가 아니라 「숨어 있다」로 확인한다. */
  it('덜 찼으면 숨어 있고 접근성 트리에서도 빠진다', () => {
    render(<SquadPanel card={CARD} squad={SQUAD} />)
    const el = document.querySelector('.ss-squad-match') as HTMLElement
    expect(el).toBeInTheDocument()
    expect(el.style.visibility).toBe('hidden')
    expect(el).toHaveAttribute('aria-hidden', 'true')
    expect(screen.queryByRole('button', { name: '팀 매칭' })).toBeNull()
  })

  it('다 차면 나타나고 깜빡인다', () => {
    render(<SquadPanel card={CARD} squad={FULL5} />)
    expect(btn()).toBeInTheDocument()
    expect(btn()).toHaveAttribute('data-blink', 'true')
  })

  /* 🔴 **내 자리도 한 자리로 센다.** 안 세면 5:5 를 다 채워도 넷으로 세어
     단추가 영영 안 켜진다. 3:3 은 내 자리 + 둘이면 다 찬 것이다.
     정정 (2026-09-16, 사용자 설계): 그 「내 자리」가 이제 공짜가 아니다 —
     내 등재(`meAt`)를 세워야 판에 선다. */
  it('3:3 도 다 차면 켜진다', () => {
    render(
      <SquadPanel
        card={CARD}
        myCardId={CARD.id}
        squad={{
          ...SQUAD,
          formation: '3:3',
          members: [
            meAt(1, 0),
            member('a', '김철수', 'MF', 1, 1),
            member('b', '이영희', 'GK', 1, 3),
          ],
        }}
      />,
    )
    expect(btn()).toBeInTheDocument()
  })

  it('7:7 은 여섯을 채워야 켜진다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel card={CARD} squad={FULL5} />)
    // 5:5 로는 찼지만 7:7 로 늘리면 두 자리가 빈다.
    await user.click(screen.getByRole('radio', { name: '7 : 7' }))
    expect(screen.queryByRole('button', { name: '팀 매칭' })).toBeNull()
  })

  it('누르면 비슷한 팀 명단이 열린다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel card={CARD} squad={FULL5} />)
    await user.click(btn())
    expect(screen.getByRole('region', { name: '비슷한 팀' })).toBeInTheDocument()
  })

  /* 🔴 **「팀원」일 때는 안 나온다**(사용자 지적, 2026-09-10). 그쪽은 *남의
     팀에 들어가는* 자리라 우리 팀이 상대를 찾을 일이 없다 — 판도 물러나 있다. */
  it('팀원 판이 서 있으면 단추가 안 나온다', () => {
    render(<SquadPanel card={CARD} squad={FULL5} seeking />)
    expect(screen.queryByRole('button', { name: '팀 매칭' })).toBeNull()
  })

  /* 열어 둔 채로 「팀원」으로 넘어가면 명단도 물러난다 — 단추가 사라지는데
     판만 남으면 닫을 길이 그 판의 × 뿐이다. */
  it('열어 둔 채로 팀원으로 넘어가면 명단도 물러난다', async () => {
    const user = userEvent.setup()
    const { rerender } = render(<SquadPanel card={CARD} squad={FULL5} />)
    await user.click(btn())
    expect(screen.getByRole('region', { name: '비슷한 팀' })).toBeInTheDocument()

    rerender(<SquadPanel card={CARD} squad={FULL5} seeking />)
    expect(screen.queryByRole('region', { name: '비슷한 팀' })).toBeNull()
  })

  /* 알약 줄로 올라오면서 명단(판 오른쪽)과 **더는 안 겹치므로**, 열려 있는
     동안에도 그대로 있고 한 번 더 누르면 닫는다. */
  it('한 번 더 누르면 닫힌다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel card={CARD} squad={FULL5} />)
    await user.click(btn())
    expect(screen.getByRole('region', { name: '비슷한 팀' })).toBeInTheDocument()

    await user.click(btn())
    expect(screen.queryByRole('region', { name: '비슷한 팀' })).toBeNull()
  })

  it('× 로도 닫힌다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel card={CARD} squad={FULL5} />)
    await user.click(btn())
    await user.click(
      screen.getByRole('region', { name: '비슷한 팀' }).querySelector('.ss-tm-close') as HTMLElement,
    )
    expect(screen.queryByRole('region', { name: '비슷한 팀' })).toBeNull()
  })

  /* 🔴 **머리줄은 한 픽셀도 안 건드린다** — 단추를 그 줄에 넣었더니 크기
     단추가 가운데로 밀렸다(사용자 지적, 2026-09-10). 판 바깥 절대배치다. */
  it('크기 단추가 있는 머리줄 밖에 있다', () => {
    render(<SquadPanel card={CARD} squad={FULL5} />)
    const head = document.querySelector('.ss-squad-head, header') as HTMLElement
    expect(head.querySelector('.ss-squad-match')).toBeNull()
    expect(head.querySelector('.ss-squad-size')).toBeInTheDocument()
  })
})

describe('스쿼드 — 서버 칸을 놓아도 판이 안 깨진다', () => {
  const at = (col: number, row: number) => ({ grid_col: col, grid_row: row })
  const member = (over: Partial<Squad['members'][number]>) => ({
    id: 'x',
    player_card_id: 'c0',
    card_public_slug: 'slug',
    nickname: '누구',
    position_code: 'MF',
    position_label: '미드필더',
    grid_col: null,
    grid_row: null,
    ...over,
  })
  /** 판 위에 실제로 그려진 카드 수 — 내 카드 + 빈 카드 + 앉은 카드. */
  const cards = () => document.querySelectorAll('.ss-pcard').length
  /** 두 자리가 같은 칸에 겹쳐 있지 않은가. */
  function noOverlap() {
    const seen = new Set<string>()
    for (const el of document.querySelectorAll<HTMLElement>('.ss-squad-seat')) {
      const key = `${el.style.gridColumn}:${el.style.gridRow}`
      expect(seen.has(key), `${key} 에 자리가 둘`).toBe(false)
      seen.add(key)
    }
  }

  /* 🔴 데모 계정의 스쿼드가 정확히 이 모양이다 — 목록에 **나 자신**이 들어
     있고 그 칸이 내 자리(1,0)다. 여기서 판이 깨졌다.

     정정 (2026-09-16, 사용자 설계): 전에는 그 칸이 포메이션의 `mine` 자리라
     **슬러그를 안 맞춰도** 「이미 찬 칸」으로 걸러졌다. 이제 나를 가리는
     열쇠는 **카드 슬러그뿐**이고, 그 칸이 곧 내가 서는 자리다 — 그래서 이
     등재에 내 슬러그를 박는다. 보는 것(겹치지 않는다 · 내 카드가 남는다 ·
     내가 두 번 안 나온다)은 그대로다. */
  it('목록에 내가 들어 있어도 내 카드를 덮지 않는다', () => {
    render(
      <SquadPanel
        card={CARD}
        myCardId={CARD.id}
        squad={{
          ...SQUAD,
          members: [
            member({
              id: 'sm1',
              nickname: '홍길동',
              card_public_slug: CARD.public_slug,
              position_code: 'FW',
              ...at(1, 0),
            }),
            member({ id: 'sm2', nickname: '김철수', ...at(0, 1) }),
            member({ id: 'sm3', nickname: '이영희', position_code: 'GK' }),
          ],
        }}
      />,
    )
    // 5:5 판은 늘 다섯 장이다 — 한 장이라도 겹쳐 사라지면 안 된다.
    expect(cards()).toBe(5)
    noOverlap()
    /* 🔴 **내 카드가 판에 남아 있다.** 남의 카드를 그 칸으로 옮기면 이것이
       덮인다 — 그게 사용자가 본 「내 카드가 안 보인다」였다. */
    expect(document.querySelector('[data-mine="true"]')).toBeInTheDocument()
    /* 🔴 **나는 두 번 안 나온다.** 서버 목록에 내가 들어 있어도 내 자리는
       `card` 가 그리므로, 그 등재는 앉히지 않는 것이 원래 규칙이다. */
    expect(screen.queryByRole('button', { name: /홍길동 빼기/ })).toBeNull()
    expect(screen.getByText('김철수')).toBeInTheDocument()
    expect(screen.getByText('이영희')).toBeInTheDocument()
  })

  /* 🔴 **그 칸에 있는 자리를 먼저 쓴다.** 아무 빈 자리나 끌어다 옮기면
     원래 그 칸에 있던 자리가 밀려나며 겹친다. */
  it('저장된 칸에 있는 자리를 그대로 쓴다', () => {
    render(
      <SquadPanel
        card={CARD}
        squad={{
          ...SQUAD,
          members: [
            member({ id: 'sm2', nickname: '김철수', ...at(0, 1) }),
            member({ id: 'sm4', nickname: '박영수', ...at(2, 1) }),
          ],
        }}
      />,
    )
    expect(cards()).toBe(5)
    noOverlap()
    const seat = (name: string) =>
      screen.getByText(name).closest('.ss-squad-seat') as HTMLElement
    expect(seat('김철수').style.gridColumn).toBe('1')
    expect(seat('박영수').style.gridColumn).toBe('3')
  })
})

describe('스쿼드 — 판 배치가 서버에 남는다', () => {
  /** 무엇이 어디로 나갔는지만 보는 서버 대역. 응답은 안 쓴다(판은 제 상태로 돈다). */
  function server() {
    const fn = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => SQUAD })
    vi.stubGlobal('fetch', fn)
    return fn
  }
  const patches = (fn: ReturnType<typeof vi.fn>) =>
    fn.mock.calls
      .filter((c) => c[1]?.method === 'PATCH')
      .map((c) => ({ url: c[0] as string, body: JSON.parse(String(c[1].body)) }))

  function layout() {
    for (const el of document.querySelectorAll<HTMLElement>('.ss-squad-cell')) {
      const col = Number(el.dataset.col)
      const row = Number(el.dataset.row)
      el.getBoundingClientRect = () =>
        ({ left: col * 100, top: row * 150, width: 100, height: 150 }) as DOMRect
    }
  }
  function drag(seat: HTMLElement, col: number, row: number) {
    layout()
    fireEvent.pointerDown(seat, { button: 0, clientX: 0, clientY: 0, pointerId: 1 })
    fireEvent.pointerMove(seat, { clientX: 40, clientY: 40, pointerId: 1 })
    fireEvent.pointerUp(seat, { clientX: col * 100 + 50, clientY: row * 150 + 75, pointerId: 1 })
  }
  const seatOf = (name: string) =>
    screen.getByRole('button', { name: new RegExp(name) }).closest('.ss-squad-seat') as HTMLElement

  afterEach(() => vi.unstubAllGlobals())

  /* 🔴 **다른 기기에서도 같은 판이 열린다** — 이 항목의 요점이다. 서버가 준
     `formation` 이 곧 판 크기다. */
  it('서버가 준 판 크기로 열린다', () => {
    render(<SquadPanel card={CARD} squad={{ ...SQUAD, formation: '7:7' }} />)
    expect(screen.getByRole('radio', { name: '7 : 7' })).toBeChecked()
    expect(document.querySelectorAll('.ss-squad-pos')).toHaveLength(7)
  })

  /* 🔴 계약이 값 집합을 강제하지 않아(길이만 본다) **화면이 모르는 크기가 올 수
     있다.** 그때 판이 안 그려지면 안 된다. */
  it('모르는 판 크기면 기본 판을 연다', () => {
    render(<SquadPanel card={CARD} squad={{ ...SQUAD, formation: '9:9' }} />)
    expect(screen.getByRole('radio', { name: '5 : 5' })).toBeChecked()
  })

  it('크기를 바꾸면 그 팀의 스쿼드에 남긴다', async () => {
    const fn = server()
    const user = userEvent.setup()
    render(<SquadPanel card={CARD} squad={SQUAD} />)
    await user.click(screen.getByRole('radio', { name: '7 : 7' }))

    await waitFor(() => expect(patches(fn)).toContainEqual({
      url: '/api/teams/t1/squad',
      body: { formation: '7:7' },
    }))
  })

  /* 🔴 칸은 **격자 번호**로 나간다 — 화면 픽셀이 아니다(계약 3-7절). 포지션도
     함께 실린다: 등재는 포지션 없이 존재하지 않는다. */
  it('카드를 옮기면 그 칸과 포지션을 등재에 남긴다', async () => {
    const fn = server()
    render(<SquadPanel card={CARD} squad={SQUAD} />)
    drag(seatOf('김철수'), 0, 0)

    await waitFor(() => expect(patches(fn)).toContainEqual({
      url: '/api/teams/t1/squad/members/sm1',
      body: { position_code: 'FW', grid_col: 0, grid_row: 0 },
    }))
  })

  /* 🔴 **맞바꾼 둘 다 남긴다.** 옮긴 쪽만 보내면 밀려난 사람의 칸이 서버에
     옛 자리로 남아, 다음에 열 때 두 카드가 한 칸에 겹친다. */
  it('자리를 맞바꾸면 둘 다 남긴다', async () => {
    const fn = server()
    render(<SquadPanel card={CARD} squad={SQUAD} />)
    // 김철수(0,1) 를 이영희가 선 골키퍼 칸(1,3) 으로 — 둘이 자리를 바꾼다.
    drag(seatOf('김철수'), 1, 3)

    await waitFor(() => {
      const urls = patches(fn).map((p) => p.url)
      expect(urls).toContain('/api/teams/t1/squad/members/sm1')
      expect(urls).toContain('/api/teams/t1/squad/members/sm2')
    })
  })

  /**
   * 🔴 **내 카드도 남들과 같다**(사용자 요청, 2026-09-10). 전에는 「내 자리는
   * `card` 가 그린다」는 이유로 등재와 안 이어 놓아서, **옮길 수는 있는데
   * 안 남았다** — 새로 고치면 제자리로 돌아갔다.
   */
  describe('내 카드', () => {
    /**
     * 데모처럼 **내가 등재에 들어 있는** 스쿼드. 슬러그로 나를 가린다.
     *
     * 🔴 정정 (2026-09-16, 사용자 설계): 전에는 `grid_col`·`grid_row` 가
     * `null` 이어도 내 카드가 포메이션의 FW 칸에 서 있었다. 이제 **칸이
     * 저장돼 있어야** 선다 — 없으면 판에 안 서는 것이 새 규칙이라, 여기도
     * 내 칸(FW, 1열 0행)을 적어 둔다.
     */
    const withMe = {
      ...SQUAD,
      members: [meAt(1, 0), ...SQUAD.members],
    }

    it('옮기면 내 등재에 저장한다', async () => {
      const fn = server()
      render(<SquadPanel card={CARD} squad={withMe} myCardId={CARD.id} />)
      const mine = document.querySelector('[data-mine="true"]') as HTMLElement
      drag(mine, 0, 2)

      await waitFor(() =>
        expect(patches(fn)).toContainEqual({
          url: '/api/teams/t1/squad/members/sm-me',
          body: { position_code: 'DF', grid_col: 0, grid_row: 2 },
        }),
      )
    })

    it('서버가 준 칸과 포지션으로 열린다', () => {
      render(
        <SquadPanel
          card={CARD}
          squad={{
            ...withMe,
            members: [
              { ...withMe.members[0], position_code: 'GK', grid_col: 1, grid_row: 3 },
              ...SQUAD.members,
            ],
          }}
        />,
      )
      const mine = document.querySelector('[data-mine="true"]') as HTMLElement
      expect(mine.style.gridRow).toBe('4')
      expect(mine.querySelector('.ss-squad-pos')!.textContent).toBe('GK')
    })

    /* 🔴 **두 번 나오면 안 된다** — 등재와 이었다고 내 자리에 이름표까지
       그리면, 내 카드 대신 「홍길동」이라 적힌 빈 카드가 선다. */
    it('등재와 이어도 카드가 두 장이 되지 않는다', () => {
      render(<SquadPanel card={CARD} squad={withMe} />)
      expect(document.querySelectorAll('.ss-pcard')).toHaveLength(5)
      expect(document.querySelectorAll('[data-mine="true"]')).toHaveLength(1)
      expect(screen.queryByRole('button', { name: /홍길동 빼기/ })).toBeNull()
    })

    /* 내가 그 등재(`sm-me`)의 주인이 아니면 그 id 로는 아무것도 안 보낸다.

       🔴 **정정 (2026-09-17, 사용자 판단)**: 09-16 에는 「나」 표식을 눌러
       앉혔지만 이제 **저절로 앉는다**(팀장은 무조건 뛴다). 자동 착석이
       등재를 **만드는** `POST` 는 별개고, 여기서 보는 것은 **남의 등재
       id 로 PATCH 가 새어 나가지 않는지**다 — 이 판(`SQUAD`)에는 내 등재가
       없기 때문이다. */
    it('내가 등재에 없으면 아무것도 안 보낸다', async () => {
      const fn = server()
      render(<SquadPanel card={CARD} squad={SQUAD} myCardId={CARD.id} />)
      await waitFor(() =>
        expect(document.querySelector('[data-mine="true"]')).toBeInTheDocument(),
      )

      const mine = document.querySelector('[data-mine="true"]') as HTMLElement
      drag(mine, 0, 2)

      await waitFor(() => expect(document.querySelectorAll('.ss-squad-pos').length).toBeGreaterThan(0))
      expect(patches(fn).map((p) => p.url)).not.toContain('/api/teams/t1/squad/members/sm-me')
    })
  })

  /* 🔴 **등재가 아닌 자리는 보낼 것이 없다.** 지인 판에서 앉힌 사람은
     `player_card_id` 가 없어 등재가 안 됐고, 없는 등재에 PATCH 를 쏘면 404 다. */
  it('등재가 아닌 자리를 옮기면 아무것도 안 보낸다', async () => {
    const fn = server()
    render(<SquadPanel card={CARD} squad={null} />)
    const seat = document.querySelectorAll<HTMLElement>('.ss-squad-seat')[1]
    drag(seat, 0, 0)

    await waitFor(() => expect(document.querySelectorAll('.ss-squad-pos').length).toBeGreaterThan(0))
    expect(patches(fn)).toEqual([])
  })

  /* ⚠️ **주장이 아니면 403 이다**(계약 3-7절). 남는 것만 주장의 것이고,
     그 실패가 판을 멈추면 안 된다. */
  it('서버가 거절해도 판은 계속 돈다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        json: async () => ({ error: { code: 'FORBIDDEN', message: '주장만 바꿀 수 있습니다.' } }),
      }),
    )
    render(<SquadPanel card={CARD} squad={SQUAD} />)
    drag(seatOf('김철수'), 0, 0)

    await waitFor(() =>
      expect(
        screen
          .getByRole('button', { name: /김철수/ })
          .closest('.ss-squad-seat')!
          .querySelector('.ss-squad-pos')!.textContent,
      ).toBe('FW'),
    )
  })
})

describe('스쿼드 — 용병 찾기(추천 + 지인)', () => {
  /**
   * 🔴 **지인 목록은 이제 서버에서 온다**(2026-09-16, 계약 3-12절). 전에는
   * `SquadFriends.tsx` 안의 붙박이 배열이라 시험이 아무것도 안 세워도 됐다.
   *
   * 여기서 세우는 것은 **계약이 정한 응답 모양**이다 — 화면이 그 모양을
   * 그대로 읽는지가 이 시험들이 지키는 것이고, 모양이 바뀌면 여기가 먼저
   * 빨개져야 한다.
   */
  const CONTACTS = [
    {
      contact_id: 'ct1',
      user_id: 'u1',
      nickname: '홍길동',
      note: '같은 동네 · 수요일 저녁',
      accepted_at: '2026-09-15T10:00:00Z',
    },
    {
      contact_id: 'ct2',
      user_id: 'u2',
      nickname: '김철수',
      // 🔴 `note` 가 **없는 것이 정상**이다(내가 신청자가 아닐 때) — 그 갈래를
      //    실제로 밟는다.
      note: null,
      accepted_at: '2026-09-15T10:00:00Z',
    },
  ]

  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      const json = (body: unknown) =>
        Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))
      if (url.startsWith('/api/me/contacts/requests')) return json([])
      if (url.startsWith('/api/me/contacts')) return json({ items: CONTACTS })
      // 검색은 **지인이 아닌 사람**만 낸다 — 지인은 위 목록에 이미 있다.
      if (url.startsWith('/api/users/search')) return json([])
      return json(null)
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  /** 목록이 서버에서 오므로 **떠야 볼 수 있다** — 첫 줄이 올 때까지 기다린다. */
  async function openFriends() {
    const r = render(<SquadPanel card={CARD} scouting />)
    await screen.findByRole('button', { name: /홍길동/ })
    return r
  }

  it('켜면 판 옆에 검색창과 지인 목록이 나온다', async () => {
    await openFriends()
    expect(screen.getByRole('complementary', { name: '지인 찾기' })).toBeInTheDocument()
    expect(screen.getByLabelText('지인 닉네임')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /홍길동/ })).toBeInTheDocument()
  })

  // 🔴 단추 하나가 **둘을 같이** 연다(2026-09-08). 전에는 '용병 찾기'와
  //    '지인 찾기'가 알약 둘이었고 두 판이 한 자리를 다퉜다.
  it('추천 판과 지인 판이 같이 열린다', async () => {
    await openFriends()
    expect(screen.getByRole('complementary', { name: /추천 선수/ })).toBeInTheDocument()
    expect(screen.getByRole('complementary', { name: '지인 찾기' })).toBeInTheDocument()
  })

  // 판 위에서 위에서 아래로 읽히는 순서가 곧 "지금 가장 급한 자리"다.
  /* 🔴 정정 (2026-09-16, 사용자 설계): 전에는 FW 가 **늘 내 자리**라 건너뛰어
     빈 판의 첫 자리가 MF 였다. 이제 처음 판은 비어 있어서 FW 부터가 빈
     자리다 — 「위에서 아래로 첫 빈 자리」라는 규칙은 그대로고, 내 자리를
     건너뛰는 쪽은 바로 아래 시험이 따로 붙든다. */
  it('추천은 빈 자리 중 첫 번째(FW)의 것이다', async () => {
    await openFriends()
    expect(screen.getByRole('heading', { name: /AI 추천 FW/ })).toBeInTheDocument()
  })

  /* 🔴 **내가 선 자리는 빈 자리가 아니다** — 추천이 거기부터 열리면 이미 선
     나를 또 채우라는 말이 된다. 위 시험과 짝으로 읽는다: 내가 FW 에 서면
     첫 빈 자리는 그 다음 줄(MF)이다. */
  it('내가 선 자리는 건너뛴다 — 그 다음 빈 자리의 추천이 열린다', async () => {
    render(<SquadPanel card={CARD} squad={SQUAD_WITH_ME} myCardId={CARD.id} scouting />)
    expect(await screen.findByRole('heading', { name: /AI 추천 MF/ })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /AI 추천 FW/ })).toBeNull()
  })

  /**
   * 🔴 **빈 자리(+)로 열어도 같은 한 벌이다**(사용자 요청, 2026-09-16).
   * 전에는 알약으로 열 때만 지인 판이 따라 나오고, 빈 자리를 누르면 추천
   * 판만 섰다.
   *
   * `scouting` 은 부모(`HomeStage`)가 드는 값이라 여기서도 부모를 흉내내
   * 짝지어 준다 — 그러지 않으면 이 길이 실제로 어떻게 도는지를 안 재게 된다.
   */
  function Controlled() {
    const [scouting, setScouting] = useState(false)
    return (
      <SquadPanel
        card={CARD}
        scouting={scouting}
        onOpenScouting={() => setScouting(true)}
        onCloseScouting={() => setScouting(false)}
      />
    )
  }

  it('빈 자리를 눌러도 지인 판이 같이 열린다', async () => {
    const user = userEvent.setup()
    render(<Controlled />)
    await user.click(screen.getByRole('button', { name: 'GK 자리에 선수 넣기' }))
    expect(screen.getByRole('complementary', { name: '지인 찾기' })).toBeInTheDocument()
  })

  // 🔴 **누른 자리가 남아야 한다.** `scouting` 효과가 자리를 첫 빈 자리로
  // 정하므로, 누르기 쪽에서 자리를 먼저 넣지 않으면 GK 를 눌렀는데 MF 추천이
  // 뜬다 — 순서가 뒤집히면 이 시험이 잡는다.
  it('빈 자리로 열면 추천은 **누른 자리**의 것이다', async () => {
    const user = userEvent.setup()
    render(<Controlled />)
    await user.click(screen.getByRole('button', { name: 'GK 자리에 선수 넣기' }))
    expect(screen.getByRole('heading', { name: /AI 추천 GK/ })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /AI 추천 MF/ })).toBeNull()
  })

  it('닉네임을 치면 그 사람만 남는다', async () => {
    const user = userEvent.setup()
    await openFriends()
    await user.type(screen.getByLabelText('지인 닉네임'), '김철')
    expect(screen.getByRole('button', { name: /김철수/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /홍길동/ })).toBeNull()
  })

  /**
   * 🔴 **바로는 안 뜬다** — 서버 검색은 입력이 멎고 나서 나가므로, 그 사이에는
   * 「찾는 중…」이다. 없다는 말을 먼저 띄우면 아직 안 물어본 것을 없다고 하는
   * 셈이라, 이 시험도 결과가 올 때까지 기다린다.
   */
  it('찾는 사람이 없으면 그렇게 적는다', async () => {
    const user = userEvent.setup()
    await openFriends()
    await user.type(screen.getByLabelText('지인 닉네임'), '없는사람')
    expect(screen.getByText('찾는 중…')).toBeInTheDocument()
    expect(await screen.findByText('찾는 지인이 없습니다')).toBeInTheDocument()
  })

  // 🔴 자리는 **왼쪽 진짜 판**에서 고른다 — 작은 스쿼드 판을 여기 하나 더
  // 그리면 판이 둘이 되고, MF 가 둘이라 포지션 이름만으로는 못 고른다.
  /* 정정 (2026-09-16, 사용자 설계): 세는 수가 넷에서 **다섯**이 됐다 — 전에는
     FW 한 칸이 늘 내 자리라 빈 자리가 넷이었고, 이제 처음 판은 통째로
     비어 있다. 보는 것(빈 자리 **전부**가 「여기 넣기」로 바뀐다)은 그대로다. */
  it('지인을 고르면 빈 자리 버튼이 넣기 버튼으로 바뀐다', async () => {
    const user = userEvent.setup()
    await openFriends()
    expect(screen.getAllByRole('button', { name: /자리에 선수 넣기/ })).toHaveLength(5)

    await user.click(screen.getByRole('button', { name: /김철수/ }))
    expect(screen.getAllByRole('button', { name: /자리에 김철수 넣기/ })).toHaveLength(5)
    expect(screen.queryByRole('button', { name: /자리에 선수 넣기/ })).toBeNull()
  })

  it('빈 자리를 누르면 그 자리에 앉는다', async () => {
    const user = userEvent.setup()
    await openFriends()
    await user.click(screen.getByRole('button', { name: /김철수/ }))
    await user.click(screen.getByRole('button', { name: 'GK 자리에 김철수 넣기' }))

    expect(screen.getByRole('button', { name: '김철수 빼기' })).toBeInTheDocument()
    // 여러 명을 이어 넣는 게 보통이라 판은 열어 둔다.
    expect(screen.getByRole('complementary', { name: '지인 찾기' })).toBeInTheDocument()
  })

  // 정정 (2026-09-16, 사용자 설계): 위와 같은 이유로 빈 자리가 넷 → 다섯이다.
  it('고른 사람을 한 번 더 누르면 고르기가 풀린다', async () => {
    const user = userEvent.setup()
    await openFriends()
    const row = screen.getByRole('button', { name: /김철수/ })
    await user.click(row)
    await user.click(row)
    expect(screen.getAllByRole('button', { name: /자리에 선수 넣기/ })).toHaveLength(5)
  })

  /* 🔴 예전 규칙("지인이 열려 있으면 추천을 안 연다")을 **일부러 뒤집었다** —
     두 판이 같은 좌표에 서 있어서 둘 중 하나만 그릴 수밖에 없었던 것이고,
     이제는 칸이 갈렸다. 되돌리지 말 것. */
  it('열려 있는 동안 다른 빈 자리를 누르면 그 자리의 추천으로 바뀐다', async () => {
    const user = userEvent.setup()
    await openFriends()
    await user.click(screen.getByRole('button', { name: 'GK 자리에 선수 넣기' }))
    expect(screen.getByRole('heading', { name: /AI 추천 GK/ })).toBeInTheDocument()
    expect(screen.getByRole('complementary', { name: '지인 찾기' })).toBeInTheDocument()
  })

  // 🔴 표식이 없으면 방금 넣은 사람이 평범한 줄로 남아 또 고르게 된다.
  it('이미 넣은 사람은 목록에서 자리 이름과 함께 잠긴다', async () => {
    const user = userEvent.setup()
    await openFriends()
    await user.click(screen.getByRole('button', { name: /김철수/ }))
    await user.click(screen.getByRole('button', { name: 'GK 자리에 김철수 넣기' }))

    const row = screen.getByRole('button', { name: /김철수.*GK/ })
    expect(row).toBeDisabled()
    // 다른 사람은 그대로 고를 수 있다.
    expect(screen.getByRole('button', { name: /홍길동/ })).toBeEnabled()
  })

  it('빼면 목록에서 다시 고를 수 있다', async () => {
    const user = userEvent.setup()
    await openFriends()
    await user.click(screen.getByRole('button', { name: /김철수/ }))
    await user.click(screen.getByRole('button', { name: 'GK 자리에 김철수 넣기' }))
    await user.click(screen.getByRole('button', { name: '김철수 빼기' }))

    expect(screen.getByRole('button', { name: /김철수/ })).toBeEnabled()
  })

  /* 🔴 **정정 (2026-09-16, 사용자 지적: "그냥 카드 어디에 클릭해도 사라진다")**:
     전에는 카드 전체가 「빼기」 버튼이고 ⊗ 는 장식(`aria-hidden`)이었다. 이제
     **⊗ 가 진짜 버튼이고 카드는 눌러도 안 빠진다** — 옮기려고 짚기만 해도
     사람이 빠지는 것이 문제였다. 되돌릴 수 없는 일에는 넓은 과녁을 주지 않는다.
     (여는 일은 여전히 카드 전체가 과녁이다 — 되돌릴 수 있어서다.) */
  it('넣은 자리는 ⊗ 로만 빠지고, 카드를 눌러서는 안 빠진다', async () => {
    const user = userEvent.setup()
    const { container } = await openFriends()
    expect(container.querySelector('.ss-squad-remove')).toBeNull()

    await user.click(screen.getByRole('button', { name: /김철수/ }))
    await user.click(screen.getByRole('button', { name: 'GK 자리에 김철수 넣기' }))

    // ⊗ 가 곧 빼기 버튼이다 — 장식이 아니다.
    const badge = container.querySelector('.ss-squad-remove')
    expect(badge).not.toBeNull()
    expect(badge).toBe(screen.getByRole('button', { name: '김철수 빼기' }))

    /* 카드를 눌러도 그대로 앉아 있다. ⚠️ 지인 판에도 같은 이름이 있으므로
       **판 위의 이름표**(`.ss-squad-name`)로 집는다. */
    const seated = container.querySelector('.ss-squad-name') as HTMLElement
    expect(seated).toHaveTextContent('김철수')
    await user.click(seated)
    expect(container.querySelector('.ss-squad-name')).toHaveTextContent('김철수')

    // ⊗ 를 눌러야 빠진다.
    await user.click(screen.getByRole('button', { name: '김철수 빼기' }))
    expect(container.querySelector('.ss-squad-name')).toBeNull()
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

/**
 * 🔴 **지인은 상호 관계다**(계약 3-12절, 2026-09-16). 검색으로 나온 사람은
 * 아직 남이라 **판에 앉힐 수 없고 신청만** 보낸다. 상대가 수락해야 지인
 * 목록에 들어오고, 그때부터 자리에 앉는다.
 *
 * 이 구분이 무너지면 "검색되는 아무나 우리 팀에 세울 수 있는" 화면이 된다 —
 * 위 describe 의 「내 지인」 시험들과 **짝으로** 읽어야 하는 이유다.
 */
describe('스쿼드 — 지인 찾기는 서버를 부른다', () => {
  const FOUND = [{ id: 'u9', nickname: '정하늘' }]

  /** 이 시험에서 실제로 나간 요청들 — 몇 번째가 무엇인지까지 본다. */
  let calls: { url: string; method: string; body: string | null }[]

  beforeEach(() => {
    calls = []
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        calls.push({
          url,
          method: init?.method ?? 'GET',
          body: typeof init?.body === 'string' ? init.body : null,
        })
        const json = (body: unknown, status = 200) =>
          Promise.resolve(new Response(JSON.stringify(body), { status }))
        if (url.startsWith('/api/me/contacts/requests')) {
          return json([
            {
              id: 'ct7',
              requester_user_id: 'u5',
              target_user_id: 'me',
              note: null,
              created_at: '2026-09-16T01:00:00Z',
            },
          ])
        }
        if (url.includes('/accept')) return json({ id: 'ct7', accepted_at: 'now' })
        if (url.startsWith('/api/me/contacts')) return json({ items: [] })
        if (url.startsWith('/api/users/search')) return json(FOUND)
        return json(null)
      },
    )
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('닉네임을 치면 서버에 묻는다 — 붙박이 명단이 아니다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel card={CARD} scouting />)
    await user.type(screen.getByLabelText('지인 닉네임'), '정하늘')
    expect(await screen.findByText('정하늘')).toBeInTheDocument()
    await waitFor(() =>
      expect(calls.some((c) => c.url.startsWith('/api/users/search?q='))).toBe(true),
    )
  })

  // 🔴 검색 결과는 **앉히는 줄이 아니다.** 누르면 신청이 나간다.
  it('검색으로 나온 사람은 앉히지 않고 신청만 보낸다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel card={CARD} scouting />)
    await user.type(screen.getByLabelText('지인 닉네임'), '정하늘')
    await screen.findByText('정하늘')

    await user.click(screen.getByRole('button', { name: '지인 신청' }))

    const sent = calls.find((c) => c.method === 'POST' && c.url === '/api/me/contacts')
    expect(sent).toBeDefined()
    expect(JSON.parse(sent!.body!)).toEqual({ target_user_id: 'u9' })
    // 누른 뒤에는 다시 못 누른다 — 두 번 보내면 409 다.
    expect(await screen.findByRole('button', { name: '신청함' })).toBeDisabled()
    // 🔴 판에 앉는 길은 안 열렸다 — 빈 자리는 여전히 「선수 넣기」다.
    expect(screen.getAllByRole('button', { name: /자리에 선수 넣기/ }).length).toBeGreaterThan(0)
  })

  it('받은 신청을 수락하면 그 경로를 부른다', async () => {
    const user = userEvent.setup()
    render(<SquadPanel card={CARD} scouting />)
    await user.click(await screen.findByRole('button', { name: '수락' }))
    await waitFor(() =>
      expect(calls.some((c) => c.url === '/api/me/contacts/ct7/accept' && c.method === 'POST')).toBe(
        true,
      ),
    )
  })
})

/**
 * 🔴 **표시 등급은 서버가 낸다**(2026-09-16, 계약 3-6·3-16절 · 미결 paik 25·26번).
 *
 * 전에는 `SquadSuggest.tsx` 의 `SUGGESTIONS[].grade` 가 지어낸 값이었다. 이제
 * 서버가 분석 등급(A~D) 위에 재매칭 의사의 Wilson 신뢰구간을 얹어 S~F 를
 * 계산해서 준다 — **화면은 받아서 그리기만 한다.**
 */
describe('스쿼드 — 추천 판의 등급은 서버 값이다', () => {
  let calls: string[]

  beforeEach(() => {
    calls = []
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      calls.push(url)
      const json = (b: unknown) =>
        Promise.resolve(new Response(JSON.stringify(b), { status: 200 }))
      if (url.includes('/squad/candidates')) {
        const grade = new URL(url, 'http://t').searchParams.get('grade')
        const rows = [
          { user_id: 'u1', nickname: '최유진', card_public_slug: 'c', grade: 'A', provisional: true },
          { user_id: 'u2', nickname: '강태원', card_public_slug: 'd', grade: 'B', provisional: false },
          // 🔴 등급을 모르는 사람 — 대표 영상이 없거나 아직 분석 전이다.
          { user_id: 'u3', nickname: '이름없음', card_public_slug: null, grade: null, provisional: null },
        ]
        return json(grade ? rows.filter((r) => r.grade === grade) : rows)
      }
      return json([])
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  const openSuggest = async (user: ReturnType<typeof userEvent.setup>) => {
    render(<SquadPanel card={CARD} myTeamId="team-mine" />)
    await user.click(screen.getAllByRole('button', { name: 'MF 자리에 선수 넣기' })[0])
  }

  it('후보를 계약 경로로 받아 온다 — 붙박이가 아니다', async () => {
    const user = userEvent.setup()
    await openSuggest(user)
    expect(await screen.findByText('최유진')).toBeInTheDocument()
    expect(
      calls.some((u) => u.includes('/api/teams/team-mine/squad/candidates?position_code=MF')),
    ).toBe(true)
  })

  /**
   * 🔴 **정상호가 조건으로 단 표시다**(2026-09-14). 지금 루브릭은
   * `review_required: true` 라 남에게 보이는 등급이 잠정인데, 등급 문자만
   * 보이면 받는 쪽은 확정으로 읽는다 — 남의 화면에 박힌 등급은 회수가 안 된다.
   */
  it('provisional 이면 등급 옆에 「검수 전」을 단다', async () => {
    const user = userEvent.setup()
    await openSuggest(user)
    const row = (await screen.findByText('최유진')).closest('.ss-suggest-nameline')
    expect(row).toHaveTextContent('A')
    expect(row).toHaveTextContent('검수 전')

    // 검수가 끝난 값에는 안 붙는다 — 늘 붙으면 표시가 뜻을 잃는다.
    const done = screen.getByText('강태원').closest('.ss-suggest-nameline')
    expect(done).toHaveTextContent('B')
    expect(done).not.toHaveTextContent('검수 전')
  })

  /* 🔴 **모르는 등급을 `F` 로 치지 않는다**(26번의 「하지 말 것」) — 「없다」와
     「낮다」는 다르다. 칸 자체를 안 그린다. */
  it('등급을 모르는 후보는 등급 칸이 아예 없다', async () => {
    const user = userEvent.setup()
    await openSuggest(user)
    const row = (await screen.findByText('이름없음')).closest('.ss-suggest-nameline')
    expect(row?.querySelector('.ss-suggest-grade')).toBeNull()
    expect(row).not.toHaveTextContent('F')
  })

  /* 🔴 **거르개는 서버로 간다.** 화면에서 거르면 「이 등급에 몇 명인가」가
     받아 온 페이지 안에서만 맞는 값이 된다 — 계약이 하드 필터를 서버에 뒀다. */
  it('등급을 고르면 그 값을 서버에 실어 보낸다', async () => {
    const user = userEvent.setup()
    await openSuggest(user)
    await screen.findByText('최유진')
    await user.click(screen.getByRole('button', { name: 'B' }))
    await waitFor(() => expect(calls.some((u) => u.includes('grade=B'))).toBe(true))
  })

  /* 「상관없음」은 빈 값으로 나가면 안 된다 — `grade=` 는 없는 등급이라 422 다. */
  it('「등급 상관없음」이면 grade 를 아예 안 싣는다', async () => {
    const user = userEvent.setup()
    await openSuggest(user)
    await screen.findByText('최유진')
    expect(calls.some((u) => u.includes('/squad/candidates') && u.includes('grade='))).toBe(false)
  })
})
