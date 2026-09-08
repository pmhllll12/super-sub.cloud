/**
 * **나를 보여주는 대표 영상** — 내 영상 중 하나를 골라 둔 것.
 *
 * 이 값은 「내가 어떤 선수인지 한 편으로 보여 주는 장면」이다. 추천 판에서
 * 후보 옆에 도는 영상이 바로 그 사람의 이 값이다 — 코치 목록이 코치마다
 * 대표 장면을 두는 것과 같은 뜻이고(`lib/market.ts` 의 `report.clipUrl`),
 * 말로 하는 자기소개 대신 장면을 보여 주는 것이 이 서비스의 주장이다.
 *
 * ⚠️ **계약에 자리가 없다.** `video` 에 「대표」 표시가 없고(3-6절), 남의
 * 대표 영상을 읽을 경로도 없다. 그래서 지금은 **내 것만** 그 브라우저에
 * 남는다 — 다른 사람 것은 화면의 자리 표시 클립 그대로다.
 * 🔴 경로가 생기면 이 파일만 갈아 끼운다(`published.ts` · `savedReports.ts` ·
 * `squadBoard.ts` 와 같은 방식).
 */

export type Featured = {
  /** 그 클립의 id(`MyVideo.id`). 어느 영상인지는 이 값이 정본이다. */
  videoId: string
  /**
   * 틀 수 있는 주소.
   *
   * ⚠️ 계약이 주는 것은 저장 키뿐이라(3-6절 「아직 없는 것」) 지금은 목업
   * 주소만 담긴다. 재생용 주소가 생기면 `videoId` 로 다시 물어보면 된다 —
   * 그래서 id 를 같이 둔다.
   */
  src: string | null
}

const KEY = 'supersub.featured.v1'

/** 🔴 읽기는 언제나 실패할 수 있다(사생활 보호 창 · 깨진 값 · 저장소 없음). */
export function loadFeatured(): Featured | null {
  try {
    const raw = globalThis.localStorage?.getItem(KEY)
    if (!raw) return null
    const v: unknown = JSON.parse(raw)
    if (!v || typeof v !== 'object') return null
    const f = v as Partial<Featured>
    return typeof f.videoId === 'string' ? { videoId: f.videoId, src: f.src ?? null } : null
  } catch {
    return null
  }
}

/** 대표로 세운다. 같은 영상을 다시 세우면 **푼다**(토글). */
export function setFeatured(next: Featured | null): void {
  try {
    if (next) globalThis.localStorage?.setItem(KEY, JSON.stringify(next))
    else globalThis.localStorage?.removeItem(KEY)
  } catch {
    // 못 써도 화면은 계속 돈다.
  }
}
