import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { __resetRefDataCache } from '@/lib/refData'
import type { Venue } from '@/lib/venues'
import VenueBoard from './VenueBoard'

/**
 * 경기장 예약 판 — 레슨 · 상점과 같은 두 색으로 짠 목록(2026-09-10 개편).
 *
 * 🔴 **우리는 예약을 중개하지 않는다**(미결 7번 결정). 그래서 이 시험이
 * 붙드는 것은 모양이 아니라 **바깥으로 나간다는 사실**과 거르기다.
 */
const venue = (over: Partial<Venue> = {}): Venue => ({
  id: 'v1',
  name: '잠실종합운동장 풋살경기장',
  region: '서울 송파구',
  address: '서울 송파구 · 잠실종합운동장 풋살경기장',
  sports: ['soccer'],
  tagline: '유료 대관 · 서울시 공공서비스예약 등록 시설',
  slots: [
    { label: '평일 · 오후', hours: '09:30~17:30', open: true, reserveUrl: 'https://yeyak.example/1' },
    { label: '주말 · 야간', hours: '18:00~22:00', open: false, reserveUrl: 'https://yeyak.example/2' },
  ],
  ...over,
})

const BASE = [
  venue(),
  venue({
    id: 'v2',
    name: '난지천 풋살장',
    region: '서울 마포구',
    sports: ['soccer'],
    slots: [
      { label: '평일 · 주간', hours: '09:00~17:00', open: true, reserveUrl: 'https://yeyak.example/2' },
    ],
  }),
  venue({
    id: 'v3',
    name: '문래 풋살장',
    region: '서울 영등포구',
    sports: ['soccer'],
    // 열린 시간대가 하나도 없는 곳 — 단추 대신 안내가 나와야 한다.
    slots: [{ label: '평일', hours: '06:00~20:00', open: false, reserveUrl: 'https://yeyak.example/3' }],
  }),
  /* 🔴 **뒤에 붙인다** — 위 셋은 `BASE[0]`·`BASE[2]` 로 가리키는 시험이 있어서
     사이에 끼우면 그 시험들이 엉뚱한 구장을 본다(실제로 그렇게 깨졌다). */
  venue({
    id: 'v4',
    name: '잠실 주말 풋살장',
    region: '서울 송파구',
    slots: [
      { label: '토/일/공휴일 · 야간', hours: '18:00~23:00', open: true, reserveUrl: 'https://yeyak.example/4' },
      { label: '토/일/공휴일 · 주간', hours: '09:00~17:00', open: true, reserveUrl: 'https://yeyak.example/5' },
      { label: '평일 · 주간', hours: '09:00~17:00', open: true, reserveUrl: 'https://yeyak.example/6' },
    ],
  }),
]

