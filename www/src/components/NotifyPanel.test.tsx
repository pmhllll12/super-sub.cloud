import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import NotifyPanel from './NotifyPanel'
import type { InboxItem } from '@/lib/useNotifyInbox'

/**
 * 「알림」 글자 아래로 떠오르는 판 (사용자 요청, 2026-09-16).
 *
 * 🔴 요청의 핵심은 **별도 화면을 만들지 않는 것**이다 — 상대 팀 정보와 수락
 * 단추가 같은 줄에 있어야 하고, 가리키기만 하면 나와야 한다. 그래서 이 시험은
 * "줄 안에 둘이 같이 있는가"를 붙든다.
 */
const MATCH: InboxItem = {
  kind: 'team-match',
  id: 'tmr1',
  teamId: 'team-mine',
  opponentTeamId: 'mt-2',
  name: '망원 유나이티드',
  region: '서울 마포구',
  playedAt: '2026-09-19T09:00:00+09:00',
  place: '망원 실내구장 A',
  opponentSquadSlug: null,
}

describe('알림 판', () => {
  it('받은 경기 신청에 상대 팀 정보와 수락 단추가 같이 있다', () => {
    render(
      <NotifyPanel
        items={[MATCH]}
        onAcceptMatch={vi.fn()}
        onRejectMatch={vi.fn()}
        onAcceptContact={vi.fn()}
      />,
    )
    const row = screen.getByText('망원 유나이티드').closest('.ss-notify-row')
    expect(row).not.toBeNull()
    expect(row).toHaveTextContent('서울 마포구')
    expect(row).toHaveTextContent('망원 실내구장 A')
    // 🔴 **같은 줄 안에** 있어야 한다 — 눌러 들어가는 화면을 만들지 않는 것이
    //    요청이라, 단추가 다른 곳에 있으면 그 요청을 안 지킨 것이다.
    expect(row?.querySelector('button')).toHaveTextContent('수락하기')
  })

  it('수락하면 그 줄을 넘겨 부른다', async () => {
    const user = userEvent.setup()
    const onAcceptMatch = vi.fn().mockResolvedValue(undefined)
    render(
      <NotifyPanel
        items={[MATCH]}
        onAcceptMatch={onAcceptMatch}
        onRejectMatch={vi.fn()}
        onAcceptContact={vi.fn()}
      />,
    )
    await user.click(screen.getByRole('button', { name: '수락하기' }))
    expect(onAcceptMatch).toHaveBeenCalledWith(MATCH)
  })

  /* 🔴 **이름을 지어내지 않는다.** 계약이 팀 이름을 안 줘서(3-15절은 id 만
     준다) 진짜 백엔드에서는 자주 `null` 이다 — 그때 빈 줄이 되면 안 된다. */
  it('상대 팀 이름을 모르면 「상대 팀」으로 적는다', () => {
    render(
      <NotifyPanel
        items={[{ ...MATCH, name: null, region: null } as InboxItem]}
        onAcceptMatch={vi.fn()}
        onRejectMatch={vi.fn()}
        onAcceptContact={vi.fn()}
      />,
    )
    expect(screen.getByText('상대 팀')).toBeInTheDocument()
  })

  it('받은 것이 없으면 그렇게 적는다', () => {
    render(
      <NotifyPanel
        items={[]}
        onAcceptMatch={vi.fn()}
        onRejectMatch={vi.fn()}
        onAcceptContact={vi.fn()}
      />,
    )
    expect(screen.getByText('새 알림이 없습니다')).toBeInTheDocument()
  })
})

/**
 * **받은 팀 초대 줄** (CCC 53번, 미결 `paik` 37번).
 *
 * 계약이 「하지 말 것」으로 못 박은 셋을 여기서 잠근다 — `position_*` 가
 * `null` 인 것을 실패로 보지 않기 · `squad_public_slug` 가 `null` 인 것도
 * 정상 · **약칭만 보고 자리 이름을 지어내지 않기**.
 */
const INVITE: InboxItem = {
  kind: 'invitation',
  id: 'inv1',
  teamName: '번개FC',
  teamRegion: '서울 강남',
  posLabel: '골키퍼',
  posCode: 'GK',
  squadSlug: 'sq-abc123',
}

function renderInvite(item: InboxItem = INVITE, extra: Record<string, unknown> = {}) {
  return render(
    <NotifyPanel
      items={[item]}
      onAcceptMatch={vi.fn()}
      onRejectMatch={vi.fn()}
      onAcceptContact={vi.fn()}
      onAcceptInvitation={vi.fn()}
      onRejectInvitation={vi.fn()}
      {...extra}
    />,
  )
}

