import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/** 관리자 전용 — 한 사람의 영상 전부(계약 3-2절). `user`(id 또는 이메일) 필수. */
export async function GET(req: NextRequest) {
  return withAuth(req, async (token) => {
    const { searchParams } = new URL(req.url)
    const user = searchParams.get('user') ?? ''
    return NextResponse.json(await getBackend().listAdminVideos(token, user))
  })
}
