import { nextOccurrence, proposalsFrom } from './matchProposal'
import type { TimeSlot } from './matchPrefs'

/**
 * **조건 슬롯 → 실제 경기 시각** (미결 `paik` 22번 후속).
 *
 * 🔴 후보 응답에는 **경기 시각·구장이 없다**(팀 후보이지 경기 공고가 아니다).
 * 그런데 신청은 `played_at`·`place` 를 필수로 받는다 — 그 시각을 **우리
 * 조건에서 만든다**(지어내지 않는다). 「토 11:00」이면 **다음 토요일 11:00**.
 */
const SAT_11: TimeSlot = { day: 6, from: '11:00', to: '13:00' }

describe('다음 그 요일 그 시각', () => {
  /* 2026-09-17 은 목요일이다. */
  const THU = new Date('2026-09-17T10:00:00+09:00')

  it('목요일에 「토 11:00」을 고르면 이틀 뒤 토요일이다', () => {
    const at = nextOccurrence(SAT_11, THU)
    expect(at.getDay()).toBe(6)
    expect(at.getDate()).toBe(19)
    expect(at.getHours()).toBe(11)
    expect(at.getMinutes()).toBe(0)
  })

  /**
   * 🔴 **같은 요일이고 시각이 이미 지났으면 다음 주다.** 지난 시각으로
   * 신청하면 서버가 받아 줘도 아무도 못 뛴다.
   */
  it('같은 요일인데 시각이 지났으면 다음 주다', () => {
    const satAfternoon = new Date('2026-09-19T15:00:00+09:00')
    const at = nextOccurrence(SAT_11, satAfternoon)
    expect(at.getDay()).toBe(6)
    expect(at.getDate()).toBe(26)
  })

  it('같은 요일이고 시각이 아직 안 됐으면 오늘이다', () => {
    const satMorning = new Date('2026-09-19T08:00:00+09:00')
    expect(nextOccurrence(SAT_11, satMorning).getDate()).toBe(19)
  })

  /* 30분 단위 시각도 그대로 살린다. */
  it('30분 단위를 잃지 않는다', () => {
    const at = nextOccurrence({ day: 6, from: '11:30', to: '13:00' }, THU)
    expect(at.getHours()).toBe(11)
    expect(at.getMinutes()).toBe(30)
  })
})

describe('고를 수 있는 시각 목록', () => {
  const THU = new Date('2026-09-17T10:00:00+09:00')

  it('조건 슬롯마다 한 줄씩, 이른 것이 앞에 온다', () => {
    const out = proposalsFrom(
      [
        { day: 0, from: '09:00', to: '11:00' },
        { day: 6, from: '11:00', to: '13:00' },
      ],
      THU,
    )
    expect(out).toHaveLength(2)
    // 목요일 기준으로 토(19일)가 일(20일)보다 앞이다.
    expect(out[0].at.getDate()).toBe(19)
    expect(out[1].at.getDate()).toBe(20)
  })

  /* 🔴 조건이 없으면 **빈 목록**이다 — 아무 시각이나 지어내지 않는다. */
  it('조건이 없으면 빈 목록이다', () => {
    expect(proposalsFrom([], THU)).toEqual([])
  })

  it('사람이 읽을 이름을 함께 준다', () => {
    const [first] = proposalsFrom([SAT_11], THU)
    expect(first.label).toContain('토')
    expect(first.label).toContain('11:00')
  })
})

/**
 * 🔴 **`toISOString()` 을 쓰지 않는다.** 그건 UTC 로 바꿔서 「토 11:00」이
 * 「토 02:00」으로 저장된다 — 사람이 고른 것은 **한국 시각의 11시**다.
 */
describe('계약에 실을 시각', () => {
  it('고른 시각을 그대로 적는다 — UTC 로 밀지 않는다', async () => {
    const { toPlayedAt } = await import('./matchProposal')
    const at = new Date('2026-09-19T11:00:00+09:00')
    // 이 기계의 표준시가 무엇이든, 적히는 시각은 `at` 의 **현지 시각**이다.
    expect(toPlayedAt(at)).toContain(`T${String(at.getHours()).padStart(2, '0')}:00:00`)
    expect(toPlayedAt(at)).not.toBe(at.toISOString())
  })
})
