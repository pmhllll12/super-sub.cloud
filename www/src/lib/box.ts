/** 상자 하나와 상자끼리의 셈. 좌표는 늘 **영상 그림 안** 0~1 정규화다. */

export type Box = { x: number; y: number; w: number; h: number }

export const cx = (b: Box) => b.x + b.w / 2
export const cy = (b: Box) => b.y + b.h / 2

/** 두 상자의 겹침 비율(0~1). */
export function iou(a: Box, b: Box): number {
  const x1 = Math.max(a.x, b.x)
  const y1 = Math.max(a.y, b.y)
  const x2 = Math.min(a.x + a.w, b.x + b.w)
  const y2 = Math.min(a.y + a.h, b.y + b.h)
  const w = x2 - x1
  const h = y2 - y1
  if (w <= 0 || h <= 0) return 0
  const inter = w * h
  return inter / (a.w * a.h + b.w * b.h - inter)
}

/**
 * 가운데끼리의 거리 — **상자 키로 나눈다.**
 *
 * 🔴 화면 비율로 재면 안 된다. 멀리 있는 사람은 작게 잡히고 화면에서 조금만
 * 움직여도 자기 키의 몇 배를 간다 — 같은 문턱으로 재면 가까운 사람은 놓치고
 * 먼 사람은 아무 데나 붙는다. 사람 키를 자로 삼으면 원근에 상관없이 같다.
 */
export function centerDist(a: Box, b: Box): number {
  return Math.hypot(cx(a) - cx(b), cy(a) - cy(b)) / Math.max(1e-6, a.h)
}

/** 크기가 얼마나 다른가(0 이면 같다). */
export function sizeGap(a: Box, b: Box): number {
  return Math.abs(Math.log(Math.max(1e-6, b.h) / Math.max(1e-6, a.h)))
}
