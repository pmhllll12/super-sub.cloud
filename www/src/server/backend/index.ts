import type { Backend } from './gateway'
import { mockBackend } from './mock'

/**
 * mock/실제 전환은 서버에서만 일어난다.
 * USE_MOCK 에 NEXT_PUBLIC_ 을 붙이지 않는다 — 클라이언트 번들에 박힌다.
 */
export function getBackend(): Backend {
  if (process.env.USE_MOCK === '1') return mockBackend
  // Task 11 에서 fastapiBackend 로 바꾼다.
  return mockBackend
}

export type { Backend } from './gateway'
export * from './types'
export { BackendError, errorResponseBody } from './errors'
