import { NextResponse } from 'next/server'
import { getBackend } from '@/server/backend'
import { toErrorResponse } from '@/server/handler'

/**
 * 공개 슬러그로 읽는 **남의 스쿼드** — 계약 3-7절 `GET /squads/{public_slug}`.
 *
 * 🔴 **`withAuth` 를 쓰지 않는다.** 슬러그 자체가 접근 통제라(SEC-005) 계약이
 * 인증 없이 열어 둔 경로다 — 공개 카드(`/api/cards/[slug]`)와 같은 모양이다.
 * 초대받은 사람은 **아직 그 팀 소속이 아니어서**, 소속을 요구하면 판을 보고
 * 수락 여부를 정할 수가 없다(미결 `paik` 37번).
 */
export async function GET(_req: Request, ctx: { params: Promise<{ slug: string }> }) {
  const { slug } = await ctx.params
  try {
    return NextResponse.json(await getBackend().getSquadBySlug(slug))
  } catch (e) {
    return toErrorResponse(e)
  }
}
