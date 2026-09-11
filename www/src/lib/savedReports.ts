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
 * (`breakdown[]`)이고 화면이 그리는 것은 칭호+문장 짝 목록이다. 부르는 쪽
 * (`AnalysisStage` · `MyVideos`)은 아래 넷만 알고 그 사이는 모른다 —
 * `lib/published.ts` 가 걷힌 방식과 같다.
 *
 * 🔴 **저장을 따로 하지 않는다.** 리포트는 분석이 끝나면 서버에 적재되므로
 * 화면이 남길 것이 없다 — 남는 문제는 「그 영상을 지우지 않는 것」뿐이고,
 * 그건 `AnalysisStage` 의 미저장분 정리가 맡는다.
 */

/**
 * 리포트 한 벌 — **화면이 쓰는 모양**이다.
 *
 * 🔴 **정정 (CCC 32, 2026-09-11)**: 이 타입이 앞서 "수치가 없다"고 적었던 것은
 * 틀렸다. 계약 3장 4 가 막은 것은 `summary` 문장 **안에** 숫자를 넣는 것이지,
 * 오버롤(`totalScore`·`overallGrade`)이나 항목별 `radar` 축 값이 아니다. 카드에
 * 능력치를 안 두는 원칙(부록 D.5)은 그대로다 — **이 값들을 `player_card`
 * 화면으로 옮기지 않는다.** 이 리포트 화면 전용이다.
 */
export type SavedReport = {
  summary: string
  /**
   * 항목별 **칭호+문장 짝**(`ho` 24번). 🔴 **따로 떼지 않는다** — `title`
   * 없이 `evidence`만 있으면 선수는 그것이 칭찬인지 지적인지 모른다.
   * `title`이 없는 항목도 있다(호칭은 서버가 채운 것만이라 못 받을 수
   * 있다) — 그때도 문장은 그대로 그린다.
   */
  points: { title: string | null; evidence: string }[]
  /** 판단의 근거가 된 장면. 시각은 수치가 아니라 찾아가는 자리다. */
  scenes: { at: string; what: string }[]
  /**
   * 오버롤 — **영상 하나(=분석 1회)의 값**이다(`ho` 28번). 여러 영상을 합친
   * 것이 아니다 — "이 클립의 오버롤"이라고만 쓴다. 옛 리포트(이 필드가 생기기
   * 전 적재분)는 `null` — 그때는 오버롤 표시를 건너뛴다.
   */
  totalScore: number | null
  overallGrade: string | null
  /**
   * 레이더 축 — 항목마다 이름 + `stat`(0~100). `skipped`거나 `stat`이 `null`인
   * 항목은 뺀다(0으로 그리면 "그 항목을 못했다"로 잘못 읽힌다). 🔴 **총점은
   * 이 값들의 평균이 아니다** — 등급의 가중합이다. 화면에 나란히 둘 때 그렇게
   * 안 읽히게 캡션을 단다.
   */
  radar: { name: string; stat: number }[]
  /** 분석한 날(YYYY-MM-DD). 언제 본 리포트인지는 알아야 한다. */
  savedAt: string
}

/**
 * 읽기의 결과. 🔴 **「아직」과 「없다」와 「실패」와 「고장」을 가른다** —
 * 뭉치면 분석 중인 클립이 결과 없는 클립처럼, 또는 **영영 안 될 실패가
 * 마치 곧 될 것처럼** 보인다(미결 `paik` 7번의 「하지 말 것」).
 *
 * 🔴 **정정 (2026-09-11)**: `failed` 상태를 새로 나눴다. 그전에는 서버가
 * `ANALYSIS_FAILED`를 안 구분해서 실패한 분석도 `not-ready`로 왔고, 화면이
 * "다시 확인"을 눌러도 영원히 같은 문구만 보여줬다 — 사용자가 실제로 겪었다.
 */
export type ReportResult =
  | { state: 'ready'; report: SavedReport }
  /** 영상은 있는데 아직 적재 전 — 분석 중이다. 다시 물어보면 바뀔 수 있다. */
  | { state: 'not-ready' }
  /**
   * 분석이 실패로 끝났다 — **다시 물어봐도 절대 안 바뀐다.** `reason`은
   * 사람이 읽을 사유(예: "품질 게이트 미달: … 재촬영이 필요하다").
   */
  | { state: 'failed'; reason: string }
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
 * 것이다 — `title` 이 있으면 받은 것으로 본다(미결로 올려 둔다). 없어도
 * 그 항목의 `evidence`는 버리지 않는다 — 칭호를 못 받았다고 문장까지
 * 사라지면 안 된다.
 */
export function toSavedReport(r: VideoReport): SavedReport {
  const live = r.breakdown.filter((b) => !b.skipped)
  return {
    summary: r.summary,
    points: live
      .filter((b) => !!b.evidence)
      .map((b) => ({ title: b.title ?? null, evidence: b.evidence as string })),
    scenes: r.scenes.map((s) => ({ at: atText(s.at_seconds), what: s.label })),
    totalScore: r.total_score,
    overallGrade: r.overall_grade,
    radar: live
      .filter((b) => b.stat !== null)
      .map((b) => ({ name: b.name, stat: b.stat as number })),
    savedAt: r.analyzed_at.slice(0, 10),
  }
}

/**
 * 그 영상의 리포트를 읽는다.
 *
 * ⚠️ **404 를 오류로 다루지 않는다.** 계약이 세 가지 뜻으로 쓰고 있어
 * (`REPORT_NOT_READY` · `ANALYSIS_FAILED` · `VIDEO_NOT_FOUND`) 사유 코드로
 * 갈라 준다.
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
    // 🔴 message 가 곧 실패 사유다 — ANALYSIS_FAILED 는 항상 사람이 읽을
    // 문장을 싣는다(백엔드 계약). 기본 문구로 덮지 않는다.
    if (code === 'ANALYSIS_FAILED') return { state: 'failed', reason: message }
    if (code === 'VIDEO_NOT_FOUND') return { state: 'missing' }
    return { state: 'error', message }
  } catch {
    return { state: 'error', message: '리포트를 읽지 못했습니다.' }
  }
}
