import { fastapiBackend } from './fastapiBackend'
import type { Backend } from './gateway'
import { mockBackend } from './mock'

/**
 * mock/실제 전환은 서버에서만 일어난다.
 * USE_MOCK 에 NEXT_PUBLIC_ 을 붙이지 않는다 — 클라이언트 번들에 박힌다.
 *
 * jin-10 해소(2026-09-03) — `USE_MOCK=1`이 아니면 이제 진짜 FastAPI를 부른다.
 * `BACKEND_BASE_URL`이 실제로 응답하는 주소를 가리켜야 한다(`fastapiCall.ts`).
 */
export function getBackend(): Backend {
  if (process.env.USE_MOCK === '1') return mockBackend
  return fastapiBackend
}

export type { Backend } from './gateway'
export * from './types'
export { BackendError, errorResponseBody } from './errors'
