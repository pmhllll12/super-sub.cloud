import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 내가 올린 클립을 지운다 — **저장소의 영상 파일과 그 분석 리포트까지.**
 *
 * 🔴 무엇을 어디서 지울지는 **서버가 정한다.** 브라우저는 저장 키도 리포트
 * 자리도 모르고, 알려 주면 남의 것을 지목할 수 있게 된다.
 *
 * ⚠️ **계약에 아직 이 경로가 없다**(미결 paik 13번). 진짜 백엔드에서는 404 가
 * 오고, 화면은 그 사유를 그대로 띄운다 — 지운 척하지 않는다.
 */
export async function DELETE(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params
  return withAuth(req, async (token) => {
    await getBackend().deleteMyVideo(token, id)
    // 본문이 없다. 지운 것에 대해 돌려줄 표현이 없다.
    return new NextResponse(null, { status: 204 })
  })
}
