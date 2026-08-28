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
export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, {
      method: 'POST',
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
