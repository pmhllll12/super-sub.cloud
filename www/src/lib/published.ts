/**
 * 공개로 돌린 **내** 클립 — 영상 모음(`HomeFeed`)에 붙는 것들.
 *
 * ⚠️ **서버 저장이 아니다.** 계약에 클립의 공개 여부가 없어서(미결
 * 「클립을 공개할 수 있어야 합니다」, 담당 정어진) 이 브라우저에만 남는다.
 * 다른 기기에서는 안 보이고, 남에게도 안 보인다 — 화면에도 그렇게 적는다.
 *
 * 🔴 계약이 생기면 **이 파일만** 갈아 끼운다. 부르는 쪽(`MyVideos` ·
 * `HomeFeed`)은 이 네 함수만 알고 저장 자리는 모른다.
 *
 * ⚠️ 좋아요·댓글은 "화면 안에서만" 사는데 이것만 저장소를 쓰는 이유 —
 * 공개는 `/me` 에서 켜고 `/home` 에서 확인한다. 화면이 갈리므로 상태로
 * 들고 있으면 넘어가는 순간 사라져 기능 자체가 성립하지 않는다.
 */

export const PUBLISHED_KEY = 'ss.published.v1'

export type PublishedClip = {
  /** `MyVideo.id`. 같은 영상을 두 번 담지 않는 기준이다. */
  id: string
  title: string
  what: string
  /** 재생 주소. 조회용 URL 이 없어 지금은 mock 클립(`/`로 시작)만 실제로 돈다. */
  src: string
  /** `가로 / 세로`. 미리 알아야 칸이 안 덜컥인다(`lib/feed.ts` 와 같은 규칙). */
  aspect: string
  at: string
}

function read(): PublishedClip[] {
  try {
    const raw = localStorage.getItem(PUBLISHED_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    // 사람이 손댈 수 있는 자리다 — 모양이 아니면 없는 것으로 친다.
    return Array.isArray(parsed) ? (parsed as PublishedClip[]) : []
  } catch {
    // 깨진 JSON, 그리고 사생활 보호 모드에서 던지는 경우까지 여기서 받는다.
    return []
  }
}

function write(list: PublishedClip[]): void {
  try {
    localStorage.setItem(PUBLISHED_KEY, JSON.stringify(list))
  } catch {
    // 저장을 못 하는 것은 참을 수 있다. 화면이 죽는 것은 아니다.
  }
}

export function listPublished(): PublishedClip[] {
  return read()
}

export function isPublished(id: string): boolean {
  return read().some((c) => c.id === id)
}

/** 이미 있으면 덮어쓴다 — 제목을 고쳐 다시 공개해도 두 번 안 쌓인다. */
export function publish(clip: PublishedClip): void {
  write([clip, ...read().filter((c) => c.id !== clip.id)])
}

export function unpublish(id: string): void {
  write(read().filter((c) => c.id !== id))
}
