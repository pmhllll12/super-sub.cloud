import { fetchReport, toSavedReport } from './savedReports'
import type { VideoReport } from '@/server/backend'

/**
 * 🔴 **여기가 계약과 화면 사이의 유일한 옮김터다**(CCC 31). 서버는 항목 배열
 * (`breakdown[]`)을 주고 화면은 칭호+문장 짝 목록을 그린다(`ho` 24번) —
 * 그 사이의 판단을 이 시험이 붙든다.
 */
const report = (over: Partial<VideoReport> = {}): VideoReport => ({
  video_id: 'v1',
  analyzed_at: '2026-09-03T09:00:00Z',
  summary: '디딤발이 공보다 앞서 있습니다.',
  provisional: true,
  total_score: 71,
  overall_grade: 'B',
  breakdown: [
    {
      criterion_id: 'plant_foot_position',
      name: '디딤발 위치',
      grade: 2,
      title: '흔들리지 않는 축',
      evidence: '측면으로 벌리는 움직임이 많습니다',
      metric_ref: 'plant_foot_offset',
      skipped: false,
      stat: 88.5,
    },
  ],
  scenes: [{ metric_code: 'impact_frame', label: '임팩트', at_seconds: 7.5 }],
  previews: null,
  keypoint_quality: null,
  ...over,
})

describe('리포트 옮기기', () => {
  it('요약 · 항목(칭호+문장 짝) · 장면 · 오버롤 · 레이더를 화면 모양으로 옮긴다', () => {
    expect(toSavedReport(report())).toEqual({
      summary: '디딤발이 공보다 앞서 있습니다.',
      points: [{ title: '흔들리지 않는 축', evidence: '측면으로 벌리는 움직임이 많습니다' }],
      scenes: [{ at: '0:07', what: '임팩트' }],
      totalScore: 71,
      overallGrade: 'B',
      radar: [{ name: '디딤발 위치', stat: 88.5 }],
      savedAt: '2026-09-03',
    })
  })

  // 옛 리포트(이 필드가 생기기 전 적재분)는 오버롤이 null — 그대로 옮긴다.
  it('오버롤이 없는 옛 리포트는 null 그대로 옮긴다', () => {
    const r = report({ total_score: null, overall_grade: null })
    const out = toSavedReport(r)
    expect(out.totalScore).toBeNull()
    expect(out.overallGrade).toBeNull()
  })

  /* 🔴 **`skipped` 는 「평가 대상이 아니었다」는 뜻이다**(`grade: null` 과 짝).
     빈 문장으로라도 그리면 못한 것으로 읽힌다. */
  it('평가 대상이 아니었던 항목은 빼고 그린다', () => {
    const r = report({
      breakdown: [
        ...report().breakdown,
        {
          criterion_id: 'jump_height',
          name: '점프 높이',
          grade: null,
          title: '안 받은 호칭',
          evidence: '안 본 항목',
          metric_ref: null,
          skipped: true,
          stat: null,
        },
      ],
    })
    const out = toSavedReport(r)
    expect(out.points).toEqual([
      { title: '흔들리지 않는 축', evidence: '측면으로 벌리는 움직임이 많습니다' },
    ])
    expect(JSON.stringify(out.points)).not.toContain('안 받은 호칭')
    // 레이더도 마찬가지 — 0으로 그리면 "그 항목을 못했다"로 잘못 읽힌다.
    expect(out.radar.map((a) => a.name)).not.toContain('점프 높이')
  })

  /* 🔴 **호칭은 서버가 채운 것만이다.** 「어느 등급부터 받은 호칭인가」가
     계약에 없어서 우리가 `grade === 2` 같은 선을 그으면 그게 곧 지어내는
     것이다(미결로 올려 둔다). 호칭이 없어도 **문장은 그대로 남는다** —
     `ho` 24번이 막은 것은 title 없이 evidence만 있는 것이 아니라, 그 반대
     (문장을 지워 통째로 사라지는 것)다. */
  it('호칭이 비어 있어도 문장은 그대로 남고 칭호만 없다', () => {
    const r = report({
      breakdown: [{ ...report().breakdown[0], grade: 1, title: null }],
    })
    expect(toSavedReport(r).points).toEqual([
      { title: null, evidence: '측면으로 벌리는 움직임이 많습니다' },
    ])
  })

  /* 🔴 초는 **버림**이다 — 올리면 그 장면이 이미 지나 있다. */
  it('시각을 분:초로 적는다', () => {
    const r = report({ scenes: [{ metric_code: 'm', label: '임팩트', at_seconds: 65.9 }] })
    expect(toSavedReport(r).scenes[0].at).toBe('1:05')
  })

  /* 🔴 **정정 (CCC 32)**: 이 시험이 앞서 "수치를 화면 모양에 담지 않는다"를
     검사했던 것은 지금은 틀렸다 — 오버롤·`stat` 은 이제 담는다(위 시험들).
     여전히 안 새는 것은 항목별 원시 등급(0/1/2 정수, `breakdown[].grade`)이다
     — 화면은 `radar` 의 연속값(`stat`)만 쓰고 정수 등급은 안 옮긴다. */
  it('항목별 원시 등급(0/1/2)은 화면 모양에 담지 않는다', () => {
    const out = toSavedReport(report())
    expect(JSON.stringify(out.points)).not.toMatch(/"grade"/)
    expect(JSON.stringify(out.radar)).not.toMatch(/"grade"/)
  })
})

