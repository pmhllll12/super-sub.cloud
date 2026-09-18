import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 카드 사진을 올릴 **사전 서명 주소**를 얻는다 — 계약 3-5절
 * `POST /me/card/photo-upload-url`.
 *
 * 🔴 **바이트가 이 서버를 지나지 않는다**(PER-002). 여기서는 주소만 받아
 * 브라우저에 넘기고, 올리는 것은 브라우저가 S3 에 직접 한다 — 영상 업로드
 * (`api/videos/upload-url`)와 같은 방식이다. 사진을 이 라우트로 흘려보내면
 * 그 원칙이 깨지고 서버 메모리로 수 MB 가 올라온다.
 *
 * 🔴 **여기서 타입을 막지 않는다.** 받을 수 있는 형식은 **서버가** 정하고
 * (`422 UNSUPPORTED_PHOTO_TYPE`), 여기서 한 벌 더 적으면 두 목록이 갈린다 —
 * 실제로 그 어긋남이 「개발에서는 되는데 도메인에서 안 된다」의 단골이다.
 */
export async function POST(req: NextRequest) {
  return withAuth(req, async (token) => {
    let body: { content_type?: unknown }
    try {
      body = await req.json()
    } catch {
      return NextResponse.json(
        { error: { code: 'BAD_REQUEST', message: '요청 형식이 잘못되었습니다.' } },
        { status: 400 },
      )
    }
    if (typeof body.content_type !== 'string' || !body.content_type.trim()) {
      return NextResponse.json(
        { error: { code: 'VALIDATION_ERROR', message: '사진 형식을 알 수 없습니다.' } },
        { status: 422 },
      )
    }
    const made = await getBackend().createCardPhotoUploadUrl(token, body.content_type)
    return NextResponse.json(made)
  })
}
