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
 * 화면의 고르는 자리**를 같이 만든다.
 */

/**
 * 🔴 **`futsal` 이 아니라 `football` 이다**(2026-09-16 정정).
 *
 * 앞서 여기에 `'futsal'` 을 적고 「계약은 아무 종목이나 받는다」고 적었던 것은
 * **틀렸다.** 서버의 `sport` 참조 테이블에 **`futsal` 행이 없다** — 마이그레이션
 * `20260901_sport_and_position.py` 가 그 코드를 **폐기**하고 `football` 로 옮겼다
 * (`_RETIRED = "futsal"` · `_REPLACEMENT = "football"`). 지금 있는 것은
 * `football`·`baseball`·`basketball` 셋뿐이다.
 *
 * 그래서 배포에서 팀 만들기가 **`422 UNKNOWN_SPORT`(「등록되지 않은 종목
 * 코드입니다」)** 로 죽었다(사용자가 겪음). mock 에는 `futsal` 자리가 있어
 * 개발에서는 돌았다 — 지인 검색 스위치와 **같은 종류의 함정**이다.
 *
 * ⚠️ 제품이 말하는 「풋살」과 코드가 쓰는 `football` 이 다른 것은 **이름
 * 차이일 뿐**이고 그대로 두기로 했다(사용자 판단, 미결 `paik` 14번). 분석도
 * 같은 이유로 `football` 을 보낸다(`lib/sports.ts`).
 */
const SPORT = 'football'

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
