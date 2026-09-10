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

/**
 * **누구를 분석할지** — 「이 사람으로 분석」이 정한 닻 (계약 3-6절, CCC 26).
 *
 * 🔴 **한 덩어리다.** 계약은 `subject_box` 와 `subject_at_ms` 를 「함께 보내거나
 * 함께 생략」으로 정했고 한쪽만 오면 422 다. 두 값을 따로 받으면 그 규칙을
 * 부르는 쪽마다 지켜야 하는데, **하나로 묶으면 어길 수가 없다.**
 *
 * 🔴 `box` 는 **정규화 0~1** 이고 기준은 **영상 그림 안**이다 — 화면 픽셀도,
 * 레터박스를 포함한 상자 좌표도 아니다(`AnalysisStage` 의 `toVideoBox` 가
 * 그 변환을 한다). 픽셀을 보내면 422 이고 서버는 조용히 깎지 않는다.
 *
 * ⚠️ **지정이 없으면 통째로 생략한다.** 그것이 「자동으로 고르기」이고 정식
 * 경로다 — 억지로 채우면 없는 지정을 있는 것처럼 만든다.
 */
export type ClipSubject = {
  /** `[x, y, w, h]` — 정규화 0~1. `w·h > 0`, `x+w ≤ 1`, `y+h ≤ 1`. */
  box: [number, number, number, number]
  /** 그 박스를 잡고 있던 영상 시각(ms). `duration_ms` 를 넘으면 422. */
  atMs: number
}

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
  /**
   * 「이 사람으로 분석」이 정한 닻 (CCC 26). 없으면 「자동으로 고르기」다.
   *
   * 🔴 **깎거나 채우지 않는다.** 받은 값을 그대로 싣는다 — 계약이 범위 밖을
   * 422 로 막기로 했고 서버가 조용히 클램프하지 않는 것과 짝이다. 화면이
   * 미리 주무르면 「왜 엉뚱한 사람을 봤는가」의 근거가 사라진다.
   */
  subject?: ClipSubject
  /**
   * **어디를 집중해서 볼지** — 루브릭의 `criteria[].id` 목록 (CCC 29).
   *
   * 🔴 **한글 표시 이름이 아니라 `id` 다**(`follow_through`, `팔로스루`가 아니다).
   * 서버는 실재 여부를 못 본다 — 루브릭은 `agent/` 에 있다.
   * 🔴 **빈 목록도 생략도 정상이다.** 「전체적으로」가 기본이자 가장 흔한
   * 경우라 실패로 만들지 않는다.
   */
  focus?: string[]
}): Promise<MyVideo> {
  const { file, sportCode, meta, analyze, subject, focus } = opts

  const spot = await fetch('/api/videos/upload-url', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content_type: file.type, size_bytes: file.size, filename: file.name }),
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
      filename: file.name,
      ...meta,
      ...(analyze === false ? { analyze: false } : {}),
      // 🔴 **둘은 늘 같이 나간다** — `ClipSubject` 가 한 덩어리라 갈라질 수 없다.
      ...(subject ? { subject_box: subject.box, subject_at_ms: subject.atMs } : {}),
      // 빈 목록은 보낼 것이 없다 — 서버 기본값(「전체적으로」)과 같은 뜻이다.
      ...(focus?.length ? { focus } : {}),
    }),
  })
  // 🔴 반려(passed: false)는 201 이다 — 예외로 만들면 사유가 화면까지 못 온다.
  // 클라이언트는 status 가 아니라 passed 로 분기한다(계약 3-6절).
  if (!register.ok) throw new Error(await readError(register, '등록에 실패했습니다.'))
  return (await register.json()) as MyVideo
}
