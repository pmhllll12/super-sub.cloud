import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/** 지인 신청 수락 — 내가 대상인 대기중 신청만 (계약 3-12절). */
export async function POST(req: NextRequest, ctx: { params: Promise<{ contactId: string }> }) {
  const { contactId } = await ctx.params
  return withAuth(req, async (token) =>
    NextResponse.json(await getBackend().acceptContact(token, contactId)),
  )
}
