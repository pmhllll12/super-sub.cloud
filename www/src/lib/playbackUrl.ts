'use client'

import { useEffect, useState } from 'react'

/**
 * 클립을 **재생할 수 있는 주소**를 받아 온다 — 계약 3-6절
 * `GET /videos/{id}/playback-url`(사전 서명 GET URL).
 *
 * 🔴 **계약이 주는 것은 저장 키뿐이라** 그것을 `<video src>` 에 그대로 넣으면
 * 403 이다. 그래서 배포에서는 플레이어가 아예 안 그려졌고(미결 paik 12번),
 * localhost 만 mock 이 `public/` 경로를 줘서 재생됐다. 이 파일이 그 자리다.
 *
 * 🔴 **캐시하지 않는다.** `expires_in`(기본 900초) 뒤 만료되므로, 목록이 바뀔
 * 때마다 새로 받는다. 오래 켜 둔 화면에서 만료되면 그 클립만 안 나오고 다음
 * 갈래 이동에서 되살아난다 — 만료된 주소를 붙들고 있는 것보다 낫다.
 */

/** `/` 로 시작하는 키는 이미 주소다 — mock 이 넣어 준 `public/` 안의 파일. */
export function isDirectKey(storageKey: string): boolean {
  return storageKey.startsWith('/')
}

export async function fetchPlaybackUrl(videoId: string): Promise<string | null> {
  try {
    const res = await fetch(`/api/videos/${encodeURIComponent(videoId)}/playback-url`)
    if (!res.ok) return null
    const body: unknown = await res.json()
    const url = (body as { url?: unknown } | null)?.url
    return typeof url === 'string' ? url : null
  } catch {
    // 못 받아도 화면은 돈다 — 그 클립만 플레이어 없이 그려진다.
    return null
  }
}

/**
 * 여러 클립의 재생 주소를 한꺼번에 — `{ [video_id]: url }`.
 *
 * 🔴 **`/` 로 시작하는 키는 안 부른다.** mock 이 주는 `public/` 경로라 이미
 * 주소이고, 부르면 시험이 그물 밖으로 나간다.
 *
 * ⚠️ 목록이 그대로면 다시 안 받는다(키를 정렬해 비교) — 안 그러면 리렌더마다
 * 서명 주소를 새로 받아 온다.
 */
export function usePlaybackUrls(
  /**
   * ⚠️ **`storage_key` 는 없을 수 있다.** 공개 클립 목록(`GET /videos/public`)은
   * 저장 키를 아예 안 준다 — 키에 업로더의 `user_id` 가 들어 있어 계약이
   * 일부러 뺐다(CCC 20). 없으면 **늘 받아야 하는 것**으로 본다.
   */
  clips: { id: string; storage_key?: string }[],
): Record<string, string> {
  const [urls, setUrls] = useState<Record<string, string>>({})
  const needs = clips.filter((c) => !c.storage_key || !isDirectKey(c.storage_key)).map((c) => c.id)
  const key = [...needs].sort().join(',')

  useEffect(() => {
    const ids = key ? key.split(',') : []
    if (ids.length === 0) {
      setUrls({})
      return
    }
    let alive = true
    void (async () => {
      const pairs = await Promise.all(
        ids.map(async (id) => [id, await fetchPlaybackUrl(id)] as const),
      )
      if (!alive) return
      const next: Record<string, string> = {}
      for (const [id, url] of pairs) if (url) next[id] = url
      setUrls(next)
    })()
    return () => {
      alive = false
    }
  }, [key])

  return urls
}
