import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/** 수락된 지인 목록 (계약 3-12절). */
export async function GET(req: NextRequest) {
  return withAuth(req, async (token) => NextResponse.json(await getBackend().listContacts(token)))
}

/**
 * 지인 신청 (계약 3-12절).
 *
 * 🔴 **에러 코드를 여기서 삼키지 않는다** — `CANNOT_REQUEST_SELF`(422) ·
 * `USER_NOT_FOUND`(404) · `ALREADY_REQUESTED`(409) 로 화면이 갈린다.
 * `withAuth` 의 catch 가 계약 형태 그대로 내려보낸다.
 */
export async function POST(req: NextRequest) {
  return withAuth(req, async (token) => {
    let body: { target_user_id?: unknown; note?: unknown }
    try {
      body = await req.json()
    } catch {
      return NextResponse.json(
        { error: { code: 'BAD_REQUEST', message: '요청 형식이 잘못되었습니다.' } },
        { status: 400 },
      )
    }
    if (typeof body.target_user_id !== 'string' || !body.target_user_id) {
      return NextResponse.json(
        { error: { code: 'VALIDATION_ERROR', message: 'target_user_id 가 필요합니다.' } },
        { status: 422 },
      )
    }
    const made = await getBackend().requestContact(token, {
      target_user_id: body.target_user_id,
      ...(typeof body.note === 'string' ? { note: body.note } : {}),
    })
    return NextResponse.json(made, { status: 201 })
  })
}