describe('경기장 예약 판', () => {
  const open = (venues = BASE) => render(<VenueBoard venues={venues} />)

  it('구장을 목록으로 그린다', () => {
    open()
    expect(screen.getByText('잠실종합운동장 풋살경기장')).toBeInTheDocument()
    expect(screen.getByText('난지천 풋살장')).toBeInTheDocument()
    expect(screen.getByText('문래 풋살장')).toBeInTheDocument()
  })

  /* 🔴 **바깥으로 나간다.** 새 탭으로 열고 그 사실을 낭독기에도 알린다 —
     우리가 결제하지 않는 것이 이 화면의 규칙이다. */
  it('예약은 서울시 사이트로 새 탭에서 나간다', () => {
    open([BASE[0]])
    const link = screen.getByRole('link', { name: /예약하러 가기/ })
    expect(link).toHaveAttribute('href', 'https://yeyak.example/1')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'))
    expect(link).toHaveTextContent('새 탭에서')
  })

  /* 눌러도 아무 일이 없으면 안 된다 — 열린 시간대가 없으면 단추를 안 낸다. */
  it('열린 시간대가 없으면 단추 대신 그렇게 적는다', () => {
    open([BASE[2]])
    expect(screen.queryByRole('link', { name: /예약하러 가기/ })).toBeNull()
    expect(screen.getByText('지금은 접수중인 시간대가 없습니다')).toBeInTheDocument()
  })

  /* ⚠️ **실시간이 아니다.** 주석에만 있고 화면에 없었다 — 「접수중」을 보고
     갔는데 마감이면 우리 화면이 거짓말을 한 것이 된다. */
  it('접수 현황이 실시간이 아니라는 것을 적어 둔다', () => {
    const { container } = open()
    // 카드 설명에도 같은 말이 있으므로 **안내줄**로 좁혀서 본다.
    const note = container.querySelector('.ss-vb-note')!
    expect(note).toHaveTextContent('내려받은 시점 기준')
    expect(note).toHaveTextContent('서울시 공공서비스예약')
  })

  describe('거르기', () => {
    /* 🔴 **종목으로 거르는 시험을 걷었다**(2026-09-16, 팀 결정: 풋살 하나만
       한다). 고를 것이 하나뿐이면 거름망이 아니다 — 화면의 탭도, 목록의
       야구장·농구장도 같이 걷었다. 종목을 다시 늘리면 **탭·거름망·이 시험을
       함께** 되살린다. 아래 「고르는 자리가 없다」가 그때 먼저 빨개진다. */
    it('종목을 고르는 자리가 없다', () => {
      open()
      expect(screen.queryByRole('group', { name: '종목' })).toBeNull()
    })

    /* 데이터에 실제로 있는 구만 고를 수 있어야 한다 — 없는 것을 고르면 늘 0건이다. */
    it('지역 알약은 데이터에 있는 구로만 채운다', async () => {
      const user = userEvent.setup()
      const { container } = open()
      await user.click(screen.getByRole('button', { name: '자세히' }))
      const box = container.querySelector('[aria-label="지역"]')!
      expect([...box.querySelectorAll('button')].map((b) => b.textContent)).toEqual([
        '마포구',
        '송파구',
        '영등포구',
      ])
    })

    /* 🔴 **여러 구를 같이 고를 수 있어야 한다**(사용자 결정) — 단일 선택이면
       「마포 아니면 서초」를 한 번에 못 본다. */
    it('지역을 여러 개 고르면 그 구들이 다 남는다', async () => {
      const user = userEvent.setup()
      open()
      await user.click(screen.getByRole('button', { name: '자세히' }))
      await user.click(screen.getByRole('button', { name: '마포구' }))
      expect(screen.getByText('난지천 풋살장')).toBeInTheDocument()
      expect(screen.queryByText('문래 풋살장')).toBeNull()

      await user.click(screen.getByRole('button', { name: '영등포구' }))
      expect(screen.getByText('난지천 풋살장')).toBeInTheDocument()
      expect(screen.getByText('문래 풋살장')).toBeInTheDocument()
    })

    /* 🔴 **시간대 하나라도** 열려 있으면 통과다 — 시설 전체가 닫힌 것과
       한 시간대만 닫힌 것은 다르다. */
    it('접수중만 보면 한 시간대라도 열린 곳이 남는다', async () => {
      const user = userEvent.setup()
      open()
      await user.click(screen.getByRole('button', { name: '접수중만' }))
      expect(screen.getByText('잠실종합운동장 풋살경기장')).toBeInTheDocument()
      expect(screen.queryByText('문래 풋살장')).toBeNull()
    })

    it('걸러서 비면 조건 때문이라고 말한다', async () => {
      const user = userEvent.setup()
      open([BASE[2]])
      await user.click(screen.getByRole('button', { name: '접수중만' }))
      expect(screen.getByText('그 조건에 맞는 구장이 없습니다.')).toBeInTheDocument()
    })

    /* 🔴 **거르는 줄은 결과와 무관하게 늘 그린다** — 결과 안쪽에 두면
       「없습니다」가 떴을 때 거르기가 같이 사라져 되돌릴 길이 없어진다. */
    it('결과가 비어도 거르는 줄은 남아 있다', async () => {
      const user = userEvent.setup()
      open([BASE[2]])
      await user.click(screen.getByRole('button', { name: '접수중만' }))
      expect(screen.getByRole('button', { name: '접수중만' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: '자세히' })).toBeInTheDocument()
    })
  })
  /* ── 세세한 조건(2026-09-10 추가) ─────────────────────────────── */
  describe('자세한 조건', () => {
    /* 늘 펼쳐 두면 목록이 화면 밖으로 밀린다 — 접어 두고 눌러서 연다. */
    it('접혀 있다가 눌러야 나온다', async () => {
      const user = userEvent.setup()
      open()
      expect(screen.queryByRole('button', { name: '마포구' })).toBeNull()
      await user.click(screen.getByRole('button', { name: '자세히' }))
      expect(screen.getByRole('button', { name: '마포구' })).toBeInTheDocument()
    })

    it('시설 이름으로 찾는다', async () => {
      const user = userEvent.setup()
      open()
      await user.type(screen.getByLabelText('시설 이름'), '난지천')
      expect(screen.getByText('난지천 풋살장')).toBeInTheDocument()
      expect(screen.queryByText('문래 풋살장')).toBeNull()
    })

    /* 🔴 요일과 때가 **같은 시간대 하나**에서 걸려야 한다 — 규칙 자체는
       `venueFilter.test.ts` 가 붙들고, 여기서는 화면이 그 규칙을 쓰는지 본다. */
    it('요일과 때로 거른다', async () => {
      const user = userEvent.setup()
      open()
      await user.click(screen.getByRole('button', { name: '자세히' }))
      await user.click(screen.getByRole('button', { name: '주말·공휴일' }))
      // 잠실은 「주말 · 야간」이 있고, 난지천 풋살장은 평일 주간뿐이다.
      expect(screen.getByText('잠실 주말 풋살장')).toBeInTheDocument()
      expect(screen.queryByText('난지천 풋살장')).toBeNull()
    })

    it('그 시각에 열린 곳만 본다', async () => {
      const user = userEvent.setup()
      open()
      await user.click(screen.getByRole('button', { name: '자세히' }))
      await user.selectOptions(screen.getByLabelText('이 시각에 열린 곳'), '21:00')
      expect(screen.getByText('잠실 주말 풋살장')).toBeInTheDocument()
      expect(screen.queryByText('난지천 풋살장')).toBeNull()
    })

    /* 하나씩 끄게 두면 아무도 안 되돌린다. */
    it('조건 비우기로 한 번에 되돌린다', async () => {
      const user = userEvent.setup()
      open()
      await user.click(screen.getByRole('button', { name: '자세히' }))
      await user.click(screen.getByRole('button', { name: '마포구' }))
      expect(screen.queryByText('문래 풋살장')).toBeNull()
      await user.click(screen.getByRole('button', { name: '조건 비우기' }))
      expect(screen.getByText('문래 풋살장')).toBeInTheDocument()
    })
  })

  /* ── 정해 둔 경기 조건(팀 매칭에서 받아 둔 것) ────────────────── */
  describe('내 경기 조건', () => {
    /**
     * 🔴 **조건은 서버에 있다**(계약 3-13절, 2026-09-17). 전에는
     * `localStorage` 를 읽었는데, 팀 매칭 쪽이 서버로 옮겨 가면서 **아무도
     * 그 저장소에 안 쓰게 됐다** — 그대로 뒀으면 이 단추가 늘 「조건이
     * 없습니다」만 내는 죽은 기능이 된다.
     */
    const REGIONS = [
      { id: 'rg-songpa', city: '서울', district: '송파구', label: '서울 송파구' },
    ]

    function prefs(pref: unknown) {
      vi.stubGlobal(
        'fetch',
        vi.fn(async (url: string) => {
          const u = String(url)
          const body = u.startsWith('/api/regions')
            ? REGIONS
            : u.startsWith('/api/positions')
              ? []
              : pref
          return { ok: true, status: 200, json: async () => body }
        }),
      )
    }

    beforeEach(() => __resetRefDataCache())
    afterEach(() => vi.unstubAllGlobals())

    /* 🔴 **여기서 다시 묻지 않는다.** 팀 매칭이 이미 받아 둔 값을 그대로 건다 —
       두 번 물으면 두 값이 어긋난다. */
    it('정해 둔 조건으로 거른다', async () => {
      prefs({
        user_id: 'u1',
        region_ids: ['rg-songpa'],
        slots: [{ weekday: 5, start_time: '18:00:00', end_time: '22:00:00' }],
        position_ids: [],
      })
      const user = userEvent.setup()
      open()
      await user.click(screen.getByRole('button', { name: '자세히' }))
      await user.click(screen.getByRole('button', { name: '정해 둔 조건에 맞는 곳만' }))
      expect(await screen.findByText('내 조건으로 걸렀습니다.')).toBeInTheDocument()
      expect(screen.getByText('잠실 주말 풋살장')).toBeInTheDocument()
      expect(screen.queryByText('난지천 풋살장')).toBeNull()
    })

    /* 조용히 0건이 되면 고장으로 읽힌다 — 왜 못 걸렀는지 말한다. */
    it('정해 둔 조건이 없으면 그렇게 말하고 안 거른다', async () => {
      prefs({ user_id: 'u1', region_ids: [], slots: [], position_ids: [] })
      const user = userEvent.setup()
      open()
      await user.click(screen.getByRole('button', { name: '자세히' }))
      await user.click(screen.getByRole('button', { name: '정해 둔 조건에 맞는 곳만' }))
      expect(await screen.findByText(/아직 정해 둔 경기 조건이 없습니다/)).toBeInTheDocument()
      expect(screen.getByText('난지천 풋살장')).toBeInTheDocument()
    })
  })

  /* 사용자 결정: 실제로 잡을 수 있는 곳이 위로 온다. */
  it('접수중인 시간대가 많은 곳부터 세운다', () => {
    const { container } = open()
    const names = [...container.querySelectorAll('.ss-vb-name')].map((e) => e.textContent)
    expect(names[0]).toBe('잠실 주말 풋살장')
    expect(names[names.length - 1]).toBe('문래 풋살장')
  })
})

