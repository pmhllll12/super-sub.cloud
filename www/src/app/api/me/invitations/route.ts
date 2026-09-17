import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 내가 받은, **아직 답 안 한** 초대만 — 최신순(계약 3-3절, CCC 53번).
 *
 * 🔴 받는 사람은 **아직 그 팀 소속이 아니라** 팀 이름을 따로 읽을 길이 없다.
 * 그래서 팀 이름·지역·종목·스쿼드 슬러그 넉 칸이 함께 온다.
 */
export async function GET(req: NextRequest) {
  return withAuth(req, async (token) =>
    NextResponse.json(await getBackend().listMyInvitations(token)),
  )
}
