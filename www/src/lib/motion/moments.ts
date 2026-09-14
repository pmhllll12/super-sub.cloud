/**
 * 세 순간 — 직전 · 임팩트 · +1초.
 *
 * 🔴 **임팩트는 에이전트와 같은 정의다** — `agent/src/supersub_agent/features.py` 의
 * `segment_phases`(`extension_peak`): 차는 다리 무릎 신전 각속도가 최대인 프레임.
 * 서버 값으로 바꿔도 뜻이 안 갈린다. 언어 모델을 쓰지 않는다(재현성이 필요한 구간).
 */
import { kneeAngle, legOf, seen } from './angles'
import type { Leg, MomentsResult, Motion } from './types'

export function kneeSeries(motion: Motion, leg: Leg): (number | null)[] {
  return motion.frames.map((f) => (f ? kneeAngle(f, leg, motion.aspect) : null))
}

/** 중앙 차분(도/초). 양옆이 비면 `null`. */
export function velocity(series: (number | null)[], fps: number): (number | null)[] {
  return series.map((_, i) => {
    const a = series[i - 1]
    const b = series[i + 1]
    return a == null || b == null ? null : ((b - a) / 2) * fps
  })
}

function pickIndex(
  values: (number | null)[],
  from: number,
  to: number,
  better: (v: number, best: number) => boolean,
): number {
  let best = -1
  for (let i = Math.max(0, from); i <= Math.min(values.length - 1, to); i += 1) {
    const v = values[i]
    if (v == null) continue
    if (best < 0 || better(v, values[best] as number)) best = i
  }
  return best
}

export function detectMoments(motion: Motion): MomentsResult {
  const legs = (['left', 'right'] as const).map((leg) => {
    const series = kneeSeries(motion, leg)
    const v = velocity(series, motion.fps)
    const peak = pickIndex(v, 0, v.length - 1, (a, b) => a > b)
    return { leg, series, peak, speed: peak < 0 ? -Infinity : (v[peak] as number) }
  })
  const kick = legs[0].speed >= legs[1].speed ? legs[0] : legs[1]
  if (kick.peak < 0 || kick.speed <= 0) {
    return { ok: false, reason: '차는 다리의 관절을 충분히 잡지 못했습니다' }
  }

  const impact = kick.peak
  const first = kick.series.findIndex((x) => x != null)
  const last = kick.series.length - 1 - [...kick.series].reverse().findIndex((x) => x != null)
  if (impact - first < 2 || last - impact < 2) {
    return { ok: false, reason: '동작 앞뒤가 잘린 영상으로 보입니다' }
  }

  // 임팩트의 각속도를 재려면 바로 앞 프레임이 잡혀 있어야 하므로 이 창에는 값이 늘 있다.
  const window = Math.max(1, Math.round(0.5 * motion.fps))
  const before = pickIndex(kick.series, impact - window, impact - 1, (a, b) => a < b)

  let after = impact + Math.round(motion.fps)
  const afterClipped = after > last
  if (afterClipped) after = last

  const ankle = legOf(kick.leg).ankle
  const a = motion.frames[before]?.[ankle]
  const b = motion.frames[impact]?.[ankle]
  const direction: 1 | -1 = seen(a) && seen(b) && b.x < a.x ? -1 : 1

  return {
    ok: true,
    moments: { kickingLeg: kick.leg, direction, before, impact, after, afterClipped },
  }
}
