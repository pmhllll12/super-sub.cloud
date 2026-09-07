/** 프로필 화면이 쓰는 짧은 표기들 — 서버 쪽(page)과 클라이언트 쪽(MyVideos)이 같이 쓴다. */

/** `2026-08-25T10:30:00Z` → `2026.08.25`. */
export function ymd(iso: string): string {
  const d = new Date(iso)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getUTCFullYear()}.${p(d.getUTCMonth() + 1)}.${p(d.getUTCDate())}`
}

/** `10200` → `10.2초`, `72000` → `1분 12초`. */
export function dur(ms: number): string {
  const total = Math.round(ms / 1000)
  if (total < 60) return `${(ms / 1000).toFixed(1)}초`
  return `${Math.floor(total / 60)}분 ${total % 60}초`
}

/** `2026-09-10T10:00:00Z` → `2026.09.10 (목) 19:00` — 보는 사람의 시간대로 옮긴다. */
export function when(iso: string): string {
  const d = new Date(iso)
  const p = (n: number) => String(n).padStart(2, '0')
  const days = ['일', '월', '화', '수', '목', '금', '토']
  return `${d.getFullYear()}.${p(d.getMonth() + 1)}.${p(d.getDate())} (${days[d.getDay()]}) ${p(d.getHours())}:${p(d.getMinutes())}`
}
