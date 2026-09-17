/**
 * 비교 요약을 **코드 규칙으로** 쓴다(2026-09-14 결정 — Gemini 없이).
 *
 * 🔴 숫자는 입력 그대로다 — 지어낼 여지가 없다. 나중에 Gemini 로 코칭 문장을 얹고 싶으면
 * 같은 `SummaryRequest` 를 넘기는 층을 더한다(응답 파싱 · 숫자 검사는 `summaryContract.ts`).
 */
import type { SummaryRequest } from './summaryContract'
import { MOMENT_LABEL, type MetricId, type MetricRow, type MomentKey } from './types'

/** 이보다 작은 차이는 「비슷함」 — 브라우저 검출의 흔들림이 몇 도는 된다. */
export const SIMILAR_DEG = 5

export type ComparisonText = { moments: { key: MomentKey; lines: string[] }[]; summary: string }

/** `more` 는 **내 값이 선수보다 클 때**의 말이다. 값이 크다는 뜻이 항목마다 다르다. */
const PHRASE: Record<MetricId, { more: string; less: string }> = {
  plant_knee_flexion: { more: '디딤발 무릎을 {d}° 덜 굽혔습니다', less: '디딤발 무릎을 {d}° 더 굽혔습니다' },
  swing_knee_extension: { more: '차는 다리를 {d}° 더 폈습니다', less: '차는 다리를 {d}° 덜 폈습니다' },
  trunk_lean: {
    more: '상체가 차는 방향으로 {d}° 더 기울었습니다',
    less: '상체가 차는 방향으로 {d}° 덜 기울었습니다',
  },
  follow_through: { more: '차는 다리를 {d}° 더 높이 들었습니다', less: '차는 다리를 {d}° 덜 높이 들었습니다' },
}

export function describeLine(r: MetricRow): string {
  const d = r.user - r.player
  const base = `${r.label} 선수 ${r.player}° · 나 ${r.user}°`
  if (Math.abs(d) < SIMILAR_DEG) return `${base} — 비슷합니다`
  const phrase = d > 0 ? PHRASE[r.id].more : PHRASE[r.id].less
  return `${base} — ${phrase.replace('{d}', String(Math.abs(d)))}`
}

export function describeComparison(req: SummaryRequest): ComparisonText {
  let biggest: { key: MomentKey; row: MetricRow; gap: number } | null = null
  let measured = 0
  const moments = req.moments.map((m) => {
    for (const row of m.metrics) {
      measured += 1
      const gap = Math.abs(row.user - row.player)
      if (gap >= SIMILAR_DEG && (!biggest || gap > biggest.gap)) biggest = { key: m.key, row, gap }
    }
    return {
      key: m.key,
      lines: m.metrics.length ? m.metrics.map(describeLine) : ['이 순간은 잴 수 없었습니다'],
    }
  })

  const top = biggest as { key: MomentKey; row: MetricRow; gap: number } | null
  const summary =
    measured === 0
      ? '잴 수 있는 순간이 없어 비교하지 못했습니다.'
      : !top
        ? '세 순간 모두 선수와 비슷합니다.'
        : `가장 큰 차이는 ${MOMENT_LABEL[top.key]}의 ${top.row.label}입니다 — 선수 ${top.row.player}° · 나 ${top.row.user}°(${top.gap}° 차이).`
  return { moments, summary }
}
