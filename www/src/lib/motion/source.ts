/**
 * 🔴 **교체 지점 — 화면은 이 파일만 부른다.**
 *
 * 지금은 브라우저가 뽑는다(`extract.ts`, 데모). 서버가 에이전트의 프레임별 관절 ·
 * fps 를 주기 시작하면(미결 paik 29 · 30) **여기서 그 경로를 부르도록만** 바꾼다 —
 * 세 순간 · 겹치기 · 각도 · 요약은 `Motion` 모양만 보므로 그대로 쓴다.
 */
import { extractMotion, type Pick } from './extract'
import type { Motion } from './types'

export type MotionInput = { src: string; pick: Pick }

export function getMotion(
  input: MotionInput,
  opts: { signal?: AbortSignal; onProgress?: (ratio: number) => void } = {},
): Promise<Motion> {
  return extractMotion(input.src, { pick: input.pick, ...opts })
}
