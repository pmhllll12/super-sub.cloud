import { kickMotion } from './kickFixture'
import { detectMoments } from './moments'
import {
  buildSummaryRequest,
  isGrounded,
  parseSummaryResponse,
  validateSummaryRequest,
  type SummaryRequest,
  type SummaryResponse,
} from './summaryContract'

function sides() {
  const pm = kickMotion()
  const um = kickMotion({ lean: 0.05 })
  const p = detectMoments(pm)
  const u = detectMoments(um)
  if (!p.ok || !u.ok) throw new Error('순간을 못 찾음')
  return { player: { motion: pm, moments: p.moments }, user: { motion: um, moments: u.moments } }
}

describe('요약 요청 만들기', () => {
  it('세 순간을 차례대로, 루브릭 항목으로 채운다', () => {
    const { player, user } = sides()
    const req = buildSummaryRequest('에스테반 로벨리', player, user, false)
    expect(req.moments.map((m) => m.key)).toEqual(['before', 'impact', 'after'])
    expect(req.kickingLeg).toEqual({ player: 'right', user: 'right' })
    expect(req.measuredBy).toBe('browser')
    expect(req.moments[1].metrics[0]).toMatchObject({ id: 'plant_knee_flexion', player: 160, user: 160 })
  })
})

describe('요청 검사', () => {
  const ok = (): SummaryRequest => {
    const { player, user } = sides()
    return buildSummaryRequest('에스테반 로벨리', player, user, false)
  }

  it('맞는 요청은 그대로 돌려준다', () => {
    const req = ok()
    expect(validateSummaryRequest(JSON.parse(JSON.stringify(req)))).toEqual(req)
  })

  it('순간이 셋이 아니면 거절한다', () => {
    const req = ok()
    expect(typeof validateSummaryRequest({ ...req, moments: req.moments.slice(0, 2) })).toBe('string')
  })

  it('모르는 항목 id 는 거절한다', () => {
    const req = ok()
    req.moments[0].metrics[0] = { ...req.moments[0].metrics[0], id: 'hip_rotation' as never }
    expect(typeof validateSummaryRequest(req)).toBe('string')
  })

  // 상체 기울기는 뒤로 기울면 음수라 범위가 따로다.
  it('항목마다 값의 범위를 본다', () => {
    const req = ok()
    const lean = req.moments[1].metrics.find((m) => m.id === 'trunk_lean')!
    lean.user = -20
    expect(typeof validateSummaryRequest(req)).not.toBe('string')
    lean.user = 120
    expect(typeof validateSummaryRequest(req)).toBe('string')
  })

  it('이름이 40자를 넘으면 거절한다', () => {
    expect(typeof validateSummaryRequest({ ...ok(), player: '가'.repeat(41) })).toBe('string')
  })
})

describe('응답', () => {
  const good: SummaryResponse = {
    moments: [
      { key: 'before', text: '직전에 무릎을 더 접었습니다.' },
      { key: 'impact', text: '임팩트에서 상체가 10° 더 기울었습니다.' },
      { key: 'after', text: '마무리가 비슷합니다.' },
    ],
    summary: '전체적으로 비슷합니다.',
    drills: ['상체 세우기', '디딤발 무릎 굽히기'],
  }

  it('모양이 맞으면 읽는다', () => {
    expect(parseSummaryResponse(JSON.stringify(good))).toEqual(good)
  })

  it('JSON 이 아니거나 모양이 틀리면 null 이다', () => {
    expect(parseSummaryResponse('안녕하세요')).toBeNull()
    expect(parseSummaryResponse(JSON.stringify({ ...good, drills: [] }))).toBeNull()
    expect(parseSummaryResponse(JSON.stringify({ ...good, moments: good.moments.slice(1) }))).toBeNull()
  })

  it('코드 울타리(```json)로 감싸 와도 읽는다', () => {
    expect(parseSummaryResponse('```json\n' + JSON.stringify(good) + '\n```')).toEqual(good)
  })

  // 🔴 지어낸 숫자를 화면에 안 올린다 — 입력 값이나 두 값의 차이(±1)만 허용.
  it('문장 속 각도가 입력 값이나 차이가 아니면 근거 없음이다', () => {
    const req: SummaryRequest = {
      player: '에스테반 로벨리',
      kickingLeg: { player: 'right', user: 'right' },
      mirrored: false,
      measuredBy: 'browser',
      moments: [
        { key: 'before', metrics: [] },
        { key: 'impact', metrics: [{ id: 'trunk_lean', label: '상체 기울기', player: 2, user: 12, unit: '°' }] },
        { key: 'after', metrics: [] },
      ],
    }
    expect(isGrounded(good, req)).toBe(true) // 10° = 12 − 2
    const made: SummaryResponse = { ...good, summary: '무릎이 37도 더 굽었습니다.' }
    expect(isGrounded(made, req)).toBe(false)
  })
})
