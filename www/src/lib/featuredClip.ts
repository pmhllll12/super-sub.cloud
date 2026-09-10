import type { FeaturedVideo, MyVideo } from '@/server/backend'

/**
 * **나를 보여주는 대표 영상** — 내 영상 중 하나를 골라 둔 것.
 *
 * 이 값은 「내가 어떤 선수인지 한 편으로 보여 주는 장면」이다. 추천 판에서
 * 후보 옆에 도는 영상이 바로 그 사람의 이 값이다 — 코치 목록이 코치마다
 * 대표 장면을 두는 것과 같은 뜻이고(`lib/market.ts` 의 `report.clipUrl`),
 * 말로 하는 자기소개 대신 장면을 보여 주는 것이 이 서비스의 주장이다.
 *
 * 🔴 **2026-09-10 에 브라우저 저장을 걷어냈다**(CCC 27, 미결 `paik` 10번).
 * 전에는 브라우저 저장소뿐이라 다른 기기에서는 안 보였고 **남의 대표는 아예
 * 읽을 수가 없어** 추천 판이 자리 표시 클립을 돌렸다. 이제 둘 다 계약이다:
 *
 *   세우기   `PATCH /videos/{id}` `{ is_featured }`
 *   읽기     `GET /cards/{slug}/featured-video`
 *
 * 🔴 **"지금 어느 것이 대표인가"를 이 파일이 들고 있지 않다.** 정본은
 * `MyVideo.is_featured` 다 — 사람당 하나라는 규칙을 서버가 지키므로(부분 유일
 * 인덱스), 화면이 따로 기억하면 서버와 갈릴 뿐이다. `featuredOf()` 가 그
 * 목록에서 골라 준다.
 */

/** 목록에서 대표를 고른다. 없으면 `null` — **서버 응답이 정본이다.** */
export function featuredOf(videos: MyVideo[]): MyVideo | null {
  return videos.find((v) => v.is_featured) ?? null
}

/**
 * 대표로 **세우거나 내린다** — `PATCH /videos/{id}`.
 *
 * 🔴 **옛 대표를 먼저 내리지 않는다.** 사람당 하나는 서버가 지킨다(세우면
 * 다른 것이 자동으로 내려간다). 화면이 「내리고 → 세우기」 두 번을 부르면
 * 그 사이에 끊겼을 때 대표가 하나도 없는 상태로 남는다.
 *
 * 바뀐 클립 한 줄을 돌려준다 — 부르는 쪽은 목록의 그 줄만 갈아 끼우면 된다.
 */
export async function setFeatured(videoId: string, on: boolean): Promise<MyVideo> {
  const res = await fetch(`/api/videos/${encodeURIComponent(videoId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_featured: on }),
  })
  if (!res.ok) {
    // 🔴 반려된 클립은 422 `CANNOT_FEATURE` 다 — 사유를 그대로 올린다.
    // 삼켜서 "됐다"로 그리면 다음에 열었을 때 안 세워져 있다.
    let message = '대표 영상을 바꾸지 못했습니다.'
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
 * **남의(또는 내) 대표 영상**을 카드 슬러그로 읽는다 —
 * `GET /cards/{slug}/featured-video`.
 *
 * 🔴 **없으면 `null` 이다.** 슬러그가 없든 대표를 안 세웠든 그 대표가
 * 반려됐든 밖에서는 다 404 `NO_FEATURED_VIDEO` 라, 화면이 가를 수 있는 것도
 * "있다 / 없다" 뿐이다. 없는 것은 고장이 아니므로 던지지 않는다.
 *
 * 🔴 **`url` 을 캐시하지 않는다** — `expires_in` 초 뒤 만료된다. 틀기 직전에
 * 부르고, 다시 필요하면 다시 부른다.
 */
export async function loadFeaturedOf(cardSlug: string): Promise<FeaturedVideo | null> {
  try {
    const res = await fetch(`/api/cards/${encodeURIComponent(cardSlug)}/featured-video`)
    if (!res.ok) return null
    return (await res.json()) as FeaturedVideo
  } catch {
    // 네트워크가 끊겨도 판은 계속 돈다 — 대표 영상은 이 화면의 본업이 아니다.
    return null
  }
}
