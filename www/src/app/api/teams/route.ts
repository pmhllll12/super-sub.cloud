import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 팀을 만든다 (계약 3-3절). 🔴 **만든 사람이 `owner` 로 함께 들어간다** —
 * 그래서 만들자마자 `GET /me` 의 `teams` 에 잡히고, 홈 스쿼드 판이 그 팀을
 * 읽는다(`app/page.tsx` 가 `user.teams[0]` 을 쓴다).
 *
 * 🔴 **종목은 화면이 정하지 않는다** — 아래 상수 하나다. 이 서비스가 지금
 * 풋살만 다루기 때문이고(사용자 결정, 2026-09-16), 종목이 늘면 **여기와
 * 화면의 고르는 자리**를 같이 만든다. 계약은 이미 아무 종목이나 받는다.
 */
const SPORT = 'futsal'

export async function POST(req: NextRequest) {
  return withAuth(req, async (token) => {
    let body: { name?: unknown; region?: unknown }
    try {
      body = await req.json()
    } catch {
      return NextResponse.json(
        { error: { code: 'BAD_REQUEST', message: '요청 형식이 잘못되었습니다.' } },
        { status: 400 },
      )
    }
    const name = typeof body.name === 'string' ? body.name.trim() : ''
    const region = typeof body.region === 'string' ? body.region.trim() : ''
    if (!name || !region) {
      return NextResponse.json(
        { error: { code: 'VALIDATION_ERROR', message: '팀 이름과 지역을 적어 주세요.' } },
        { status: 422 },
      )
    }
    const made = await getBackend().createTeam(token, { name, region, sport_code: SPORT })
    return NextResponse.json(made, { status: 201 })
  })
}