describe('알림 판 — 받은 팀 초대', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('팀 이름·지역과 부르는 자리가 수락 단추와 같은 줄에 있다', () => {
    renderInvite()
    const row = screen.getByText('번개FC').closest('.ss-notify-row')
    expect(row).not.toBeNull()
    expect(row).toHaveTextContent('서울 강남')
    // 🔴 **서버가 준 이름**을 쓴다 — 약칭으로 지어내지 않는다.
    expect(row).toHaveTextContent('골키퍼')
    expect(row).toHaveTextContent('수락하기')
    expect(row).toHaveTextContent('거절')
  })

  /**
   * 🔴 **약칭으로 이름을 지어내지 않는다.** 종목마다 같은 약칭이 다른 뜻이라
   * (축구 `FW` ≠ 농구 `FW`) 화면이 표를 들면 갈린다. 서버가 준 `position_label`
   * 이 아닌 다른 이름이 나오면 폴백 표가 살아난 것이므로 여기서 빨개진다.
   */
  it('자리 이름은 서버 값을 쓴다 — 약칭으로 지어내지 않는다', () => {
    renderInvite({ ...INVITE, posLabel: '서버가 준 자리', posCode: 'GK' })
    expect(screen.getByText(/서버가 준 자리/)).toBeInTheDocument()
    expect(screen.queryByText(/골키퍼/)).toBeNull()
  })

  it('자리를 안 정한 초대면 자리 줄을 안 그린다 — null 은 실패가 아니다', () => {
    renderInvite({ ...INVITE, posLabel: null, posCode: null })
    const row = screen.getByText('번개FC').closest('.ss-notify-row')
    expect(row).not.toHaveTextContent('로 부릅니다')
    // 그래도 수락은 할 수 있어야 한다.
    expect(row).toHaveTextContent('수락하기')
  })

  it('판이 아직 없는 팀이면 그렇게 적고 「스쿼드」를 안 준다', () => {
    renderInvite({ ...INVITE, squadSlug: null })
    expect(screen.getByText('아직 판이 없습니다')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '스쿼드' })).toBeNull()
  })

  /**
   * 🔴 **목록을 그릴 때 줄마다 부르지 않는다.** 초대가 여럿이면 열지도 않은
   * 판을 그 수만큼 읽게 된다 — 누른 그 줄만, 그때 읽는다.
   */
  it('「스쿼드」를 누를 때까지 판을 안 읽는다', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ public_slug: 'sq-abc123', formation: null, members: [] }),
    })
    vi.stubGlobal('fetch', fetchMock)

    renderInvite()
    expect(fetchMock).not.toHaveBeenCalled()

    await userEvent.click(screen.getByRole('button', { name: '스쿼드' }))
    expect(fetchMock).toHaveBeenCalledWith('/api/squads/sq-abc123')
  })

  it('「스쿼드」를 누르면 그 팀 판이 줄 아래에 펼쳐진다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          public_slug: 'sq-abc123',
          formation: '5:5',
          members: [
            {
              id: 'sm1',
              nickname: '홍길동',
              position_code: 'FW',
              position_label: '공격수',
              grid_col: 1,
              grid_row: 0,
            },
          ],
        }),
      }),
    )

    renderInvite()
    await userEvent.click(screen.getByRole('button', { name: '스쿼드' }))

    expect(await screen.findByText('홍길동')).toBeInTheDocument()
  })

  it('수락하면 그 초대를 넘긴다', async () => {
    const onAcceptInvitation = vi.fn().mockResolvedValue(undefined)
    renderInvite(INVITE, { onAcceptInvitation })

    await userEvent.click(screen.getByRole('button', { name: '수락하기' }))
    expect(onAcceptInvitation).toHaveBeenCalledWith(INVITE)
  })

  it('거절하면 그 초대를 넘긴다', async () => {
    const onRejectInvitation = vi.fn().mockResolvedValue(undefined)
    renderInvite(INVITE, { onRejectInvitation })

    await userEvent.click(screen.getByRole('button', { name: '거절' }))
    expect(onRejectInvitation).toHaveBeenCalledWith(INVITE)
  })
})

