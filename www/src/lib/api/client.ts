'use client'

export class ApiCallError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message)
    this.name = 'ApiCallError'
  }
}

/**
 * 같은 오리진의 /api/* 만 부른다. 브라우저는 FastAPI 주소를 모른다.
 * 쿠키는 same-origin 이라 자동으로 실린다.
 */
async function send<T>(method: 'POST' | 'PATCH', path: string, body: unknown): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, {
      method,
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    })
  } catch {
    throw new ApiCallError(0, 'NETWORK_ERROR', '서버에 연결하지 못했습니다.')
  }

  const data = await res.json().catch(() => null)
  if (!res.ok) {
    const err = (data as { error?: { code?: string; message?: string } } | null)?.error
    throw new ApiCallError(
      res.status,
      err?.code ?? 'UNKNOWN_ERROR',
      err?.message ?? '알 수 없는 오류입니다.',
    )
  }
  return data as T
}

export const apiPost = <T>(path: string, body: unknown) => send<T>('POST', path, body)
export const apiPatch = <T>(path: string, body: unknown) => send<T>('PATCH', path, body)

/** 화면이 보여줄 에러 문구. 서버가 준 message 를 그대로 쓰고, 그 외에는 일반 문구로 떨어진다. */
export function apiErrorMessage(err: unknown): string {
  return err instanceof ApiCallError ? err.message : '알 수 없는 오류입니다.'
}