describe('리포트 읽기', () => {
  const stub = (res: { ok: boolean; status?: number; body?: unknown }) => {
    const fn = vi.fn().mockResolvedValue({
      ok: res.ok,
      status: res.status ?? (res.ok ? 200 : 404),
      json: async () => res.body,
    })
    vi.stubGlobal('fetch', fn)
    return fn
  }
  afterEach(() => vi.unstubAllGlobals())

  it('계약 경로를 부른다', async () => {
    const fn = stub({ ok: true, body: report() })
    await fetchReport('v 1')
    // 아이디는 주소에 그대로 붙이지 않는다 — 공백·슬래시가 경로를 바꾼다.
    expect(fn.mock.calls[0][0]).toBe('/api/videos/v%201/report')
  })

  /* 🔴 **「아직」과 「없다」와 「고장」을 가른다.** 셋을 뭉치면 분석 중인 클립이
     결과 없는 클립처럼 보인다(미결 `paik` 7번의 「하지 말 것」). */
  it('적재 전이면 not-ready', async () => {
    stub({ ok: false, body: { error: { code: 'REPORT_NOT_READY', message: '아직입니다.' } } })
    expect(await fetchReport('v1')).toEqual({ state: 'not-ready' })
  })

  it('없는 영상이면 missing', async () => {
    stub({ ok: false, body: { error: { code: 'VIDEO_NOT_FOUND', message: '없습니다.' } } })
    expect(await fetchReport('v1')).toEqual({ state: 'missing' })
  })

  // 🔴 정정(2026-09-11): 그전엔 이 코드가 not-ready 로 갔다 — 다시 확인해도
  // 절대 안 바뀌는데 "아직입니다"로 보여 사용자가 실제로 헷갈렸다.
  it('분석이 실패했으면 failed — 사유를 그대로 들고 온다', async () => {
    stub({
      ok: false,
      body: {
        error: { code: 'ANALYSIS_FAILED', message: '품질 게이트 미달: 재촬영이 필요합니다.' },
      },
    })
    expect(await fetchReport('v1')).toEqual({
      state: 'failed',
      reason: '품질 게이트 미달: 재촬영이 필요합니다.',
    })
  })

  it('그 밖의 실패는 사유를 들고 온다', async () => {
    stub({ ok: false, status: 500, body: { error: { code: 'X', message: '서버가 아픕니다.' } } })
    expect(await fetchReport('v1')).toEqual({ state: 'error', message: '서버가 아픕니다.' })
  })

  // 계약 형태가 아닌 응답(프록시의 HTML 등)에도 화면이 안 죽는다.
  it('본문이 계약 형태가 아니어도 죽지 않는다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 502,
        json: async () => {
          throw new Error('not json')
        },
      }),
    )
    expect(await fetchReport('v1')).toEqual({
      state: 'error',
      message: '리포트를 읽지 못했습니다.',
    })
  })
})
