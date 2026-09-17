import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 지역 목록 — 조건 판의 「어느 동네에서」 후보 (계약 3-13절, CCC 40번).
 *
 * 🔴 **화면이 목록을 들고 있지 않다.** `lib/regions.ts` 의 붙박이 60곳이
 * 있던 자리고, 저장은 이름이 아니라 **`id`** 로 하므로 이 경로 없이는
 * 조건을 서버에 올릴 수가 없다.
 */
export async function GET(req: NextRequest) {
  return withAuth(req, async (token) => NextResponse.json(await getBackend().listRegions(token)))
}
