import { NextResponse, type NextRequest } from 'next/server'
import { getBackend, type CardStyleWire } from '@/server/backend'
import { withAuth } from '@/server/handler'

export async function GET(req: NextRequest) {
  return withAuth(req, async (token) => NextResponse.json(await getBackend().getMyCard(token)))
}

/**
 * 카드를 만든다 — `POST /api/v1/me/card` (api-contract.md 3장, 미결 jin-7).
 *
 * 🔴 **화면을 열 때 자동으로 부르지 않는다.** 공개 링크가 생기는 것은
 * 사용자의 행위여야 해서 계약이 `GET` 과 일부러 나눠 두었다 — 프리페치나
 * 봇이 카드를 만들면 되돌리기 어렵다.
 *
 * 멱등이라 이미 있으면 있는 카드가 그대로 온다. 그래서 201 을 고정으로
 * 쓰지 않고 200 으로 돌려준다 — 만들었는지 이미 있었는지는 화면이 굳이
 * 갈라 다룰 일이 없다.
 */
export async function POST(req: NextRequest) {
  return withAuth(req, async (token) => NextResponse.json(await getBackend().createMyCard(token)))
}

/**
 * 카드의 한 줄(`tagline`)과 꾸미기(`style`)를 바꾼다 — 계약 3장, CCC 18·35.
 *
 * 🔴 **보낸 필드만 통과시킨다** — `PATCH /videos/{id}` route handler 와 같은
 * 판단이다. `undefined` 로라도 실어 보내면 서버가 "왔다"로 읽어, 꾸미기만
 * 바꿔도 한 줄이 지워지는 갈래가 생긴다.
 */
export async function PATCH(req: NextRequest) {
  return withAuth(req, async (token) => {
    let body: { tagline?: unknown; style?: unknown; titles?: unknown }
    try {
      body = await req.json()
    } catch {
      return NextResponse.json(
        { error: { code: 'BAD_REQUEST', message: '요청 형식이 잘못되었습니다.' } },
        { status: 400 },
      )
    }

    const input: { tagline?: string | null; style?: CardStyleWire | null; titles?: string[] } =
      {}
    // `tagline` 은 `null` 이 지운다는 뜻이 있는 값이다 — 그대로 넘긴다.
    if ('tagline' in body) {
      const v = body.tagline
      if (v === null || typeof v === 'string') input.tagline = v
    }
    if ('style' in body) {
      const v = body.style
      input.style = v === null ? null : (v as CardStyleWire)
    }
    /* **사람이 직접 적는 호칭**(2026-09-16, 미결 `paik` 36번).
       ⚠️ **아직 계약에 없다** — mock 만 받는다. 진짜 서버가 이 칸을 받기 전까지
       실서버에서는 그냥 무시되거나 422 다. 화면이 그것을 숨기지 않고 말한다. */
    if ('titles' in body) {
      const v = body.titles
      if (!Array.isArray(v) || v.some((t) => typeof t !== 'string')) {
        return NextResponse.json(
          { error: { code: 'VALIDATION_ERROR', message: '호칭은 글자 목록입니다.' } },
          { status: 422 },
        )
      }
      // 🔴 **길이는 여기서 막는다** — 20자는 `tagline` 과 같은 값이고, 추천
      //    판의 한 줄에 들어가야 한다. 조용히 자르지 않는다(계약 3-5절과 같은
      //    판단 — 쓴 것과 보이는 것이 달라지면 알아차리는 때가 공유한 뒤다).
      if (v.some((t) => (t as string).trim().length > 20)) {
        return NextResponse.json(
          { error: { code: 'VALIDATION_ERROR', message: '호칭은 20자까지입니다.' } },
          { status: 422 },
        )
      }
      input.titles = v as string[]
    }

    if (Object.keys(input).length === 0) {
      return NextResponse.json(
        {
          error: {
            code: 'VALIDATION_ERROR',
            message: 'tagline·style·titles 중 하나가 필요합니다.',
          },
        },
        { status: 422 },
      )
    }
    return NextResponse.json(await getBackend().updateMyCard(token, input))
  })
}