/**
 * **판에 내가 설 자리를 보여 준다** (사용자 요청, 2026-09-17).
 *
 * 🔴 판만 그리면 「저 팀이 이렇게 짜여 있구나」까지다 — 정작 **내가 어디로
 * 불렸는지**가 안 보인다. 팀장이 정해 둔 자리(`position_code`)에 내 카드를
 * 세우고 **깜빡이게** 해야 「저기로 부르는구나」가 한눈에 읽힌다.
 */
function stubSquad(members: unknown[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ public_slug: 'sq-abc123', formation: '5:5', members }),
    }),
  )
}

const OTHERS = [
  {
    id: 'sm1',
    nickname: '박지성',
    position_code: 'FW',
    position_label: '공격수',
    grid_col: 1,
    grid_row: 0,
  },
]

describe('초대 판 — 내가 설 자리', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('팀장이 정한 자리에 내 카드가 선다', async () => {
    stubSquad(OTHERS)
    renderInvite()
    await userEvent.click(screen.getByRole('button', { name: '스쿼드' }))

    const mine = await screen.findByText('나')
    const seat = mine.closest('.ss-squad-seat')
    expect(seat).not.toBeNull()
    // 🔴 **GK 줄이다** — 행이 포지션을 정한다(0 FW · 1 MF · 2 DF · 3 GK).
    expect(seat).toHaveStyle({ gridRow: '4' })
    // 깜빡이는 것은 CSS 가 맡고, 표식은 이 속성이다.
    expect(seat).toHaveAttribute('data-mine', 'true')
  })

  /**
   * 🔴 **이미 선 사람을 밀어내지 않는다.** 그리고 **GK 줄은 칸이 하나뿐**이다
   * (`pitchGrid.ts` — 골키퍼 줄 양옆은 아예 없는 칸이다). 그 한 칸이 차 있으면
   * 세울 데가 없으므로 **안 세운다** — 남의 카드를 덮으면 판이 거짓이 된다.
   */
  it('GK 줄이 이미 찼으면 남의 카드를 덮지 않는다', async () => {
    stubSquad([
      ...OTHERS,
      {
        id: 'sm2',
        nickname: '이운재',
        position_code: 'GK',
        position_label: '골키퍼',
        grid_col: 1,
        grid_row: 3,
      },
    ])
    renderInvite()
    await userEvent.click(screen.getByRole('button', { name: '스쿼드' }))

    expect(await screen.findByText('이운재')).toBeInTheDocument()
    expect(screen.queryByText('나')).toBeNull()
  })

  /**
   * 🔴 **포메이션에 있는 칸에만 선다** (사용자 지적, 2026-09-17 — 「위치가
   * 몇 개로 정해져 있는데」). 판은 아무 칸이나 쓰는 것이 아니라 크기마다
   * 자리가 정해져 있다 — 5:5 는 **1-2-1** 이라 MF 는 **왼쪽(0)·오른쪽(2)
   * 둘뿐**이고 가운데(1)는 MF 자리가 아니다.
   */
  it('5:5 에서 MF 로 부르면 빈 MF 칸(왼쪽·오른쪽)에 선다 — 가운데가 아니다', async () => {
    stubSquad([
      {
        id: 'sm2',
        nickname: '기성용',
        position_code: 'MF',
        position_label: '미드필더',
        grid_col: 0,
        grid_row: 1,
      },
    ])
    renderInvite({ ...INVITE, posCode: 'MF', posLabel: '미드필더' })
    await userEvent.click(screen.getByRole('button', { name: '스쿼드' }))

    const seat = (await screen.findByText('나')).closest('.ss-squad-seat')
    expect(seat).toHaveStyle({ gridRow: '2' })
    // 왼쪽(1번째 칸)은 기성용이 섰으니 남은 MF 자리는 **오른쪽(3번째 칸)**이다.
    expect(seat).toHaveStyle({ gridColumn: '3' })
  })

  /* 5:5 의 MF 두 칸이 다 차면 설 자리가 없다 — 가운데에 억지로 세우지 않는다. */
  it('MF 두 칸이 다 차면 가운데에 억지로 세우지 않는다', async () => {
    stubSquad([
      { id: 'a', nickname: '기성용', position_code: 'MF', position_label: '미드필더', grid_col: 0, grid_row: 1 },
      { id: 'b', nickname: '구자철', position_code: 'MF', position_label: '미드필더', grid_col: 2, grid_row: 1 },
    ])
    renderInvite({ ...INVITE, posCode: 'MF', posLabel: '미드필더' })
    await userEvent.click(screen.getByRole('button', { name: '스쿼드' }))

    expect(await screen.findByText('기성용')).toBeInTheDocument()
    expect(screen.queryByText('나')).toBeNull()
  })

  /* 자리를 안 정한 초대면 세울 자리가 없다 — 지어내지 않는다(계약). */
  it('자리를 안 정한 초대면 내 카드를 안 세운다', async () => {
    stubSquad(OTHERS)
    renderInvite({ ...INVITE, posLabel: null, posCode: null })
    await userEvent.click(screen.getByRole('button', { name: '스쿼드' }))

    expect(await screen.findByText('박지성')).toBeInTheDocument()
    expect(screen.queryByText('나')).toBeNull()
  })
})

