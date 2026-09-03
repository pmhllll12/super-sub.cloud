import { NextResponse, type NextRequest } from 'next/server'
import { callFastApi } from '@/server/backend/fastapiCall'
import { withAuth } from '@/server/handler'

/** api-contract.md 3-6절 — 클립 업로드 1단계. 올릴 자리(S3 사전 서명 URL)를 받는다. */
export async function POST(req: NextRequest) {
  return withAuth(req, async (token) => {
    let body: { content_type?: string; size_bytes?: number }
    try {
      body = await req.json()
    } catch {
      return NextResponse.json(
        { error: { code: 'BAD_REQUEST', message: '요청 형식이 잘못되었습니다.' } },
        { status: 400 },
      )
    }
    if (typeof body.content_type !== 'string' || typeof body.size_bytes !== 'number') {
      return NextResponse.json(
        { error: { code: 'BAD_REQUEST', message: 'content_type과 size_bytes가 필요합니다.' } },
        { status: 400 },
      )
    }

    const result = await callFastApi<{ storage_key: string; upload_url: string; expires_in: number }>(
      '/videos/upload-url',
      { method: 'POST', token, body },
    )
    return NextResponse.json(result)
  })
}
