import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 나에게 온 **대기중** 지인 신청 (계약 3-12절).
 *
 * ⚠️ 내가 **보낸** 신청은 여기 안 온다 — 계약에 그 경로가 없다. 보낸 쪽은
 * 수락되기 전까지 목록 어디에서도 안 보이므로, 화면이 「신청함」을 보여
 * 주려면 누른 사실을 화면이 직접 들고 있어야 한다.
 */
export async function GET(req: NextRequest) {
  return withAuth(req, async (token) =>
    NextResponse.json(await getBackend().listContactRequests(token)),
  )
}
