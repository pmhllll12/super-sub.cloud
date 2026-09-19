import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SiteHeader from './SiteHeader'
import type { Destination } from './HomeNav'
import { NOTIFY } from '@/lib/destinations'

const pathname = vi.fn(() => '/')
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => pathname(),
}))

const DESTINATIONS: Destination[] = [
  { title: '영상 분석', icon: 'camera_video', summary: '경기 영상을 올리면', href: '/analysis' },
  { title: '레슨 · 상점', icon: 'add_business', summary: '제휴 코치와 장비를' },
]

describe('화면 맨 위 줄', () => {
  it('모든 목적지를 적는다', () => {
    pathname.mockReturnValue('/')
    render(<SiteHeader user={{ nickname: '홍길동' }} destinations={DESTINATIONS} />)
    // 글자 줄 항목은 2026-09-08 부터 **링크**다 — 아이콘이 글자 위로 올라가고
    // 그 둘을 링크가 감싸면서 이동을 맡았다(HomeNav 주석).
    expect(screen.getByRole('link', { name: '영상 분석' })).toBeInTheDocument()
    // 이 고정값의 '레슨 · 상점' 은 href 가 없다 — 갈 곳이 없으면 버튼이다.
    expect(screen.getByRole('button', { name: '레슨 · 상점' })).toBeInTheDocument()
  })

  // 🔴 눌러도 제자리인 글자를 남겨 두면 "안 눌린다"로 읽힌다.
  it('지금 보고 있는 화면은 목적지에서 뺀다', () => {
    pathname.mockReturnValue('/analysis')
    render(<SiteHeader user={{ nickname: '홍길동' }} destinations={DESTINATIONS} />)
    expect(screen.queryByRole('button', { name: '영상 분석' })).toBeNull()
    expect(screen.getByRole('button', { name: '레슨 · 상점' })).toBeInTheDocument()
  })
})

/**
 * **받은 초대가 머리줄 알림까지 이어져 있는가** (미결 `paik` 37번).
 *
 * 훅과 판을 따로 시험해도 **둘을 안 이어 두면** 화면에서는 아무 일도 안
 * 일어난다 — 그 배선을 여기서 잡는다.
 */
const INVITE_ROW = {
  id: 'inv1',
  team_id: 'team-bolt',
  invited_user_id: 'u-me',
  status: 'pending',
  created_at: '2026-09-17T10:00:00+09:00',
  responded_at: null,
  position_code: 'GK',
  position_label: '골키퍼',
  team_name: '번개FC',
  team_region: '서울 강남',
  team_sport_code: 'football',
  squad_public_slug: 'sq-abc123',
}

describe('머리줄 알림 — 받은 팀 초대', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('초대를 그리고, 수락하면 그 경로를 부른다', async () => {
    pathname.mockReturnValue('/')
    const sent: { url: string; method: string }[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((url: string, init?: RequestInit) => {
        const u = String(url)
        sent.push({ url: u, method: init?.method ?? 'GET' })
        const body = u.endsWith('/api/me')
          ? { teams: [] }
          : u.includes('/me/invitations')
            ? [INVITE_ROW]
            : []
        return Promise.resolve({ ok: true, status: 200, json: async () => body })
      }),
    )

    /* 🔴 「알림」은 `SiteHeader` 가 만들지 않고 **목적지 목록으로 들어온다**
       (`lib/destinations.ts`) — 실제 앱과 같은 자리를 주어야 판이 열린다. */
    render(
      <SiteHeader
        user={{ nickname: '홍길동' }}
        destinations={[...DESTINATIONS, { title: NOTIFY, icon: 'circle_notifications', summary: '받은 신청' }]}
      />,
    )

    // 알림 판을 연다 — 🔴 **눌러서 연다**(가리키기로 열면 판 안의 단추까지
    // 마우스가 못 간다, 2026-09-16).
    await userEvent.click(await screen.findByRole('button', { name: '알림' }))
    expect(await screen.findByText('번개FC')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: '수락하기' }))

    await waitFor(() =>
      expect(
        sent.some((c) => c.method === 'POST' && c.url.endsWith('/api/me/invitations/inv1/accept')),
      ).toBe(true),
    )
  })
})

