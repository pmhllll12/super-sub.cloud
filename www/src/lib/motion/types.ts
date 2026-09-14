/**
 * 선수 비교 분석이 주고받는 모양(설계 `www/docs/2026-09-14-선수-비교-분석-design.md`).
 *
 * 🔴 `Motion` 은 **어디서 왔는지 모르는 모양**이다 — 지금은 브라우저가 뽑고
 * (`measuredBy: 'browser'`), 최종에는 에이전트 결과를 서버에서 받는다(미결 paik 29 · 30).
 * 화면은 이 모양만 안다.
 */
import type { Point } from '@/lib/pose'

export type Leg = 'left' | 'right'
export type MomentKey = 'before' | 'impact' | 'after'
export type MetricId = 'plant_knee_flexion' | 'swing_knee_extension' | 'trunk_lean' | 'follow_through'

export type Motion = {
  /** 실제로 잰 간격(초당 장수). */
  fps: number
  /** 영상 가로/세로. 좌표가 가로 · 세로 따로 0~1 로 눌려 있어 각도를 잴 때 되돌린다. */
  aspect: number
  /** 프레임마다 COCO 17점. 못 잡은 프레임은 `null` 로 자리를 지킨다. */
  frames: (Point[] | null)[]
  measuredBy: 'browser' | 'agent'
}

export type Moments = {
  kickingLeg: Leg
  /** 차는 방향 — 화면 오른쪽이 1. */
  direction: 1 | -1
  before: number
  impact: number
  after: number
  /** 영상이 임팩트 + 1초 전에 끝나 마지막 유효 프레임으로 대신했는가. */
  afterClipped: boolean
}

export type MomentsResult = { ok: true; moments: Moments } | { ok: false; reason: string }

export type MetricRow = { id: MetricId; label: string; player: number; user: number; unit: '°' }
export type MomentMetrics = { key: MomentKey; metrics: MetricRow[] }

export const MOMENT_KEYS: readonly MomentKey[] = ['before', 'impact', 'after']

export const MOMENT_LABEL: Record<MomentKey, string> = {
  before: '직전',
  impact: '임팩트',
  after: '+1초',
}

/** 🔴 루브릭(`agent/rubrics/football_instep_shot.yaml`)의 `criteria[].name` 그대로. */
export const METRIC_LABEL: Record<MetricId, string> = {
  plant_knee_flexion: '디딤발 무릎 굽히기',
  swing_knee_extension: '차는 다리 뻗기',
  trunk_lean: '상체 기울기',
  follow_through: '차고 난 뒤 마무리',
}
