import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 종목별 포지션 목록 — 계약 3-3절 `GET /positions` (CCC 28).
 *
 * 이 경로가 생기기 전에는 챗봇 프롬프트 · 스쿼드 등재 · 모집 등록이 각자
 * `{ GK: '골키퍼', … }` 를 들고 있었다. 🔴 **마이그레이션이 바뀌면 조용히
 * 낡는** 자리라, 목록의 정본을 서버 하나로 모은다.
 *
 * 🔴 **빈 `sport_code` 를 실어 보내지 않는다.** `?sport_code=` 는 "전체"가
 * 아니라 **없는 종목**이라 422 `UNKNOWN_SPORT` 로 튕긴다(`GET /matches` 와
 * 같은 판단 — 오타와 "그 종목 포지션이 아직 없다"가 같아 보이면 안 된다).
 * 전 종목을 원하면 **파라미터 자체를 빼서** 부른다.
 */
export async function GET(req: NextRequest) {
  const sport = req.nextUrl.searchParams.get('sport_code')
  return withAuth(req, async (token) =>
    NextResponse.json(
      await getBackend().listPositions(token, sport ? { sport_code: sport } : undefined),
    ),
  )
}
