import { BackendError, parseErrorBody } from './errors'

/**
 * FastAPI 를 직접 부르는 낮은 층 — `Backend` 인터페이스의 두 구현
 * (`fastapiBackend.ts`, 영상 업로드 라우트 핸들러)이 공유해서 쓴다.
 *
 * `token` 은 선택이다 — 로그인·회원가입·구글 로그인처럼 아직 토큰이 없는
 * 호출도 이 함수를 그대로 쓴다.
 */
export async function callFastApi<T>(
  path: string,
  opts: { method: 'GET' | 'POST' | 'PATCH' | 'DELETE'; token?: string; body?: unknown },
): Promise<T> {
  const base = process.env.BACKEND_BASE_URL
  // 🔴 여기서 잡지 않은 예외는 route handler를 그대로 깨뜨린다 — Next.js가
  // 빈 본문의 500을 돌려주고, 브라우저는 그걸 JSON으로 읽으려다
  // "Unexpected end of JSON input"이라는 뜻 모를 에러를 낸다(실측, 2026-09-03).
  // BackendError로만 던져야 withAuth의 catch(toErrorResponse)가 계약 형태
  // ({"error": {code, message}})로 바꿔 준다.
  if (!base) {
    throw new BackendError(503, 'BACKEND_NOT_CONFIGURED', 'BACKEND_BASE_URL이 설정되어 있지 않습니다.')
  }

  let res: Response
  try {
    res = await fetch(`${base}${path}`, {
      method: opts.method,
      headers: {
        ...(opts.token ? { Authorization: `Bearer ${opts.token}` } : {}),
        ...(opts.body ? { 'Content-Type': 'application/json' } : {}),
      },
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    })
  } catch (e) {
    // DNS 실패·연결 거부 등 네트워크 계층 오류 — fetch가 Response 대신 예외를 던진다.
    throw new BackendError(
      503,
      'BACKEND_UNREACHABLE',
      `백엔드 서버에 연결하지 못했습니다: ${e instanceof Error ? e.message : String(e)}`,
    )
  }

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
