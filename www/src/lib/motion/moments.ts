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

/**
 * `target`이 잡혔으면 그대로, 아니면 `[lo, hi]` 안에서 가장 가까운 잡힌 프레임(동률이면
 * 더 이른 쪽). `hi` 안에 잡힌 프레임이 하나도 없으면 -1(호출부에서 늘 있음을 보장한다).
 */
function nearestUsable(series: (number | null)[], target: number, lo: number, hi: number): number {
  if (series[target] != null) return target
  let best = -1
  let bestDist = Infinity
  for (let i = Math.max(0, lo); i <= Math.min(series.length - 1, hi); i += 1) {
    if (series[i] == null) continue
    const dist = Math.abs(i - target)
    if (dist < bestDist) {
      best = i
      bestDist = dist
    }
  }
  return best
}

export function detectMoments(motion: Motion): MomentsResult {
  const legs = (['left', 'right'] as const).map((leg) => {
    const series = kneeSeries(motion, leg)
    const v = velocity(series, motion.fps)
    // velocity[i]는 series[i-1]·series[i+1]만 보므로 그 프레임 자신의 무릎각이 없어도
    // 값이 나올 수 있다 — series[i]가 없는 프레임은 임팩트 후보에서 뺀다.
    const usable = v.map((val, i) => (series[i] == null ? null : val))
    const peak = pickIndex(usable, 0, usable.length - 1, (a, b) => a > b)
    return { leg, series, peak, speed: peak < 0 ? -Infinity : (usable[peak] as number) }
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

  /* 🔴 직전 = 임팩트 0.3초 전(2026-09-15 사용자 결정 — 예전엔 「임팩트 앞 0.5초 안에서
     무릎이 가장 굽은 프레임」이었는데, 그 프레임이 구조상 임팩트 바로 한 프레임 전으로
     쏠려 두 카드가 거의 같은 자세로 보였다). 그 프레임에 관절이 없으면 가장 가까운
     잡힌 프레임을 쓴다 — 임팩트의 각속도를 재려면 `impact - 1`은 반드시 잡혀 있으므로
     `[first, impact - 1]` 안에는 항상 후보가 있다. */
  const beforeTarget = Math.max(first, impact - Math.round(0.3 * motion.fps))
  const before = nearestUsable(kick.series, beforeTarget, first, impact - 1)

  let after = impact + Math.round(motion.fps)
  const afterClipped = after > last
  if (afterClipped) after = last

  /* 🔴 방향은 **임팩트 바로 한 프레임 전(`impact - 1`)** 과 비교해 잰다 — `before` 가 아니다.
     `before` 는 이제 0.3초 앞이라(위) 되접는 동작 도중일 수 있어, 되접기 + 펴기가 섞인
     구간에서는 가로 이동 부호가 실제로 차는 방향과 반대로 나올 수 있다(2026-09-15,
     `before` 재정의로 드러남). `impact - 1` 은 늘 잡혀 있고(임팩트 각속도 계산 조건)
     펴는 도중의 마지막 한 걸음이라 방향이 안정적이다. */
  const ankle = legOf(kick.leg).ankle
  const swingStart = impact - 1
  const a = motion.frames[swingStart]?.[ankle]
  const b = motion.frames[impact]?.[ankle]
  const direction: 1 | -1 = seen(a) && seen(b) && b.x < a.x ? -1 : 1

  return {
    ok: true,
    moments: { kickingLeg: kick.leg, direction, before, impact, after, afterClipped },
  }
}
