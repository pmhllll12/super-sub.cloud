export class BackendError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    /**
     * 429 일 때 서버가 준 `Retry-After`(**정수 초**) — 계약 1번(SEC-009).
     *
     * 🔴 **고정값이 아니라 그 시점에 남은 시간**이다. 올림한 값이라 그만큼
     * 기다리면 반드시 한 자리가 비어 있다 — **자체 타이머를 만들지 않는다.**
     * 임의의 상수(무조건 60초)를 두면 필요 이상으로 기다리게 된다.
     */
    readonly retryAfter?: number,
  ) {
    super(message)
    this.name = 'BackendError'
  }
}

/**
 * `Retry-After` 헤더를 초로 읽는다. 없거나 숫자가 아니면 `undefined` 다.
 *
 * ⚠️ HTTP 는 **날짜 형식**(`Retry-After: Wed, 21 Oct 2026 …`)도 허용하지만
 * 계약은 정수 초로 정했다 — 날짜가 오면 못 읽은 것으로 치고 넘어간다.
 * 잘못 읽어 0 으로 만들면 잠금이 곧바로 풀려 제한을 지키지 못한다.
 */
export function readRetryAfter(headers: Headers | null | undefined): number | undefined {
  const raw = headers?.get('retry-after')
  if (!raw) return undefined
  const n = Number(raw)
  return Number.isFinite(n) && n >= 0 ? n : undefined
}

/**
 * FastAPI 의 에러 본문을 BackendError 로 바꾼다.
 *
 * 백엔드가 항상 계약 형태로 준다는 보장은 없다 — 프록시가 끼어들면
 * HTML 이 오기도 한다. 그때도 던지지 않고 UNKNOWN_ERROR 로 떨어뜨린다.
 */
export function parseErrorBody(
  status: number,
  body: unknown,
  retryAfter?: number,
): BackendError {
  if (
    body !== null &&
    typeof body === 'object' &&
    'error' in body &&
    typeof (body as Record<string, unknown>).error === 'object'
  ) {
    const err = (body as { error: Record<string, unknown> }).error
    if (typeof err?.code === 'string') {
      const message = typeof err.message === 'string' ? err.message : '알 수 없는 오류입니다.'
      return new BackendError(status, err.code, message, retryAfter)
    }
  }
  return new BackendError(status, 'UNKNOWN_ERROR', '서버와 통신하지 못했습니다.', retryAfter)
}

export function errorResponseBody(e: BackendError) {
  return { error: { code: e.code, message: e.message } }
}
