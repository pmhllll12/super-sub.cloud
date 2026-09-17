import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 닉네임으로 사람 찾기 (계약 3-12절, CCC 37번).
 *
 * 🔴 **`q` 가 비면 서버를 부르지 않고 빈 배열이다.** 계약상 `q` 는 필수고,
 * 전체 명단을 주는 경로가 아니다 — 빈 질의를 그대로 넘기면 422 가 되고,
 * 화면은 글자를 지울 때마다 그 오류를 보게 된다.
 */
export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams.get('q')?.trim() ?? ''
  return withAuth(req, async (token) =>
    NextResponse.json(q ? await getBackend().searchUsers(token, q) : []),
  )
}
