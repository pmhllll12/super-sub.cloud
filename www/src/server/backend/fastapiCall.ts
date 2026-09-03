import { parseErrorBody } from './errors'

/**
 * FastAPI 를 직접 부른다 — `getBackend()`/`Backend` 를 거치지 않는다.
 *
 * 🔴 **임시로 좁게 낸 길이다.** `Backend` 인터페이스는 아직 영상 업로드를
 * 모르고(jin-12), `getBackend()` 는 `USE_MOCK` 과 무관하게 늘 mock 을 반환한다
 * (jin-10, 미결). 그 둘을 아우르는 실제 게이트웨이(`fastapiBackend`)를 만드는
 * 일은 범위가 커서 이 자리에서 하지 않는다 — 영상 업로드 라우트 핸들러만
 * `BACKEND_BASE_URL` 을 직접 불러 쓴다. `Backend` 가 정리되면 이 파일은
 * 그리로 흡수돼야 한다.
 */
export async function callFastApi<T>(
  path: string,
  opts: { method: 'GET' | 'POST'; token: string; body?: unknown },
): Promise<T> {
  const base = process.env.BACKEND_BASE_URL
  if (!base) throw new Error('BACKEND_BASE_URL 이 설정되어 있지 않습니다.')

  const res = await fetch(`${base}${path}`, {
    method: opts.method,
    headers: {
      Authorization: `Bearer ${opts.token}`,
      ...(opts.body ? { 'Content-Type': 'application/json' } : {}),
    },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  })

  const text = await res.text()
  let json: unknown = null
  try {
    json = text ? JSON.parse(text) : null
  } catch {
    // 계약 형태가 아닌 응답(프록시가 HTML 을 주는 경우 등) — parseErrorBody 가 떨어뜨린다.
  }

  if (!res.ok) throw parseErrorBody(res.status, json)
  return json as T
}
