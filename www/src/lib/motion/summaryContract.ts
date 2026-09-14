/**
 * Gemini 비교 요약의 **요청 · 응답 약속**. 서버 라우트와 화면이 같은 파일을 쓴다 —
 * 두 벌로 두면 한쪽만 늙는다.
 *
 * 🔴 보내는 것은 **숫자와 항목 이름뿐**이다(영상 · 사진 · 사용자 정보 없음).
 */
import { metricsAt, sideAt } from './angles'
import {
  MOMENT_KEYS,
  type Leg,
  type MetricId,
  type MomentKey,
  type MomentMetrics,
  type Moments,
  type Motion,
} from './types'

export type SummaryRequest = {
  player: string
  kickingLeg: { player: Leg; user: Leg }
  mirrored: boolean
  measuredBy: 'browser' | 'agent'
  moments: MomentMetrics[]
}

export type SummaryResponse = {
  moments: { key: MomentKey; text: string }[]
  summary: string
  drills: string[]
}

type Analyzed = { motion: Motion; moments: Moments }

export function buildSummaryRequest(
  playerName: string,
  player: Analyzed,
  user: Analyzed,
  mirrored: boolean,
): SummaryRequest {
  return {
    player: playerName,
    kickingLeg: { player: player.moments.kickingLeg, user: user.moments.kickingLeg },
    mirrored,
    measuredBy:
      player.motion.measuredBy === 'agent' && user.motion.measuredBy === 'agent' ? 'agent' : 'browser',
    moments: MOMENT_KEYS.map((key) => {
      const p = sideAt(player.motion, player.moments, key)
      const u = sideAt(user.motion, user.moments, key)
      return { key, metrics: p && u ? metricsAt(key, p, u) : [] }
    }),
  }
}

/** 항목마다 받을 수 있는 값 범위(도). 상체 기울기는 뒤로면 음수다. */
const RANGE: Record<MetricId, [number, number]> = {
  plant_knee_flexion: [0, 180],
  swing_knee_extension: [0, 180],
  trunk_lean: [-90, 90],
  follow_through: [-90, 180],
}

const isObj = (x: unknown): x is Record<string, unknown> => typeof x === 'object' && x !== null
const isLeg = (x: unknown): x is Leg => x === 'left' || x === 'right'
const inRange = (id: MetricId, v: unknown) =>
  typeof v === 'number' && Number.isFinite(v) && v >= RANGE[id][0] && v <= RANGE[id][1]

/** 맞으면 요청을, 틀리면 **오류 문구**를 돌려준다. */
export function validateSummaryRequest(x: unknown): SummaryRequest | string {
  if (!isObj(x)) return '요청 형식이 잘못되었습니다.'
  if (typeof x.player !== 'string' || !x.player.trim() || x.player.length > 40) {
    return 'player 는 1~40자여야 합니다.'
  }
  if (!isObj(x.kickingLeg) || !isLeg(x.kickingLeg.player) || !isLeg(x.kickingLeg.user)) {
    return 'kickingLeg 가 잘못되었습니다.'
  }
  if (typeof x.mirrored !== 'boolean') return 'mirrored 가 필요합니다.'
  if (x.measuredBy !== 'browser' && x.measuredBy !== 'agent') return 'measuredBy 가 잘못되었습니다.'
  if (!Array.isArray(x.moments) || x.moments.length !== MOMENT_KEYS.length) {
    return 'moments 는 셋이어야 합니다.'
  }
  const moments: MomentMetrics[] = []
  for (let i = 0; i < MOMENT_KEYS.length; i += 1) {
    const m = x.moments[i]
    if (!isObj(m) || m.key !== MOMENT_KEYS[i] || !Array.isArray(m.metrics)) {
      return 'moments 는 before · impact · after 차례여야 합니다.'
    }
    const metrics = []
    for (const r of m.metrics) {
      if (!isObj(r) || typeof r.id !== 'string' || !(r.id in RANGE)) return '모르는 항목입니다.'
      const id = r.id as MetricId
      if (!inRange(id, r.player) || !inRange(id, r.user)) return `${id} 값이 범위를 벗어났습니다.`
      if (typeof r.label !== 'string' || r.label.length > 40 || r.unit !== '°') {
        return `${id} 이름표가 잘못되었습니다.`
      }
      metrics.push({ id, label: r.label, player: r.player as number, user: r.user as number, unit: '°' as const })
    }
    moments.push({ key: MOMENT_KEYS[i], metrics })
  }
  return {
    player: x.player,
    kickingLeg: { player: x.kickingLeg.player, user: x.kickingLeg.user },
    mirrored: x.mirrored,
    measuredBy: x.measuredBy,
    moments,
  }
}

export function parseSummaryResponse(text: string): SummaryResponse | null {
  const bare = text.trim().replace(/^```(?:json)?\s*/i, '').replace(/```$/, '').trim()
  let x: unknown
  try {
    x = JSON.parse(bare)
  } catch {
    return null
  }
  if (!isObj(x) || typeof x.summary !== 'string' || !x.summary.trim()) return null
  if (!Array.isArray(x.drills) || x.drills.length < 2 || x.drills.length > 3) return null
  if (!x.drills.every((d) => typeof d === 'string' && d.trim())) return null
  if (!Array.isArray(x.moments) || x.moments.length !== MOMENT_KEYS.length) return null
  const moments: { key: MomentKey; text: string }[] = []
  for (let i = 0; i < MOMENT_KEYS.length; i += 1) {
    const m = x.moments[i]
    if (!isObj(m) || m.key !== MOMENT_KEYS[i] || typeof m.text !== 'string' || !m.text.trim()) return null
    moments.push({ key: MOMENT_KEYS[i], text: m.text })
  }
  return { moments, summary: x.summary, drills: x.drills as string[] }
}

/** 🔴 문장에 나온 `N°`·`N도` 가 입력 값이나 두 값의 차이(±1)가 아니면 근거 없음. */
export function isGrounded(res: SummaryResponse, req: SummaryRequest): boolean {
  const allowed: number[] = []
  for (const m of req.moments) {
    for (const r of m.metrics) allowed.push(r.player, r.user, Math.abs(r.player - r.user))
  }
  const texts = [res.summary, ...res.drills, ...res.moments.map((m) => m.text)]
  for (const t of texts) {
    for (const hit of t.matchAll(/(-?\d+(?:\.\d+)?)\s*(?:°|도)/g)) {
      const n = Math.abs(Number(hit[1]))
      if (!allowed.some((a) => Math.abs(Math.abs(a) - n) <= 1)) return false
    }
  }
  return true
}
