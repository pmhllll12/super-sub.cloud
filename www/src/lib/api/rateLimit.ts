'use client'

import { useCallback, useEffect, useState } from 'react'
import { retryAfterSeconds } from './client'

/**
 * **429 뒤에는 같은 요청이 다시 안 나간다** — 계약 1번(SEC-009), 미결 `jin` 2번.
 *
 * 인증 세 경로(`/auth/login` · `/auth/signup` · `/auth/google`)에 같은 출처
 * 1분 10회 제한이 걸려 있다. 창이 지나기 전에 다시 보내면 **계속 거부되고
 * 서버 자원만 쓴다**(만료 시각을 밀지는 않는다 — 거부된 요청은 카운터에 안
 * 들어간다).
 *
 * 🔴 **기다릴 시간은 서버가 준 `Retry-After` 를 쓴다.** 임의의 상수(무조건
 * 60초)를 두면 필요 이상으로 기다리게 된다 — 남은 시간은 대부분 그보다 짧다.
 * 그 값이 브라우저까지 오도록 BFF 세 층을 이어 두었다(`server/handler.ts` ·
 * `lib/api/client.ts`).
 *
 * 🔴 **세 화면이 이 하나를 쓴다.** 로그인 · 가입 · 구글 로그인이 각자 세면
 * 한 곳만 고쳐지고, 그게 이 항목이 막으려는 것이다.
 */
export function useRateLimitLock() {
  /** 남은 초. 0 이면 안 잠겨 있다. */
  const [left, setLeft] = useState(0)

  useEffect(() => {
    if (left <= 0) return
    // 1초마다 한 칸씩 — 남은 시간을 화면에 보여 주려고 센다.
    const t = setInterval(() => setLeft((n) => (n <= 1 ? 0 : n - 1)), 1000)
    return () => clearInterval(t)
  }, [left])

  /**
   * 이 오류가 429 면 잠그고 `true` 를 돌려준다. 아니면 아무 일도 없이 `false`.
   * 부르는 쪽은 그 결과로 **제 에러 문구를 낼지** 정한다.
   */
  const lockFrom = useCallback((err: unknown): boolean => {
    const secs = retryAfterSeconds(err)
    if (secs === null) return false
    setLeft(secs)
    return true
  }, [])

  return {
    locked: left > 0,
    seconds: left,
    lockFrom,
    /** 잠겨 있는 동안 보여 줄 한 줄. 안 잠겼으면 `null`. */
    note: left > 0 ? `요청이 너무 잦습니다. ${left}초 뒤에 다시 시도해 주세요.` : null,
  }
}
