/**
 * 영상 위에 **상자와 뼈대를 그리는 셈**.
 *
 * 분석 화면의 내 영상(`AnalysisStage`)과 비교 칸의 선수 영상(`ComparePlayer`)이
 * 같은 셈을 쓴다 — 두 벌로 두면 한쪽만 보정이 고쳐져 막대기가 어긋난다.
 */
import type { Box } from './box'
import { EDGES, L_SHOULDER, MIN_KP, NOSE, R_SHOULDER, type Point } from './pose'

/** 뼈대를 그리는 좌표계 — 실제 크기와 무관한 고정 격자다(SVG `viewBox`). */
export const POSE_VB = 1000

/**
 * 판(`el`) 안에서 영상 그림이 차지하는 비율. 🔴 `<video>` 는 `object-fit:
 * contain` 이라 판 비율과 영상 비율이 다르면 **레터박스 여백**이 생긴다 —
 * 그 여백을 빼야 그림 위의 자리가 맞는다. 세로 영상일수록 크게 어긋난다.
 */
function fit(el: HTMLElement, video: HTMLVideoElement | null) {
  const r = el.getBoundingClientRect()
  const vw = video?.videoWidth ?? 0
  const vh = video?.videoHeight ?? 0
  if (!vw || !vh || !r.width || !r.height) return null
  const scale = Math.min(r.width / vw, r.height / vh)
  return { cw: (vw * scale) / r.width, ch: (vh * scale) / r.height }
}

/** 영상 안 좌표(0~1) → 판 좌표(0~1). */
export function toViewBox(box: Box, el: HTMLElement, video: HTMLVideoElement | null): Box {
  const f = fit(el, video)
  if (!f) return box
  return {
    x: (1 - f.cw) / 2 + box.x * f.cw,
    y: (1 - f.ch) / 2 + box.y * f.ch,
    w: box.w * f.cw,
    h: box.h * f.ch,
  }
}

/**
 * 관절 한 점을 영상 안 좌표 → 판 좌표로. 🔴 상자와 **같은 보정**을 거쳐야 한다 —
 * 한쪽만 보정하면 막대기가 상자와 어긋난 자리에 그려진다.
 */
export function toViewPoint(p: Point, el: HTMLElement, video: HTMLVideoElement | null): Point {
  const f = fit(el, video)
  if (!f) return p
  return { x: (1 - f.cw) / 2 + p.x * f.cw, y: (1 - f.ch) / 2 + p.y * f.ch, score: p.score }
}

/**
 * 여러 사람의 자세를 뼈 · 관절 **두 줄의 `d`** 로 모은다.
 *
 * 🔴 관절 17개에 선 12개를 각각의 요소로 두면 프레임마다 DOM 을 수십 번 만진다.
 * 관절점은 **길이 0 인 선**이다 — 둥근 끝이 붙어 점으로 보인다.
 */
export function posePaths(poses: Point[][], el: HTMLElement, video: HTMLVideoElement | null) {
  let bones = ''
  let joints = ''
  for (const pose of poses) {
    const pt = pose.map((p) => toViewPoint(p, el, video))
    const at = (i: number) => `${(pt[i].x * POSE_VB).toFixed(1)} ${(pt[i].y * POSE_VB).toFixed(1)}`
    const seen = (i: number) => pt[i] && pt[i].score >= MIN_KP

    for (const [a, b] of EDGES) {
      if (!seen(a) || !seen(b)) continue
      bones += `M${at(a)}L${at(b)}`
    }
    // 목 — 코와 두 어깨의 가운데를 잇는다. 고개 방향만 남긴다.
    if (seen(NOSE) && seen(L_SHOULDER) && seen(R_SHOULDER)) {
      const mx = ((pt[L_SHOULDER].x + pt[R_SHOULDER].x) / 2) * POSE_VB
      const my = ((pt[L_SHOULDER].y + pt[R_SHOULDER].y) / 2) * POSE_VB
      bones += `M${at(NOSE)}L${mx.toFixed(1)} ${my.toFixed(1)}`
    }
    for (let i = 0; i < pt.length; i += 1) {
      if (seen(i)) joints += `M${at(i)}L${at(i)}`
    }
  }
  return { bones, joints }
}
