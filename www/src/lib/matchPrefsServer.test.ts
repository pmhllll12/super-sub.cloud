import { toServerSlot, toScreenSlot, toServerPrefs, toScreenPrefs } from './matchPrefsServer'
import type { Region } from '@/server/backend'

/**
 * **화면 모양 ↔ 계약 모양** (CCC 40번).
 *
 * 🔴 **요일 기준이 서로 다르다.** 화면의 `day` 는 `Date.getDay()` 와 같은
 * **0(일)~6(토)** 이고, 계약의 `weekday` 는 **0(월)~6(일)** 이다 — 그냥
 * 넘기면 **하루씩 밀린다.** 여기가 그 유일한 변환 자리다.
 */
const REGIONS: Region[] = [
  { id: 'rg-001', city: '서울', district: '강남구', label: '서울 강남구' },
  { id: 'rg-010', city: '서울', district: '마포구', label: '서울 마포구' },
]

describe('요일 기준 — 화면 0=일, 계약 0=월', () => {
  it('일요일은 화면 0 · 계약 6 이다', () => {
    expect(toServerSlot({ day: 0, from: '09:00', to: '11:00' }).weekday).toBe(6)
  })

  it('월요일은 화면 1 · 계약 0 이다', () => {
    expect(toServerSlot({ day: 1, from: '09:00', to: '11:00' }).weekday).toBe(0)
  })

  it('토요일은 화면 6 · 계약 5 이다', () => {
    expect(toServerSlot({ day: 6, from: '09:00', to: '11:00' }).weekday).toBe(5)
  })

  /* 🔴 **왕복해서 제자리여야 한다** — 한쪽만 맞으면 저장할 때와 읽을 때가 갈린다. */
  it('이레 전부 왕복해서 제자리다', () => {
    for (let day = 0; day < 7; day += 1) {
      const slot = { day, from: '09:00', to: '11:00' }
      expect(toScreenSlot(toServerSlot(slot)).day).toBe(day)
    }
  })

  it('시각은 계약이 HH:MM:SS 를 쓰고 화면은 HH:MM 이다', () => {
    const s = toServerSlot({ day: 6, from: '09:00', to: '11:30' })
    expect(s.start_time).toBe('09:00:00')
    expect(s.end_time).toBe('11:30:00')
    expect(toScreenSlot(s)).toEqual({ day: 6, from: '09:00', to: '11:30' })
  })
})

describe('지역 — 이름이 아니라 id 로 보낸다', () => {
  it('고른 이름을 id 로 바꿔 보낸다', () => {
    const out = toServerPrefs({ regions: ['서울 마포구'], times: [], positions: [] }, REGIONS)
    expect(out.region_ids).toEqual(['rg-010'])
  })

  /* 🔴 **모르는 이름은 버린다** — 그대로 보내면 422 `UNKNOWN_REGION` 으로
     저장이 통째로 실패한다(계약은 통째로 교체다). */
  it('목록에 없는 이름은 실어 보내지 않는다', () => {
    const out = toServerPrefs({ regions: ['화성 어딘가'], times: [], positions: [] }, REGIONS)
    expect(out.region_ids).toEqual([])
  })

  it('받은 id 를 화면 이름으로 되돌린다', () => {
    const out = toScreenPrefs({ team_id: 't1', region_ids: ['rg-001'], slots: [] }, REGIONS)
    expect(out.regions).toEqual(['서울 강남구'])
  })

  /* 서버가 준 id 를 목록에서 못 찾으면 **지어내지 않는다** — 그 줄을 뺀다. */
  it('모르는 id 는 이름을 지어내지 않고 뺀다', () => {
    const out = toScreenPrefs({ team_id: 't1', region_ids: ['rg-999'], slots: [] }, REGIONS)
    expect(out.regions).toEqual([])
  })
})
