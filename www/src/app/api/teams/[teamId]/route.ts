import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 팀 이름·지역을 고친다 — 계약 3-3절 `PATCH /teams/{team_id}`, **주장만**.
 *
 * 🔴 **왜 이게 필요한가**: 「사람을 찾는 팀」이 지역으로 거르는데(그 값이
 * `team.region` 이다) 오타를 내거나 연고를 옮기면 **그 팀 경기가 탐색에서
 * 통째로 빠졌고, 고칠 경로가 아예 없었다**(계약 52번).
 *
 * 🔴 **안 바꿀 필드는 빼서 보낸다.** `null` 은 「지우기」가 아니라 **422** 다
 * (둘 다 NOT NULL 이라 「안 정한 상태」가 없다). 그래서 이 자리에서 `null` 을
 * 조용히 떨어뜨리지 **않고** 422 로 돌려준다 — 떨어뜨리면 화면은 200 을 받고
 * **아무것도 안 바뀐 것을 성공으로** 읽는다(호칭 저장이 실서버에서 정확히
 * 그렇게 실패했다, 2026-09-16).
 *
 * 🔴 **`sport_code` 는 올려 보내지 않는다** — 본문에 자리가 없어 무시되고,
 * 포지션·스쿼드·경기가 전부 그 값에 매달려 있다. 종목을 바꿔야 하면 팀을
 * 새로 만드는 쪽이 맞다.
 */
export async function PATCH(
  req: NextRequest,
  ctx: { params: Promise<{ teamId: string }> },
) {
  const { teamId } = await ctx.params
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

    const input: { name?: string; region?: string } = {}
    for (const key of ['name', 'region'] as const) {
      const v = body[key]
      if (v === undefined) continue
      // 🔴 위 머리말대로 — `null` 도, 빈 글자도 거절한다.
      if (typeof v !== 'string' || !v.trim()) {
        return NextResponse.json(
          {
            error: {
              code: 'VALIDATION_ERROR',
              message: key === 'name' ? '팀 이름을 적어 주세요.' : '지역을 골라 주세요.',
            },
          },
          { status: 422 },
        )
      }
      input[key] = v.trim()
    }

    /* 빈 본문(`{}`)은 계약상 「아무것도 안 바뀜」이라 그대로 올려 보낸다 —
       화면이 부를 일은 없지만 계약이 허용하는 것을 여기서 막지 않는다. */
    const team = await getBackend().updateTeam(token, teamId, input)
    return NextResponse.json(team)
  })
}

/**
 * 팀을 **해체한다** — 계약 3-3절 `DELETE /teams/{team_id}`, **주장만**, `204`.
 *
 * 🔴 **왜 이게 필요한가**(미결 `paik` 35번, 사용자 지적 2026-09-18): 나가기는
 * 마지막 주장에게 `409 LAST_OWNER` 로 막힌다. 그래서 **혼자 만든 팀을 버릴
 * 방법이 아예 없었다** — 계약은 2026-09-17에 길을 냈는데 이 자리가 비어 있었다.
 *
 * 🔴 **행을 지우지 않는다.** 서버가 `disbanded_at` 을 찍고 구성원을 내보내며
 * 대기 중이던 초대·신청을 닫는다. 지난 경기·평가·스쿼드는 그대로 남는다.
 *
 * 🔴 **여기서 막지 않는다.** 주장인지, 앞으로 있을 경기가 있는지는 **서버만**
 * 안다 — `403 FORBIDDEN` · `409 TEAM_HAS_UPCOMING_MATCH` 를 그대로 흘려보내
 * 화면이 그 문구를 보여 준다(마지막 주장 나가기와 같은 원칙).
 */
export async function DELETE(
  req: NextRequest,
  ctx: { params: Promise<{ teamId: string }> },
) {
  const { teamId } = await ctx.params
  return withAuth(req, async (token) => {
    await getBackend().disbandTeam(token, teamId)
    // 계약이 `204` 다 — 본문이 없다.
    return new NextResponse(null, { status: 204 })
  })
}
