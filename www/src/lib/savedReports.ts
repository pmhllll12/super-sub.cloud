import type { VideoReport } from '@/server/backend'

/**
 * 분석 리포트를 **그 영상에 매달아 둔다.**
 *
 * 🔴 **2026-09-10 에 브라우저 저장소를 걷어냈다**(CCC 31, 미결 `paik` 7번 ·
 * `jin` 27번). 그전에는 화면이 만든 자리 표시를 이 브라우저의 `localStorage`
 * 에 두어서 **다른 기기에서는 안 보였고, 애초에 진짜 분석 결과가 아니었다.**
 * 이제 계약이다:
 *
 *   읽기  `GET /videos/{id}/report`
 *
 * 🔴 **모양을 바꾸는 일은 여기서만 한다.** 서버가 주는 것은 항목 배열
 * (`breakdown[]`)이고 화면이 그리는 것은 특징 · 호칭 목록이다. 부르는 쪽
 * (`AnalysisStage` · `MyVideos`)은 아래 셋만 알고 그 사이는 모른다 —
 * `lib/published.ts` 가 걷힌 방식과 같다.
 *
 * 🔴 **저장을 따로 하지 않는다.** 리포트는 분석이 끝나면 서버에 적재되므로
 * 화면이 남길 것이 없다 — 남는 문제는 「그 영상을 지우지 않는 것」뿐이고,
 * 그건 `AnalysisStage` 의 미저장분 정리가 맡는다.
 */

/**
 * 리포트 한 벌 — **화면이 쓰는 모양**이다.
 *
 * 🔴 **수치가 없다.** 계약 3장 4 가 `report.summary` 에 총점 · 등급 숫자를
 * 넣지 말라고 못박아 뒀고, 카드에 능력치 컬럼을 두지 않는 원칙(부록 D.5)과
 * 짝이다. 서버 응답에도 점수 숫자는 없다(허용목록).
 */
export type SavedReport = {
  summary: string
  traits: string[]
  /** 받은 것만. 못 받은 호칭을 미달 표식으로 남기지 않는다(4장). */
  titles: string[]
  /** 판단의 근거가 된 장면. 시각은 수치가 아니라 찾아가는 자리다. */
  scenes: { at: string; what: string }[]
  /** 분석한 날(YYYY-MM-DD). 언제 본 리포트인지는 알아야 한다. */
  savedAt: string
}

/**
 * 읽기의 결과. 🔴 **「아직」과 「없다」와 「고장」을 가른다** — 셋을 하나로
 * 뭉치면 분석 중인 클립이 결과 없는 클립처럼 보인다(미결 `paik` 7번의
 * 「하지 말 것」이 바로 이것이다).
 */
export type ReportResult =
  | { state: 'ready'; report: SavedReport }
  /** 영상은 있는데 아직 적재 전 — 분석 중이다. */
  | { state: 'not-ready' }
  /** 없는 영상이거나 남의 영상. */
  | { state: 'missing' }
  | { state: 'error'; message: string }

/** `7.5` → `0:07`. 🔴 초는 **버림**이다 — 그 시각 *이후*를 가리켜야 장면이 지나 있지 않다. */
function atText(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds))
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

/**
 * 서버 응답 → 화면 모양.
 *
 * 🔴 **`skipped` 항목은 뺀다.** `grade: null` 과 짝이라 「평가 대상이
 * 아니었다」는 뜻이고, 0 으로도 빈 문장으로도 그리면 못한 것으로 읽힌다.
 *
 * 🔴 **호칭은 서버가 채운 것만 그린다.** 「어느 등급부터 받은 호칭인가」는
 * 계약에 없어서, 우리가 `grade === 2` 같은 선을 그으면 그게 곧 지어내는
 * 것이다 — `title` 이 있으면 받은 것으로 본다(미결로 올려 둔다).
 */
export function toSavedReport(r: VideoReport): SavedReport {
  const live = r.breakdown.filter((b) => !b.skipped)
  return {
    summary: r.summary,
    traits: live.map((b) => b.evidence).filter((t): t is string => !!t),
    titles: live.map((b) => b.title).filter((t): t is string => !!t),
    scenes: r.scenes.map((s) => ({ at: atText(s.at_seconds), what: s.label })),
    savedAt: r.analyzed_at.slice(0, 10),
  }
}

/**
 * 그 영상의 리포트를 읽는다.
 *
 * ⚠️ **404 를 오류로 다루지 않는다.** 계약이 두 가지 뜻으로 쓰고 있어
 * (`REPORT_NOT_READY` · `VIDEO_NOT_FOUND`) 사유 코드로 갈라 준다.
 */
export async function fetchReport(videoId: string): Promise<ReportResult> {
  try {
    const res = await fetch(`/api/videos/${encodeURIComponent(videoId)}/report`)
    if (res.ok) return { state: 'ready', report: toSavedReport((await res.json()) as VideoReport) }

    let code = ''
    let message = '리포트를 읽지 못했습니다.'
    try {
      const body = (await res.json()) as { error?: { code?: string; message?: string } }
      code = body?.error?.code ?? ''
      message = body?.error?.message ?? message
    } catch {
      // 계약 형태가 아닌 응답 — 위 기본 문구를 쓴다.
    }
    if (code === 'REPORT_NOT_READY') return { state: 'not-ready' }
    if (code === 'VIDEO_NOT_FOUND') return { state: 'missing' }
    return { state: 'error', message }
  } catch {
    return { state: 'error', message: '리포트를 읽지 못했습니다.' }
  }
}
