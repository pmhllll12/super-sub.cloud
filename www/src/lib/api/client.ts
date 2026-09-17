'use client'

export class ApiCallError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    /**
     * 429 일 때 **얼마나 기다려야 하는가**(정수 초) — 계약 1번(SEC-009).
     *
     * 🔴 **서버가 준 값이다.** 그 시점에 남은 시간이라 대부분 60초보다 짧고,
     * 올림한 값이라 그만큼 기다리면 반드시 한 자리가 비어 있다. 임의의 상수를
     * 두면 필요 이상으로 기다리게 된다.
     */
    readonly retryAfter?: number,
  ) {
    super(message)
    this.name = 'ApiCallError'
  }
}

/**
 * 같은 오리진의 /api/* 만 부른다. 브라우저는 FastAPI 주소를 모른다.
 * 쿠키는 same-origin 이라 자동으로 실린다.
 */
async function send<T>(
  method: 'POST' | 'PATCH' | 'DELETE',
  path: string,
  body?: unknown,
): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, {
      method,
      ...(body !== undefined
        ? { headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) }
        : {}),
    })
  } catch {
    throw new ApiCallError(0, 'NETWORK_ERROR', '서버에 연결하지 못했습니다.')
  }

  // 204 No Content 는 본문이 없다 — json() 을 부르면 그 자체로 예외가 난다.
  const data = res.status === 204 ? null : await res.json().catch(() => null)
  if (!res.ok) {
    const err = (data as { error?: { code?: string; message?: string } } | null)?.error
    /* 🔴 **헤더를 여기서 읽는다.** 위층(화면)은 `Response` 를 못 보므로, 이
       자리를 지나면 `Retry-After` 를 알 길이 없다. BFF 가 다시 실어 준
       값이다(`server/handler.ts`). */
    const raw = res.headers.get('retry-after')
    const secs = raw === null ? NaN : Number(raw)
    throw new ApiCallError(
      res.status,
      err?.code ?? 'UNKNOWN_ERROR',
      err?.message ?? '알 수 없는 오류입니다.',
      Number.isFinite(secs) && secs >= 0 ? secs : undefined,
    )
  }
  return data as T
}

export const apiPost = <T>(path: string, body: unknown) => send<T>('POST', path, body)
export const apiPatch = <T>(path: string, body: unknown) => send<T>('PATCH', path, body)
/** 🔴 DELETE 도 본문을 받는다 — 탈퇴가 비밀번호를 함께 보낸다(계약 2장).
 *  `body` 를 안 주면 예전처럼 본문 없이 나간다. */
export const apiDelete = <T = void>(path: string, body?: unknown) =>
  send<T>('DELETE', path, body)

/** 화면이 보여줄 에러 문구. 서버가 준 message 를 그대로 쓰고, 그 외에는 일반 문구로 떨어진다. */
export function apiErrorMessage(err: unknown): string {
  return err instanceof ApiCallError ? err.message : '알 수 없는 오류입니다.'
}

/**
 * **요청이 너무 잦아 거부된 것인가** — 429 `TOO_MANY_REQUESTS`(계약 1번).
 *
 * 🔴 **status 가 아니라 `code` 로 가른다.** 같은 429 라도 다른 제한이 생길 수
 * 있고, 계약이 클라이언트는 `code` 로 분기한다고 정했다.
 */
export function isRateLimited(err: unknown): boolean {
  return err instanceof ApiCallError && err.code === 'TOO_MANY_REQUESTS'
}

/**
 * 429 거부에서 **몇 초 기다려야 하는가.** 429 가 아니면 `null`.
 *
 * 🔴 **서버가 값을 안 줬으면 `0` 이 아니라 최소 1초를 준다.** 0 이면 잠금이
 * 곧바로 풀려 「429 직후 재요청이 안 나간다」는 성질이 깨진다 — 헤더가
 * 중간에서 사라지는 일이 실제로 있었다(그걸 고치는 것이 이 항목이다).
 */
export function retryAfterSeconds(err: unknown): number | null {
  if (!isRateLimited(err)) return null
  const secs = (err as ApiCallError).retryAfter
  return secs !== undefined && secs > 0 ? Math.ceil(secs) : 1
}
