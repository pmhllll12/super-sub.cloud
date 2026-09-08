import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 모집 중인 경기 — 「팀원」 판이 훑는 목록(계약 3-4절 `GET /matches`).
 *
 * 🔴 **팀 id 를 몰라도 되는 유일한 경로다.** 다른 목록은 그 팀을 이미 알아야
 * 하므로, 아직 팀이 없는 사람이 갈 데가 여기밖에 없다.
 *
 * 🔴 빈 값은 실어 보내지 않는다 — `sport_code=` 는 "전체"가 아니라 없는
 * 종목이라 422 로 튕긴다. 걸러 내는 일은 백엔드 접점이 한다.
 */
export async function GET(req: NextRequest) {
  return withAuth(req, async (token) => {
    const q = req.nextUrl.searchParams
    const page = Number(q.get('page') ?? '')
    const size = Number(q.get('size') ?? '')
    return NextResponse.json(
      await getBackend().searchMatches(token, {
        sport_code: q.get('sport_code') ?? undefined,
        region: q.get('region') ?? undefined,
        page: Number.isFinite(page) && page > 0 ? page : undefined,
        size: Number.isFinite(size) && size > 0 ? size : undefined,
      }),
    )
  })
}
