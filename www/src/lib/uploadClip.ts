import type { MyVideo } from '@/server/backend'

/**
 * 클립 업로드 — 계약 3-6절의 세 단계를 한 자리에 모은다.
 *
 *   (1) POST /api/videos/upload-url   올릴 자리를 받는다
 *   (2) PUT  <upload_url>             S3 에 **직접** 올린다 (앱 서버를 안 지난다, PER-002)
 *   (3) POST /api/videos              등록하고 서버가 규격을 검사한다
 *
 * 🔴 영상 분석 화면(`AnalysisStage`)과 내 프로필(`MyVideos`)이 **같은 것을**
 * 부른다. 두 벌로 두면 계약이 바뀔 때 한쪽만 고쳐진다.
 */

/** 계약 3-6절의 상한 중 **화면이 미리 볼 수 있는 것**. */
export const LIMITS = {
  bytes: 200 * 1024 * 1024,
  types: ['video/mp4', 'video/quicktime'],
} as const

/**
 * 올리기 전에 거른다 — 통과면 `null`, 아니면 사람이 읽을 사유.
 *
 * 🔴 **형식과 용량만** 본다. 그 둘은 `upload-url` 이 422 로 튕겨서 아무 데도
 * 안 남으므로 미리 막는 편이 낫다. 길이·해상도는 반대다 — 서버가
 * `reject_reason` 으로 **남겨야 하는** 것이고(SFR-001 이 규격 검사를 두는
 * 이유가 그것이다), 화면이 미리 막으면 그 사유가 사라진다.
 */
export function checkClip(file: { type: string; size: number }): string | null {
  if (!(LIMITS.types as readonly string[]).includes(file.type)) {
    return '받지 않는 형식입니다. mp4 또는 mov 로 올려 주세요.'
  }
  if (file.size > LIMITS.bytes) {
    return `용량이 상한을 넘습니다 (상한 ${LIMITS.bytes / 1024 / 1024}MB).`
  }
  return null
}

/** 클라이언트가 잰 값. 서버가 다시 재려면 원본을 받아야 해서(PER-002) 우리가 준다. */
export type ClipMeta = { duration_ms: number; width: number; height: number }

async function readError(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json()
    return body?.error?.message ?? fallback
  } catch {
    return fallback
  }
}

export async function uploadClip(opts: {
  file: File
  sportCode: string
  meta: ClipMeta
  /**
   * 분석까지 걸 것인가. `false` 면 등록 본문에 실어 보낸다.
   *
   * ⚠️ **계약이 아직 이 필드를 모른다**(미결로 올렸다). 그래서 화면은 보낸 뜻이
   * 아니라 **돌아온 응답을 믿는다** — 백엔드가 무시하고 분석을 걸면
   * `analysis_job_id` 가 채워져 오고, 그러면 「분석 영상」이 맞다.
   */
  analyze?: boolean
}): Promise<MyVideo> {
  const { file, sportCode, meta, analyze } = opts

  const spot = await fetch('/api/videos/upload-url', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content_type: file.type, size_bytes: file.size }),
  })
  if (!spot.ok) throw new Error(await readError(spot, '업로드 자리를 못 받았습니다.'))
  const { storage_key, upload_url } = (await spot.json()) as {
    storage_key: string
    upload_url: string
  }

  // 🔴 서명에 Content-Type 이 들어 있다 — 요청한 값과 다르면 S3 가 거절한다.
  const put = await fetch(upload_url, {
    method: 'PUT',
    headers: { 'Content-Type': file.type },
    body: file,
  })
  if (!put.ok) throw new Error('S3 업로드가 실패했습니다.')

  const register = await fetch('/api/videos', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sport_code: sportCode,
      storage_key,
      ...meta,
      ...(analyze === false ? { analyze: false } : {}),
    }),
  })
  // 🔴 반려(passed: false)는 201 이다 — 예외로 만들면 사유가 화면까지 못 온다.
  // 클라이언트는 status 가 아니라 passed 로 분기한다(계약 3-6절).
  if (!register.ok) throw new Error(await readError(register, '등록에 실패했습니다.'))
  return (await register.json()) as MyVideo
}
