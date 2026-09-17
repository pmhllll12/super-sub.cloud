import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/** 알림 읽음 처리 — **멱등이다**(이미 읽었어도 200). 계약 3-12절. */
export async function PATCH(
  req: NextRequest,
  ctx: { params: Promise<{ notificationId: string }> },
) {
  const { notificationId } = await ctx.params
  return withAuth(req, async (token) =>
    NextResponse.json(await getBackend().readNotification(token, notificationId)),
  )
}
