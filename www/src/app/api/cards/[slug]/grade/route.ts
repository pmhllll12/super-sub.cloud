import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 남의 **표시 등급** (계약 3-6절, CCC 43번).
 *
 * 🔴 **등급과 `provisional` 은 늘 짝으로 나간다.** 등급 문자만 떼어 쓰면
 * 받는 쪽에서 검수 전 값인지 알 방법이 없어진다 — 남의 화면에 박힌 등급은
 * 회수가 안 된다(정상호 조건). 그래서 이 경로는 서버 응답을 **그대로**
 * 흘려보내고 한 칸도 골라 담지 않는다.
 */
export async function GET(req: NextRequest, ctx: { params: Promise<{ slug: string }> }) {
  const { slug } = await ctx.params
  return withAuth(req, async (token) =>
    NextResponse.json(await getBackend().getCardGrade(token, slug)),
  )
}