/**
 * 🔴 **불러오는 동안에도 줄이 흔들리면 안 된다** (사용자 지적, 2026-09-17 —
 * 「하나 더 복사되어서 떨어지는게 보여」).
 *
 * 판은 흐름에서 빠져 줄 왼쪽에 서는데, **불러오는 중·실패 상태만** 그
 * 상자 밖으로 나가 있었다. 그것만 흐름 안에 남아 단추 옆에 끼어 **두 번째
 * 막대처럼 보였다가**, 판이 도착하면 사라졌다 — 그게 「복사되어 떨어지는」
 * 것의 정체다. DOM 에 줄이 둘인 적은 없었다(`SiteHeader.test.tsx` 가 확인).
 */
describe('초대 판 — 불러오는 동안', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('불러오는 중 표시도 판과 같은 상자 안에 있다 — 줄에 끼어들지 않는다', async () => {
    // 영영 안 끝나는 약속 — 불러오는 중 상태에 머문다.
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise(() => {})))
    renderInvite()
    await userEvent.click(screen.getByRole('button', { name: '스쿼드' }))

    const loading = await screen.findByText('판을 불러오는 중…')
    expect(loading.closest('.ss-notify-squad')).not.toBeNull()
  })

  it('실패 표시도 같은 상자 안에 있다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 404 }))
    renderInvite()
    await userEvent.click(screen.getByRole('button', { name: '스쿼드' }))

    const failed = await screen.findByText('판을 불러오지 못했습니다')
    expect(failed.closest('.ss-notify-squad')).not.toBeNull()
  })
})

/**
 * **판을 열면 뒤의 두 판이 흐려진다** (사용자 요청, 2026-09-17).
 *
 * 초대 판은 알림에서 왼쪽으로 나오는데, 그 자리에 「AI 추천」·「지인 찾기」
 * 판이 **겹쳐 있을 때가 있다**. 둘은 헤더가 아니라 페이지 쪽 조각이라 직접
 * 넘길 수가 없어서, **문서 뿌리에 표식 하나**를 걸고 CSS 가 그것을 읽는다.
 *
 * 🔴 **닫으면 반드시 걷는다** — 안 걷으면 화면이 흐린 채로 남는다.
 */
describe('초대 판 — 뒤 판 흐리기', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    delete document.documentElement.dataset.ssPeek
    delete document.documentElement.dataset.ssNotify
  })

  /* 🔴 **범위가 둘이다**(사용자 요청) — 알림 판만 열렸을 때는 그 아래 깔린
     「지인 찾기」만, 초대 판까지 열면 둘 다. 표식을 나눠 CSS 가 가른다. */
  it('알림 판이 열려 있는 동안에는 알림 표식만 선다', () => {
    renderInvite()
    expect(document.documentElement.dataset.ssNotify).toBe('true')
    expect(document.documentElement.dataset.ssPeek).toBeUndefined()
  })

  it('판을 열면 표식이 서고, 닫으면 걷힌다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise(() => {})))
    renderInvite()
    expect(document.documentElement.dataset.ssPeek).toBeUndefined()

    await userEvent.click(screen.getByRole('button', { name: '스쿼드' }))
    expect(document.documentElement.dataset.ssPeek).toBe('true')

    await userEvent.click(screen.getByRole('button', { name: '스쿼드 닫기' }))
    expect(document.documentElement.dataset.ssPeek).toBeUndefined()
  })

  /* 🔴 알림 판이 통째로 닫히면 이 조각이 사라진다 — 그때도 걷어야 한다. */
  it('알림 판이 사라져도 표식을 걷는다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise(() => {})))
    const { unmount } = renderInvite()
    await userEvent.click(screen.getByRole('button', { name: '스쿼드' }))
    expect(document.documentElement.dataset.ssPeek).toBe('true')

    unmount()
    expect(document.documentElement.dataset.ssPeek).toBeUndefined()
  })
})
