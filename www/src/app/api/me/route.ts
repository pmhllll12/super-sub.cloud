import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'
import { clearSession } from '@/server/session'

export async function GET(req: NextRequest) {
  return withAuth(req, async (token) => NextResponse.json(await getBackend().getMe(token)))
}

/**
 * 내 정보를 고친다.
 *
 * 🔴 **보낸 칸만 바뀐다**(계약 3-12절). 닉네임만 고칠 때 검색 노출을 같이
 * 실어 보내면, 그 사람이 껐던 스위치가 조용히 켜진다 — 그래서 **있는 것만**
 * 골라 넘긴다.
 */
export async function PATCH(req: NextRequest) {
  return withAuth(req, async (token) => {
    let body: { nickname?: unknown; is_nickname_searchable?: unknown }
    try {
      body = await req.json()
    } catch {
      return NextResponse.json(
        { error: { code: 'BAD_REQUEST', message: '요청 형식이 잘못되었습니다.' } },
        { status: 400 },
      )
    }
    const input: { nickname?: string; is_nickname_searchable?: boolean } = {}
    if (body.nickname !== undefined) {
      if (typeof body.nickname !== 'string') {
        return NextResponse.json(
          { error: { code: 'VALIDATION_ERROR', message: '요청 값이 올바르지 않습니다: nickname' } },
          { status: 422 },
        )
      }
      input.nickname = body.nickname
    }
    if (body.is_nickname_searchable !== undefined) {
      if (typeof body.is_nickname_searchable !== 'boolean') {
        return NextResponse.json(
          {
            error: {
              code: 'VALIDATION_ERROR',
              message: '요청 값이 올바르지 않습니다: is_nickname_searchable',
            },
          },
          { status: 422 },
        )
      }
      input.is_nickname_searchable = body.is_nickname_searchable
    }
    // 🔴 빈 본문은 **아무것도 안 바꾸는 요청**이라 막는다 — 조용히 200 을
    //    돌려주면 부르는 쪽이 바뀐 줄 안다.
    if (Object.keys(input).length === 0) {
      return NextResponse.json(
        { error: { code: 'VALIDATION_ERROR', message: '고칠 값이 없습니다.' } },
        { status: 422 },
      )
    }
    return NextResponse.json(await getBackend().updateMe(token, input))
  })
}

/**
 * 탈퇴. 🔴 **비밀번호는 있을 수도 없을 수도 있다** — 구글로만 가입한 계정에는
 * 확인할 비밀번호가 없어서, 요구하면 그 사람은 탈퇴할 방법이 사라진다
 * (api-contract.md 2장). 그래서 없으면 없는 대로 넘긴다.
 */
export async function DELETE(req: NextRequest) {
  return withAuth(req, async (token) => {
    let body: { password?: unknown } = {}
    try {
      body = await req.json()
    } catch {
      // 본문이 없는 것은 정상이다(위 주석).
    }
    const password = typeof body.password === 'string' ? body.password : undefined
    await getBackend().deleteMe(token, { password })
    // 계정이 사라졌으므로 쿠키에 남은 토큰도 함께 지운다.
    return clearSession(new NextResponse(null, { status: 204 }))
  })
}
