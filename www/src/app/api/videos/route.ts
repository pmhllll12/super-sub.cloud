import { NextResponse, type NextRequest } from 'next/server'
import { callFastApi } from '@/server/backend/fastapiCall'
import { withAuth } from '@/server/handler'

type VideoRegistration = {
  id: string
  sport_code: string
  storage_key: string
  duration_ms: number
  side: string | null
  created_at: string
  passed: boolean
  reject_reason: string | null
  analysis_job_id: string | null
  analysis_status: string | null
  /* 🔴 **같은 영상을 다시 올렸을 때만**(CCC 48, `ho` 41번). 서버가 새 분석을
     안 걸고 앞 결과를 여기 실어 준다 — 그때 `analysis_job_id` 는 `null` 이다.
     🔴 **등록 응답에만 실린다.** 나중에 `GET /videos` 로 같은 영상을 읽으면
     전부 `null` 이라, 이 응답을 놓치면 다시 볼 방법이 없다. */
  duplicate_of_video_id?: string | null
  duplicate_status?: string | null
  duplicate_failure_reason?: string | null
}

/** api-contract.md 3-6절 — 클립 업로드 3단계. S3에 올린 뒤 등록·검사한다. */
export async function POST(req: NextRequest) {
  return withAuth(req, async (token) => {
    let body: {
      sport_code?: string
      storage_key?: string
      filename?: string
      duration_ms?: number
      width?: number
      height?: number
      side?: string
    }
    try {
      body = await req.json()
    } catch {
      return NextResponse.json(
        { error: { code: 'BAD_REQUEST', message: '요청 형식이 잘못되었습니다.' } },
        { status: 400 },
      )
    }
    const { sport_code, storage_key, duration_ms, width, height } = body
    if (
      typeof sport_code !== 'string' ||
      typeof storage_key !== 'string' ||
      typeof duration_ms !== 'number' ||
      typeof width !== 'number' ||
      typeof height !== 'number'
    ) {
      return NextResponse.json(
        {
          error: {
            code: 'BAD_REQUEST',
            message: 'sport_code·storage_key·duration_ms·width·height가 필요합니다.',
          },
        },
        { status: 400 },
      )
    }

    // 201(반려 포함)과 4xx/5xx(등록 자체 실패)를 그대로 전달한다 — 클라이언트는
    // status가 아니라 body의 passed로 분기한다(api-contract.md 3-6절).
    const result = await callFastApi<VideoRegistration>('/videos', { method: 'POST', token, body })
    return NextResponse.json(result, { status: 201 })
  })
}
