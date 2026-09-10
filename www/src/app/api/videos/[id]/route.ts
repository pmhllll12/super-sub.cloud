import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 내가 올린 클립을 지운다 — **저장소의 영상 파일과 그 분석 리포트까지.**
 *
 * 🔴 무엇을 어디서 지울지는 **서버가 정한다.** 브라우저는 저장 키도 리포트
 * 자리도 모르고, 알려 주면 남의 것을 지목할 수 있게 된다.
 *
 * ⚠️ **계약에 아직 이 경로가 없다**(미결 paik 13번). 진짜 백엔드에서는 404 가
 * 오고, 화면은 그 사유를 그대로 띄운다 — 지운 척하지 않는다.
 */
export async function DELETE(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params
  return withAuth(req, async (token) => {
    await getBackend().deleteMyVideo(token, id)
    // 본문이 없다. 지운 것에 대해 돌려줄 표현이 없다.
    return new NextResponse(null, { status: 204 })
  })
}

/**
 * 내 클립을 부분 수정한다 — 계약 3-6절 `PATCH /videos/{id}` (CCC 20 · 27).
 *
 * 🔴 **보낸 것만 바뀐다.** 그래서 **보낸 것만 통과시킨다** — 안 보낸 필드를
 * `undefined` 로라도 실어 보내면, 공개만 토글해도 제목이 지워지는 갈래가
 * 생긴다(서버가 "왔다"로 읽는다).
 * 🔴 대표(`is_featured`)는 **사람당 하나**라 옛 대표는 서버가 내린다.
 */
export async function PATCH(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params
  return withAuth(req, async (token) => {
    let body: {
      is_featured?: unknown
      is_public?: unknown
      title?: unknown
      description?: unknown
    }
    try {
      body = await req.json()
    } catch {
      return NextResponse.json(
        { error: { code: 'BAD_REQUEST', message: '요청 형식이 잘못되었습니다.' } },
        { status: 400 },
      )
    }

    const input: {
      is_featured?: boolean
      is_public?: boolean
      title?: string | null
      description?: string | null
    } = {}
    // 🔴 불리언 둘은 `null`·생략을 **무시한다**(계약: 보낸 것만 바뀐다).
    if (typeof body.is_featured === 'boolean') input.is_featured = body.is_featured
    if (typeof body.is_public === 'boolean') input.is_public = body.is_public
    // 🔴 글 둘은 `null` 이 **뜻이 있는 값**이다 — 지우라는 뜻이라 그대로 넘긴다.
    for (const key of ['title', 'description'] as const) {
      const v = body[key]
      if (v === null || typeof v === 'string') input[key] = v
    }

    if (Object.keys(input).length === 0) {
      return NextResponse.json(
        {
          error: {
            code: 'VALIDATION_ERROR',
            message: 'is_featured·is_public·title·description 중 하나가 필요합니다.',
          },
        },
        { status: 422 },
      )
    }
    return NextResponse.json(await getBackend().updateVideo(token, id, input))
  })
}
