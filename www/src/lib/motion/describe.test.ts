import { describeComparison, describeLine } from './describe'
import type { SummaryRequest } from './summaryContract'
import type { MetricRow } from './types'

const row = (id: MetricRow['id'], label: string, player: number, user: number): MetricRow => ({
  id,
  label,
  player,
  user,
  unit: '°',
})

function req(moments: SummaryRequest['moments']): SummaryRequest {
  return {
    player: '에스테반 로벨리',
    kickingLeg: { player: 'right', user: 'right' },
    mirrored: false,
    measuredBy: 'browser',
    moments,
  }
}

describe('규칙 문장', () => {
  it('차이가 5° 미만이면 비슷하다고 적는다', () => {
    expect(describeLine(row('trunk_lean', '상체 기울기', 10, 13))).toBe('상체 기울기 선수 10° · 나 13° — 비슷합니다')
  })

  // 🔴 값이 크다는 뜻이 항목마다 다르다 — 무릎각이 크면 「덜 굽힘」, 뻗기가 크면 「더 폄」.
  it('항목마다 방향에 맞는 말로 차이를 적는다', () => {
    expect(describeLine(row('plant_knee_flexion', '디딤발 무릎 굽히기', 142, 158))).toBe(
      '디딤발 무릎 굽히기 선수 142° · 나 158° — 디딤발 무릎을 16° 덜 굽혔습니다',
    )
    expect(describeLine(row('swing_knee_extension', '차는 다리 뻗기', 171, 149))).toBe(
      '차는 다리 뻗기 선수 171° · 나 149° — 차는 다리를 22° 덜 폈습니다',
    )
    expect(describeLine(row('trunk_lean', '상체 기울기', 12, -5))).toBe(
      '상체 기울기 선수 12° · 나 -5° — 상체가 차는 방향으로 17° 덜 기울었습니다',
    )
    expect(describeLine(row('follow_through', '차고 난 뒤 마무리', 40, 60))).toBe(
      '차고 난 뒤 마무리 선수 40° · 나 60° — 차는 다리를 20° 더 높이 들었습니다',
    )
  })

  it('순간마다 줄을 모으고, 잰 항목이 없으면 그렇다고 적는다', () => {
    const text = describeComparison(
      req([
        { key: 'before', metrics: [row('trunk_lean', '상체 기울기', 10, 13)] },
        { key: 'impact', metrics: [] },
        { key: 'after', metrics: [] },
      ]),
    )
    expect(text.moments.map((m) => m.key)).toEqual(['before', 'impact', 'after'])
    expect(text.moments[1].lines).toEqual(['이 순간은 잴 수 없었습니다'])
  })

  it('총평은 가장 큰 차이를 짚는다', () => {
    const text = describeComparison(
      req([
        { key: 'before', metrics: [row('plant_knee_flexion', '디딤발 무릎 굽히기', 142, 158)] },
        { key: 'impact', metrics: [row('swing_knee_extension', '차는 다리 뻗기', 171, 149)] },
        { key: 'after', metrics: [] },
      ]),
    )
    expect(text.summary).toBe('가장 큰 차이는 접촉의 차는 다리 뻗기입니다 — 선수 171° · 나 149°(22° 차이).')
  })

  it('모두 5° 미만이면 비슷하다고, 잰 것이 없으면 비교하지 못했다고 적는다', () => {
    const similar = describeComparison(
      req([
        { key: 'before', metrics: [row('trunk_lean', '상체 기울기', 10, 13)] },
        { key: 'impact', metrics: [] },
        { key: 'after', metrics: [] },
      ]),
    )
    expect(similar.summary).toBe('세 순간 모두 선수와 비슷합니다.')
    const none = describeComparison(
      req([
        { key: 'before', metrics: [] },
        { key: 'impact', metrics: [] },
        { key: 'after', metrics: [] },
      ]),
    )
    expect(none.summary).toBe('잴 수 있는 순간이 없어 비교하지 못했습니다.')
  })
})