/**
 * 🔴 **판을 열 때 알림 줄이 둘로 보인다**(사용자 지적, 2026-09-17).
 *
 * DOM 에 정말 둘인지, 아니면 연출이 겹쳐 그렇게 보이는지부터 가른다 —
 * 원인을 모르고 고치면 엉뚱한 데를 만진다.
 */
describe('머리줄 알림 — 판을 열어도 줄은 하나다', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('「스쿼드」를 눌러도 알림 줄이 하나뿐이다', async () => {
    pathname.mockReturnValue('/')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((url: string) => {
        const u = String(url)
        const body = u.endsWith('/api/me')
          ? { teams: [] }
          : u.includes('/me/invitations')
            ? [INVITE_ROW]
            : u.includes('/api/squads/')
              ? { public_slug: 'sq-abc123', formation: '5:5', members: [] }
              : []
        return Promise.resolve({ ok: true, status: 200, json: async () => body })
      }),
    )

    const { container } = render(
      <SiteHeader
        user={{ nickname: '홍길동' }}
        destinations={[
          ...DESTINATIONS,
          { title: NOTIFY, icon: 'circle_notifications', summary: '받은 신청' },
        ]}
      />,
    )

    await userEvent.click(await screen.findByRole('button', { name: '알림' }))
    expect(await screen.findByText('번개FC')).toBeInTheDocument()
    expect(container.querySelectorAll('.ss-notify-row')).toHaveLength(1)

    await userEvent.click(screen.getByRole('button', { name: '스쿼드' }))

    // 판이 열려도 줄은 하나여야 한다.
    expect(container.querySelectorAll('.ss-notify-row')).toHaveLength(1)
    expect(container.querySelectorAll('.ss-home-nav-card')).toHaveLength(1)
  })
})

/**
 * 🔴 **알림함이 두 벌이면 수락이 화면에 안 닿는다** (2026-09-17, 사용자가
 * 로컬에서 잡았다 — 「수락하기 눌렀는데 왜 대기화면 안 뜸?」).
 *
 * `SiteHeader` 와 `HomeStage` 가 각각 `useNotifyInbox()` 를 불러서, 헤더에서
 * 수락한 결과(`acceptedTeam`)가 대기 화면을 그리는 `SquadPanel` 쪽 통에는
 * **영영 안 들어갔다.** 헤더가 **받은 통을 쓰게** 해서 하나로 합친다.
 */
describe('머리줄 — 알림함을 밖에서 받을 수 있다', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('받은 통의 수락 함수를 부른다 — 제 통을 따로 만들지 않는다', async () => {
    pathname.mockReturnValue('/')
    const acceptMatch = vi.fn().mockResolvedValue(undefined)
    const inbox = {
      teamId: 'team-mine',
      items: [
        {
          kind: 'team-match' as const,
          id: 'tmr1',
          teamId: 'team-mine',
          opponentTeamId: 'mt-2',
          name: '망원 유나이티드',
          region: '서울 마포구',
          playedAt: '2026-09-19T09:00:00+09:00',
          place: '망원 실내구장 A',
          opponentSquadSlug: null,
          ourName: '우리 팀',
          ourSquadSlug: null,
        },
      ],
      count: 1,
      acceptedTeamId: null,
      acceptedTeam: null,
      acceptedUs: null,
      acceptedMatchId: null,
      confirmed: null,
      reopenConfirmed: vi.fn(),
      clearAccepted: vi.fn(),
      acceptMatch,
      rejectMatch: vi.fn(),
      acceptContact: vi.fn(),
      acceptInvitation: vi.fn(),
      rejectInvitation: vi.fn(),
      noteSent: vi.fn(),
      reload: vi.fn(),
    }

    /* 헤더가 제 통을 안 만들어도 `/api/me` 는 부르므로 대역을 세운다. */
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ teams: [] }) }),
    )

    render(
      <SiteHeader
        user={{ nickname: '홍길동' }}
        destinations={[
          ...DESTINATIONS,
          { title: NOTIFY, icon: 'circle_notifications', summary: '받은 신청' },
        ]}
        inbox={inbox}
      />,
    )

    /* 🔴 빨간 점이 켜지면 낭독용 「새 알림 있음」이 이름에 붙는다 — 정확히
       `'알림'` 으로는 안 잡힌다. */
    await userEvent.click(await screen.findByRole('button', { name: /알림/ }))
    await userEvent.click(await screen.findByRole('button', { name: '수락하기' }))

    expect(acceptMatch).toHaveBeenCalled()
  })
})
