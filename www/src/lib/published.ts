import type { MyVideo, PublicVideo } from '@/server/backend'

/**
 * **공개로 돌린 클립** — 영상 모음(`HomeFeed`)에 붙는 것들.
 *
 * 🔴 **2026-09-10 에 브라우저 저장소를 걷어냈다**(CCC 20, 미결 `paik` 5번).
 * 그전에는 이 브라우저에만 남아서 **다른 기기에서도, 남에게도 안 보였다** —
 * 「공개」라는 말이 성립하지 않는 상태였다. 이제 계약이다:
 *
 *   켜고 끄기 · 제목  `PATCH /videos/{id}` `{is_public, title, description}`
 *   남의 것까지 목록  `GET /videos/public`
 *
 * 🔴 **"이 클립이 공개인가"를 이 파일이 들고 있지 않다.** 정본은
 * `MyVideo.is_public` 이다 — 내 목록의 각 줄에 실려 온다.
 *
 * 🔴 부르는 쪽(`MyVideos` · `HomeFeed`)은 아래 세 함수만 안다.
 */

/** 내 목록의 그 줄이 공개인가. **서버 응답이 정본이다.** */
export function isPublished(v: MyVideo): boolean {
  return v.is_public
}

async function patch(videoId: string, body: unknown): Promise<MyVideo> {
  const res = await fetch(`/api/videos/${encodeURIComponent(videoId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    let message = '공개 여부를 바꾸지 못했습니다.'
    try {
      message = (await res.json())?.error?.message ?? message
    } catch {
      // 계약 형태가 아닌 응답 — 위 기본 문구를 쓴다.
    }
    throw new Error(message)
  }
  return (await res.json()) as MyVideo
}

/**
 * 공개로 돌린다. 제목과 한 줄 설명을 **같이** 보낸다.
 *
 * 🔴 **한 번에 보낸다.** 「공개로 돌리고 → 제목을 단다」 두 번으로 나누면 그
 * 사이에 끊겼을 때 **이름 없는 영상이 남에게 보인다.**
 * ⚠️ 서버가 100자 · 280자를 넘으면 422 다 — 화면이 미리 막는 편이 낫다.
 */
export function publish(
  videoId: string,
  meta: { title: string; description: string },
): Promise<MyVideo> {
  return patch(videoId, {
    is_public: true,
    title: meta.title,
    // 빈 문자열은 서버가 **지운다**(`null` 과 같은 뜻) — 그대로 보내면 된다.
    description: meta.description,
  })
}

/**
 * 공개를 푼다.
 *
 * 🔴 **제목을 같이 지우지 않는다.** 부분 수정이라 안 보낸 것은 그대로 남고,
 * 다시 공개할 때 적어 둔 이름이 살아 있다.
 */
export function unpublish(videoId: string): Promise<MyVideo> {
  return patch(videoId, { is_public: false })
}

/**
 * **공개된 클립 전부**(남의 것까지) — `GET /videos/public`.
 *
 * 🔴 **못 받으면 빈 배열이다.** 영상 모음은 붙박이 목록이 뒤를 받쳐 주므로
 * (`lib/feed.ts`) 목록을 못 받았다고 화면이 비면 안 된다.
 */
export async function listPublished(): Promise<PublicVideo[]> {
  try {
    const res = await fetch('/api/videos/public')
    if (!res.ok) return []
    const body: unknown = await res.json()
    return Array.isArray(body) ? (body as PublicVideo[]) : []
  } catch {
    return []
  }
}
