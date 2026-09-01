export class BackendError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message)
    this.name = 'BackendError'
  }
}

/**
 * FastAPI 의 에러 본문을 BackendError 로 바꾼다.
 *
 * 백엔드가 항상 계약 형태로 준다는 보장은 없다 — 프록시가 끼어들면
 * HTML 이 오기도 한다. 그때도 던지지 않고 UNKNOWN_ERROR 로 떨어뜨린다.
 */
export function parseErrorBody(status: number, body: unknown): BackendError {
  if (
    body !== null &&
    typeof body === 'object' &&
    'error' in body &&
    typeof (body as Record<string, unknown>).error === 'object'
  ) {
    const err = (body as { error: Record<string, unknown> }).error
    if (typeof err?.code === 'string') {
      const message = typeof err.message === 'string' ? err.message : '알 수 없는 오류입니다.'
      return new BackendError(status, err.code, message)
    }
  }
  return new BackendError(status, 'UNKNOWN_ERROR', '서버와 통신하지 못했습니다.')
}

export function errorResponseBody(e: BackendError) {
  return { error: { code: e.code, message: e.message } }
}
