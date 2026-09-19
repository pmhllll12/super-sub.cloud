import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 내 경기 조건 — 지역·시간·**포지션** (계약 3-13절, CCC 40번).
 *
 * 🔴 **이걸 올려야 내가 남의 AI 추천 후보로 뜬다.** 서버가 후보를 고를 때
 * 첫 하드 필터가 「그 포지션을 등록했는가」인데, 조건이 브라우저에만 남던
 * 동안에는(`lib/matchPrefs.ts` 의 localStorage) **아무도 등록된 적이 없어서**
 * 팀을 만들어도 추천이 0명이었다(2026-09-17). 팀 조건을 안 올리면 우리 팀이
 * 남의 목록에 안 뜨는 것과 짝을 이루는 규칙이다.
 * 🔴 **팀 조건과 안 섞인다** — 같은 사람이 팀장이면서 팀원일 수 있다.
 * 🔴 `PUT` 은 **통째로 교체**다 — 하나만 더하려도 전체를 다시 보낸다.
 */
export async function GET(req: NextRequest) {
  return withAuth(req, async (token) =>
    NextResponse.json(await getBackend().getMyMatchPrefs(token)),
  )
}

export async function PUT(req: NextRequest) {
  return withAuth(req, async (token) => {
    const body = (await req.json().catch(() => null)) as {
      region_ids?: unknown
      slots?: unknown
      position_ids?: unknown
    } | null
    /* 🔴 **모양을 여기서 본다.** 서버도 막지만, 빈 몸통을 그대로 흘리면
       「통째로 교체」 규칙 때문에 **조건이 전부 지워진다.** */
    if (
      !body ||
      !Array.isArray(body.region_ids) ||
      !Array.isArray(body.slots) ||
      !Array.isArray(body.position_ids)
    ) {
      return NextResponse.json(
        {
          error: {
            code: 'VALIDATION_ERROR',
            message: 'region_ids · slots · position_ids 를 배열로 보내야 합니다.',
          },
        },
        { status: 422 },
      )
    }
    return NextResponse.json(
      await getBackend().putMyMatchPrefs(token, {
        region_ids: body.region_ids as string[],
        slots: body.slots as { weekday: number; start_time: string; end_time: string }[],
        position_ids: body.position_ids as string[],
      }),
    )
  })
}
