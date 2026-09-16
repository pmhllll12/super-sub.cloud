import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 알림 목록 (계약 3-12절). **폴링이다** — 실시간 전달 경로가 없다.
 *
 * 🔴 **문구가 없다.** `type`·`actor_user_id` 만 오므로 문장은 화면이 짓는다.
 */
export async function GET(req: NextRequest) {
  const unreadOnly = req.nextUrl.searchParams.get('unread_only') === 'true'
  return withAuth(req, async (token) =>
    NextResponse.json(await getBackend().listNotifications(token, unreadOnly)),
  )
}
