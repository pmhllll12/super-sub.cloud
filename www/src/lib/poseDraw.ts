/**
 * 영상 위에 **상자와 뼈대를 그리는 셈**.
 *
 * 분석 화면의 내 영상(`AnalysisStage`)과 비교 칸의 선수 영상(`ComparePlayer`)이
 * 같은 셈을 쓴다 — 두 벌로 두면 한쪽만 보정이 고쳐져 막대기가 어긋난다.
 */
import type { Box } from './box'
import type { Point } from './pose'
import type { Leg } from './motion/types'
import { skeletonShapes, toGrid } from './skeleton'

/** 뼈대를 그리는 좌표계 — 실제 크기와 무관한 고정 격자다(SVG `viewBox`). */
export const POSE_VB = 1000

/**
 * 판(`el`) 안에서 영상 그림이 차지하는 비율. 🔴 `<video>` 는 `object-fit:
 * contain` 이라 판 비율과 영상 비율이 다르면 **레터박스 여백**이 생긴다 —
 * 그 여백을 빼야 그림 위의 자리가 맞는다. 세로 영상일수록 크게 어긋난다.
 */
function fit(r: DOMRect, video: HTMLVideoElement | null) {
  const vw = video?.videoWidth ?? 0
  const vh = video?.videoHeight ?? 0
  if (!vw || !vh || !r.width || !r.height) return null
  const scale = Math.min(r.width / vw, r.height / vh)
  return { cw: (vw * scale) / r.width, ch: (vh * scale) / r.height }
}

/** 영상 안 좌표(0~1) → 판 좌표(0~1). */
export function toViewBox(box: Box, el: HTMLElement, video: HTMLVideoElement | null): Box {
  const f = fit(el.getBoundingClientRect(), video)
  if (!f) return box
  return {
    x: (1 - f.cw) / 2 + box.x * f.cw,
    y: (1 - f.ch) / 2 + box.y * f.ch,
    w: box.w * f.cw,
    h: box.h * f.ch,
  }
}

/**
 * 여러 사람의 자세를 **세 줄의 `d`** 로 모은다 — 뼈(머리 원 · 척추 포함) · 차는 다리 · 관절.
 * 모양은 `lib/skeleton.ts` 가 정한다(세 순간 카드와 같은 모양).
 *
 * 🔴 관절 17개에 선 12개를 각각의 요소로 두면 프레임마다 DOM 을 수십 번 만진다.
 * 관절점은 **길이 0 인 선**이다 — 둥근 끝이 붙어 점으로 보인다.
 *
 * 🔴 판 크기는 **한 번만** 잰다 — 점마다 `getBoundingClientRect` 를 부르면 초당 60번 ×
 * 17번 레이아웃을 읽는다.
 */
export function posePaths(
  poses: Point[][],
  el: HTMLElement,
  video: HTMLVideoElement | null,
  { kickingLeg = null }: { kickingLeg?: Leg | null } = {},
) {
  const r = el.getBoundingClientRect()
  // 🔴 상자(`toViewBox`)와 **같은 보정**을 거친다 — 한쪽만 보정하면 막대기가 상자와 어긋난다.
  const { cw, ch } = fit(r, video) ?? { cw: 1, ch: 1 }
  // 격자 한 칸의 화면 px — 머리 원이 늘어난 격자에서도 원으로 보이게(`skeletonShapes`).
  const sx = r.width ? r.width / POSE_VB : 1
  const sy = r.height ? r.height / POSE_VB : 1

  let bones = ''
  let kick = ''
  let joints = ''
  for (const pose of poses) {
    const pts = toGrid(pose, (p) => ({
      x: ((1 - cw) / 2 + p.x * cw) * POSE_VB,
      y: ((1 - ch) / 2 + p.y * ch) * POSE_VB,
    }))
    const shape = skeletonShapes(pts, { kickingLeg, sx, sy })
    bones += shape.bones
    kick += shape.kick
    joints += shape.joints
  }
  return { bones, kick, joints }
}
