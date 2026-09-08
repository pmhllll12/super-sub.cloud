/**
 * 분석 리포트를 **그 영상에 매달아 둔다.**
 *
 * ⚠️ **아직 `localStorage` 다.** 계약에 리포트를 **읽는** 경로가 없다 —
 * `GET /videos` 가 주는 것은 `analysis_status`(queued · running · succeeded ·
 * failed)까지고, 요약 · 특징 · 호칭 · 근거 장면을 되받을 데가 없다(미결
 * 「분석 리포트를 **읽는** 경로가 없습니다」, 담당 정어진).
 *
 * 🔴 **경로가 생기면 이 파일만 갈아 끼운다.** 부르는 쪽(`AnalysisStage` ·
 * `MyVideos`)은 아래 두 함수만 알고 저장 방식은 모른다 — `lib/published.ts` ·
 * `me/cardStyleStore.ts` 와 같은 방식 · 같은 이유다.
 *
 * ⚠️ 그때까지는 **그 브라우저에만** 남는다. 다른 기기에서도 남에게도 안
 * 보인다 — 화면에도 그렇게 적어 둔다(숨기면 고장으로 읽힌다).
 */

/**
 * 리포트 한 벌.
 *
 * 🔴 **수치가 없다.** 계약 3장 4 가 `report.summary` 에 총점 · 등급 숫자를
 * 넣지 말라고 못박아 뒀고, 카드에 능력치 컬럼을 두지 않는 원칙(부록 D.5)과
 * 짝이다. 서버 경로가 생겨도 이 모양은 그대로여야 한다.
 */
export type SavedReport = {
  summary: string
  traits: string[]
  /** 받은 것만. 못 받은 호칭을 미달 표식으로 남기지 않는다(4장). */
  titles: string[]
  /** 판단의 근거가 된 장면. 시각은 수치가 아니라 찾아가는 자리다. */
  scenes: { at: string; what: string }[]
  /** 저장한 날(YYYY-MM-DD). 언제 본 리포트인지는 알아야 한다. */
  savedAt: string
}

const KEY = 'supersub.reports.v1'

type Store = Record<string, SavedReport>

/**
 * 🔴 **읽기는 언제나 실패할 수 있다.** 사생활 보호 창 · 저장 공간 꽉 참 ·
 * 남이 넣어 둔 깨진 값 — 어느 쪽이든 화면이 통째로 안 뜨면 안 된다.
 * ⚠️ 이 jsdom 조합은 `localStorage` 를 안 깔아 준다(`vitest.setup.ts` 참고).
 */
function read(): Store {
  try {
    const raw = globalThis.localStorage?.getItem(KEY)
    if (!raw) return {}
    const parsed: unknown = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? (parsed as Store) : {}
  } catch {
    return {}
  }
}

/** 그 영상에 매달린 리포트. 없으면 null. */
export function reportFor(videoId: string): SavedReport | null {
  return read()[videoId] ?? null
}

/** 리포트를 그 영상에 매단다. 같은 영상을 다시 저장하면 덮어쓴다. */
export function saveReport(videoId: string, report: Omit<SavedReport, 'savedAt'>): SavedReport {
  const saved: SavedReport = { ...report, savedAt: new Date().toISOString().slice(0, 10) }
  try {
    globalThis.localStorage?.setItem(KEY, JSON.stringify({ ...read(), [videoId]: saved }))
  } catch {
    // 못 써도 화면은 계속 돈다 — 저장이 이 화면의 본업이 아니다.
  }
  return saved
}

/**
 * 그 영상의 리포트를 **잊는다.** 영상을 지울 때 함께 부른다 — 안 그러면
 * 지워진 영상의 리포트가 이 브라우저에 남는다.
 */
export function forgetReport(videoId: string): void {
  const all = read()
  if (!(videoId in all)) return
  delete all[videoId]
  try {
    globalThis.localStorage?.setItem(KEY, JSON.stringify(all))
  } catch {
    // 못 지워도 화면은 계속 돈다 — 목록의 정본은 서버다.
  }
}
